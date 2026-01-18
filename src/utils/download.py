import requests
import time
import random
import json
import os
from src.utils.google_sheets import get_google_sheets_service, prepare_sheet_data, update_google_sheet

url = "https://leetcode.com/graphql"

# --- GraphQL Queries ---
all_questions_query = """
query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
  problemsetQuestionList: questionList(
    categorySlug: $categorySlug
    limit: $limit
    skip: $skip
    filters: $filters
  ) {
    total: totalNum
    questions: data {
      questionId
      questionFrontendId
      title
      titleSlug
    }
  }
}
"""

question_data_query = """
query questionData($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    questionId
    questionFrontendId
    title
    content
    likes
    dislikes
    stats
    similarQuestions
    categoryTitle
    hints
    topicTags { name }
    companyTags { name }
    difficulty
    isPaidOnly
    solution {
      canSeeDetail
      content
    }
    hasSolution 
    hasVideoSolution 
  }
}
"""

# --- Phase 1: Fetch basic question list with Pagination ---
all_basic_questions = []
limit_per_request = 100  # LeetCode API usually caps at 100 per request
skip = 0
total_questions = -1

data_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "leetcode_questions.json"))
os.makedirs(os.path.dirname(data_file_path), exist_ok=True)

print("Fetching question list from LeetCode...")

while True:
    variables = {
        "categorySlug": "",
        "limit": limit_per_request,
        "skip": skip,
        "filters": {}
    }
    payload = {
        "query": all_questions_query,
        "variables": variables
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code != 200:
        print(f"Failed to fetch list at skip {skip}. Status code: {response.status_code}")
        break
        
    data = response.json()
    res_list = data["data"]["problemsetQuestionList"]
    questions_batch = res_list["questions"]
    total_questions = res_list["total"]
    
    if not questions_batch:
        break
        
    all_basic_questions.extend(questions_batch)
    print(f"Progress: {len(all_basic_questions)} / {total_questions}")
    
    skip += limit_per_request
    
    # Break loop if all questions are fetched
    if len(all_basic_questions) >= total_questions:
        break
    
    # Small delay to avoid aggressive polling
    time.sleep(0.5)

print(f"Successfully retrieved basic info for {len(all_basic_questions)} questions.")

# --- Phase 2: Fetch detailed data with robust error handling ---
all_questions_data = []
max_retries = 5

for idx, question in enumerate(all_basic_questions):
    title_slug = question["titleSlug"]
    question_id = question["questionId"]
    
    # Check if we already have this data (Optional: simple in-memory skip)
    # If you want real "breakpoint" support, you should load your JSON file first
    
    payload = {
        "query": question_data_query,
        "variables": {"titleSlug": title_slug}
    }
    
    retries = 0
    success = False
    
    while retries < max_retries:
        try:
            # 1. Added timeout to prevent hanging
            response = requests.post(url, json=payload, timeout=15)
            
            if response.status_code == 200:
                question_data = response.json()
                if question_data.get("data") and question_data["data"].get("question"):
                    question_data["data"]["question"]["url"] = f"https://leetcode.com/problems/{title_slug}/"
                    all_questions_data.append(question_data)
                    print(f"Processed: {len(all_questions_data)}/{len(all_basic_questions)} - (ID: {question_id}) {question['title']}")
                success = True
                break
            elif response.status_code == 429:
                print("Rate limit hit (429). Sleeping longer...")
                time.sleep(30) # Wait 30 seconds if throttled
            else:
                print(f"HTTP Error {response.status_code} for {title_slug}")
                
        except (requests.exceptions.ConnectionError, 
                requests.exceptions.Timeout,
                requests.exceptions.ChunkedEncodingError) as e:
            # 2. Catch network-level errors
            retries += 1
            wait_time = (2 ** retries) + random.random() # Exponential backoff
            print(f"Network error: {e}. Retrying in {wait_time:.2f}s... ({retries}/{max_retries})")
            time.sleep(wait_time)
            
        except Exception as e:
            print(f"Unexpected error: {e}")
            break
            
    if not success:
        print(f"Critical: Failed to fetch {title_slug} after {max_retries} attempts. Skipping to next...")

    # 3. Intermediate Save: Save every 100 questions to prevent total data loss
    if len(all_questions_data) % 100 == 0:
        with open(data_file_path, "w", encoding='utf-8') as f:
            json.dump(all_questions_data, f, indent=2, ensure_ascii=False)
        print(f">>> Auto-save: Progress backed up to JSON.")

# --- Phase 3: Storage and External Updates ---

# 1. Save to local JSON backup
with open(data_file_path, "w", encoding='utf-8') as f:
    json.dump(all_questions_data, f, indent=2, ensure_ascii=False)

print(f"Local backup saved to: {data_file_path}")

# 2. Update Google Sheets
if len(all_questions_data) >= 1000:
    try:    
      print(f"Step 3: Updating Google Sheets with {len(all_questions_data)} items...")
      service = get_google_sheets_service()
      sheet_data = prepare_sheet_data(all_questions_data)        
      update_google_sheet(service, sheet_data, sheet_id=0)
      # update_google_sheet(service, sheet_data, sheet_id=533665120)
      print("Successfully updated Google Sheets!")
    except Exception as e:
        print(f"Failed to update Sheets: {e}")
else:
    # Automatic skip if data is less than 1000 to protect remote sheet
    print(f"Insufficient data: Found {len(all_questions_data)} questions.")
    print("Skipping Google Sheets update to prevent accidental data loss.")