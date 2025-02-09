import requests
import time
import random
import json
import os
from src.utils.google_sheets import get_google_sheets_service, prepare_sheet_data, update_google_sheet

url = "https://leetcode.com/graphql"

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
    topicTags {
      name
    }
    companyTags { 
      name 
    }
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

variables = {
    "categorySlug": "",
    "limit": 10000,
    "skip": 0,
    "filters": {}
}

payload = {
    "query": all_questions_query,
    "variables": variables
}

response = requests.post(url, json=payload)

if response.status_code != 200:
    print("Failed to fetch question list:", response.status_code)
    exit()

data = response.json()
total_questions = data["data"]["problemsetQuestionList"]["total"]
questions = data["data"]["problemsetQuestionList"]["questions"]

print(f"Total questions: {total_questions}")

all_questions_data = []
max_retries = 5

for question in questions:
    title_slug = question["titleSlug"]
    question_id = question["questionId"]
    payload = {
        "query": question_data_query,
        "variables": {"titleSlug": title_slug}
    }
    
    retries = 0
    while retries < max_retries:
        response = requests.post(url, json=payload)
        delay = random.uniform(0.5, 1.2)
        time.sleep(delay)
        
        if response.status_code == 200:
            question_data = response.json()
            question_data["data"]["question"]["url"] = f"https://leetcode.com/problems/{title_slug}/"
            all_questions_data.append(question_data)
            print(f"Fetched data for: (ID: {question_id}) {question['title']}")
            break
        else:
            retries += 1
            print(f"Failed to fetch data for: (ID: {question_id}) {question['title']}, retry {retries}/{max_retries}")
    
    if retries == max_retries:
        print(f"Max retries reached for: (ID: {question_id}) {question['title']}. Skipping...")

data_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "leetcode_questions.json"))
os.makedirs(os.path.dirname(data_file_path), exist_ok=True)

with open(data_file_path, "w") as f:
    json.dump(all_questions_data, f, indent=2)

print("All questions' data saved to leetcode_questions.json")

# Add Google Sheets update
try:    
    print("Starting Google Sheets update...")
    service = get_google_sheets_service()
    sheet_data = prepare_sheet_data(all_questions_data)
    update_google_sheet(service, sheet_data, sheet_id=0)
    print("Successfully updated Google Sheets")
except Exception as e:
    print(f"Failed to update Google Sheets: {str(e)}")

