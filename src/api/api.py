import asyncio
import time
from contextlib import asynccontextmanager
from functools import lru_cache
from collections import OrderedDict
import httpx
from typing import Dict
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
import random
import os

# Determine base directory for static files
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
data_dir = os.path.join(base_dir, "data")
static_dir = os.path.join(base_dir, "static")

leetcode_url = "https://leetcode.com/graphql"
# Global client with timeout to prevent hanging requests
client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))

class LRUCache:
    """Simple LRU cache with max size to prevent unbounded memory growth."""
    def __init__(self, max_size: int = 500):
        self._cache: OrderedDict = OrderedDict()
        self._max_size = max_size
    
    def get(self, key: str):
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None
    
    def set(self, key: str, value: dict):
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)
        self._cache[key] = value
    
    def __contains__(self, key: str):
        return key in self._cache
    
    def __len__(self):
        return len(self._cache)


class QuestionCache:
    def __init__(self):
        self.questions: Dict[str, dict] = {}
        self.slug_to_id: Dict[str, str] = {}
        self.frontend_id_to_slug: Dict[str, str] = {}
        self.question_details = LRUCache(max_size=500)  # LRU cache to limit memory
        self.last_updated: float = 0
        self.update_interval: int = 3600
        self.lock = asyncio.Lock()
        self.data_file_path = os.path.join(data_dir, "leetcode_questions.json")

    async def initialize(self):
        async with self.lock:
            # First try to load from file if we haven't already
            if not self.questions:
                if self._load_from_file():
                    print("Initialized cache from local file.")
                    self.last_updated = time.time()
                else:
                    print("Local cache file not found or invalid. Fetching from API.")

            # If still empty or outdated (and we are not on Vercel or we want to update), try to fetch
            # Note: On Vercel we might want to rely solely on the file to avoid timeouts, 
            # but if the file is missing we have no choice but to try fetching.
            if not self.questions or (time.time() - self.last_updated) > self.update_interval:
                await self._fetch_all_questions()
                # self.last_updated is set in _fetch_all_questions now

    def _load_from_file(self) -> bool:
        """Load questions from local JSON file."""
        import json
        try:
            if not os.path.exists(self.data_file_path):
                return False
            
            with open(self.data_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # The file format from inspection seems to be a list of objects, 
            # where each object has "data" -> "question" -> fields
            # We need to parse this into our internal format
            temp_questions: Dict[str, dict] = {}
            temp_slug_to_id: Dict[str, str] = {}
            temp_frontend_id_to_slug: Dict[str, str] = {}
            
            count = 0
            for item in data:
                # Handle both raw format from LeetCode API (wrapped in 'data.question') 
                # and potentially our processed format if we saved it differently?
                # Looking at the provided file content, it is:
                # [ { "data": { "question": { ... } } }, ... ]
                
                q = None
                if "data" in item and "question" in item["data"]:
                    q = item["data"]["question"]
                elif "questionId" in item:
                    # In case we save it in a simplified format later, support that too
                    q = item
                
                if q:
                    # Normalized fields map
                    title_slug = q.get("titleSlug")
                    if not title_slug and q.get("url"):
                        # Extract slug from url: https://leetcode.com/problems/two-sum/ -> two-sum
                        parts = q.get("url").strip("/").split("/")
                        if parts:
                            title_slug = parts[-1]
                    
                    q_data = {
                        "questionId": q.get("questionId"),
                        "questionFrontendId": q.get("questionFrontendId"),
                        "title": q.get("title"),
                        "titleSlug": title_slug,
                        "difficulty": q.get("difficulty"),
                        "paidOnly": q.get("isPaidOnly") or q.get("paidOnly", False),
                        "hasSolution": q.get("hasSolution", False),
                        "hasVideoSolution": q.get("hasVideoSolution", False)
                    }
                    
                    # Ensure minimal required fields
                    if q_data["questionId"] and q_data["titleSlug"]:


                        temp_questions[q_data["questionId"]] = q_data
                        temp_slug_to_id[q_data["titleSlug"]] = q_data["questionId"]
                        if q_data["questionFrontendId"]:
                            temp_frontend_id_to_slug[q_data["questionFrontendId"]] = q_data["titleSlug"]
                        count += 1
            
            if count > 0:
                self.questions = temp_questions
                self.slug_to_id = temp_slug_to_id
                self.frontend_id_to_slug = temp_frontend_id_to_slug
                print(f"Loaded {count} questions from {self.data_file_path}")
                return True
                
        except Exception as e:
            print(f"Error loading from file: {e}")
        
        return False

    async def _fetch_all_questions(self):
        query = """query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
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
                    difficulty                    
                    paidOnly: isPaidOnly      
                    hasSolution
                    hasVideoSolution                                                           
                }
            }
        }"""
        
        try:
            # Build to temp dicts first for atomic swap (prevents empty results during refresh)
            temp_questions: Dict[str, dict] = {}
            temp_slug_to_id: Dict[str, str] = {}
            temp_frontend_id_to_slug: Dict[str, str] = {}
            
            limit_per_request = 100  # LeetCode API caps at 100 per request
            skip = 0
            total_questions = -1
            
            print("Starting to fetch all questions from LeetCode API...")
            
            while True:
                variables = {
                    "categorySlug": "",
                    "limit": limit_per_request,
                    "skip": skip,
                    "filters": {}
                }
                payload = {
                    "query": query,
                    "variables": variables
                }
                
                try:
                    response = await client.post(leetcode_url, json=payload)
                    if response.status_code != 200:
                        print(f"Failed to fetch list at skip {skip}. Status code: {response.status_code}")
                        break
                        
                    data = response.json()
                    res_list = data["data"]["problemsetQuestionList"]
                    questions_batch = res_list["questions"]
                    total_questions = res_list["total"]
                    
                    if not questions_batch:
                        break
                        
                    for q in questions_batch:
                        temp_questions[q["questionId"]] = q
                        temp_slug_to_id[q["titleSlug"]] = q["questionId"]
                        # Some questions might not have frontend id, safely handle
                        if q.get("questionFrontendId"):
                            temp_frontend_id_to_slug[q["questionFrontendId"]] = q["titleSlug"]
                    
                    print(f"Fetched questions: {len(temp_questions)} / {total_questions}")
                    
                    skip += limit_per_request
                    
                    # Break loop if all questions are fetched
                    if len(temp_questions) >= total_questions:
                        break
                        
                    # Small delay to avoid aggressive polling
                    await asyncio.sleep(0.3)
                    
                except httpx.TimeoutException:
                     print(f"Timeout occurred at skip {skip}. Aborting fetch.")
                     break
                except Exception as e:
                     print(f"Error at skip {skip}: {e}")
                     break
            
            # Atomic swap - only replace if we got data
            if temp_questions:
                self.questions = temp_questions
                self.slug_to_id = temp_slug_to_id
                self.frontend_id_to_slug = temp_frontend_id_to_slug
                self.last_updated = time.time()
                print(f"Successfully cached {len(self.questions)} questions from API.")
            else:
                print("Warning: No questions fetched, keeping existing cache.")
        except Exception as e:
            print(f"Error updating questions: {e}")

cache = QuestionCache()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await cache.initialize()
    yield
    # Cleanup: close the HTTP client on shutdown
    await client.aclose()

app = FastAPI(lifespan=lifespan)

# Add CORS middleware for public API access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add gzip compression - will compress responses > 500 bytes
app.add_middleware(GZipMiddleware, minimum_size=500)

# Mount static files AFTER app is created with lifespan
if os.path.exists(data_dir):
    print(f"Mounting data directory: {data_dir}")
    app.mount("/data", StaticFiles(directory=data_dir), name="data")
else:
    print(f"WARNING: Data directory not found at {data_dir}")

app.mount("/static", StaticFiles(directory=static_dir), name="static")

async def fetch_with_retry(url: str, payload: dict, retries: int = 3):
    for _ in range(retries):
        try:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Request failed: {e}")
            await asyncio.sleep(1)
    return None

@app.get("/problems", tags=["Problems"])
async def get_all_problems():
    await cache.initialize()
    return [{
        "id": q["questionId"],
        "frontend_id": q["questionFrontendId"],
        "title": q["title"],
        "title_slug": q["titleSlug"],
        "url": f"https://leetcode.com/problems/{q['titleSlug']}/",
        "difficulty": q["difficulty"],                
        "paid_only": q["paidOnly"],        
        "has_solution": q["hasSolution"],
        "has_video_solution": q["hasVideoSolution"],        
    } for q in cache.questions.values()]

@app.get("/problem/{id_or_slug}", tags=["Problems"])
async def get_problem(id_or_slug: str):
    await cache.initialize()
    
    if id_or_slug in cache.frontend_id_to_slug:
        slug = cache.frontend_id_to_slug[id_or_slug]
    elif id_or_slug in cache.slug_to_id:
        slug = id_or_slug
    else:
        raise HTTPException(status_code=404, detail="Question not found")

    # check cache
    question_id = cache.slug_to_id[slug]
    cached = cache.question_details.get(question_id)
    if cached:
        return cached

    # not in cache, fetch from leetcode
    query = """query questionData($titleSlug: String!) {
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
            solution { canSeeDetail content }
            hasSolution 
            hasVideoSolution
        }
    }"""
    
    payload = {
        "query": query,
        "variables": {"titleSlug": slug}
    }
    
    data = await fetch_with_retry(leetcode_url, payload)
    if not data or "data" not in data or not data["data"]["question"]:
        raise HTTPException(status_code=404, detail="Question data not found")
    
    question_data = data["data"]["question"]
    question_data["url"] = f"https://leetcode.com/problems/{slug}/"
        
    cache.question_details.set(question_id, question_data)
    return question_data

@app.get("/search", tags=["Problems"])
async def search_problems(query: str):
    """
    Search for problems whose titles contain the given query (case-insensitive).
    """
    await cache.initialize()
    query_lower = query.lower()
    results = []
    for q in cache.questions.values():
        if query_lower in q["title"].lower():
            results.append({
                "id": q["questionId"],
                "frontend_id": q["questionFrontendId"],
                "title": q["title"],
                "title_slug": q["titleSlug"],
                "url": f"https://leetcode.com/problems/{q['titleSlug']}/"
            })
    return results

@app.get("/random", tags=["Problems"])
async def get_random_problem():
    """
    Return a random problem from the cached questions.
    """
    await cache.initialize()
    if not cache.questions:
        raise HTTPException(status_code=404, detail="No questions available")
    q = random.choice(list(cache.questions.values()))
    return {
        "id": q["questionId"],
        "frontend_id": q["questionFrontendId"],
        "title": q["title"],
        "title_slug": q["titleSlug"],
        "url": f"https://leetcode.com/problems/{q['titleSlug']}/"
    }

@app.get("/user/{username}", tags=["Users"])
async def get_user_profile(username: str):
    try:
        query = """query userPublicProfile($username: String!) {
            matchedUser(username: $username) {
                username
                githubUrl
                twitterUrl
                linkedinUrl
                profile {
                    userAvatar
                    realName
                    websites
                    countryName
                    company
                    jobTitle
                    skillTags
                    school
                    aboutMe
                    postViewCount
                    postViewCountDiff
                    reputation
                    ranking
                    reputationDiff
                    solutionCount
                    solutionCountDiff
                    categoryDiscussCount
                    categoryDiscussCountDiff
                    certificationLevel
                }
                submitStats {
                    acSubmissionNum {
                        difficulty
                        count
                        submissions
                    }
                    totalSubmissionNum {
                        difficulty
                        count
                        submissions
                    }
                }
                contestBadge {
                    name
                    expired
                    hoverText
                    icon
                }
            }
        }"""
        
        payload = {
            "query": query,
            "variables": {"username": username},
            "operationName": "userPublicProfile"
        }
        
        response = await client.post(leetcode_url, json=payload)
        if response.status_code == 200:
            data = response.json()
            if not data.get("data", {}).get("matchedUser"):
                raise HTTPException(status_code=404, detail="User not found")
            return data["data"]["matchedUser"]
        raise HTTPException(status_code=response.status_code, detail="Error fetching user profile")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request to LeetCode timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/{username}/contests", tags=["Users"])
async def get_user_contest_history(username: str):
    try:
        query = """query userContestRankingInfo($username: String!) {
            userContestRanking(username: $username) {
                attendedContestsCount
                rating
                globalRanking
                totalParticipants
                topPercentage
                badge {
                    name
                }
            }
            userContestRankingHistory(username: $username) {
                attended
                trendDirection
                problemsSolved
                totalProblems
                finishTimeInSeconds
                rating
                ranking
                contest {
                title
                startTime
                }
            }
        }"""
        
        payload = {
            "query": query,
            "variables": {"username": username},
            "operationName": "userContestRankingInfo"
        }
        
        response = await client.post(leetcode_url, json=payload)
        if response.status_code == 200:
            data = response.json()
            if not data.get("data"):
                raise HTTPException(status_code=404, detail="User not found")
            return data["data"]
        raise HTTPException(status_code=response.status_code, detail="Error fetching contest history")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request to LeetCode timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/{username}/submissions", tags=["Users"])
async def get_recent_submissions(username: str, limit: int = Query(default=20, ge=1, le=100)):
    try:
        query = """query recentSubmissions($username: String!, $limit: Int) {
            recentSubmissionList(username: $username, limit: $limit) {
                id
                title
                titleSlug
                timestamp
                status
                statusDisplay
                lang
                url
                langName
                runtime
                isPending
                memory
                hasNotes
                notes
                flagType
                frontendId
                topicTags {
                    id
                }
            }
        }"""
        
        payload = {
            "query": query,
            "variables": {"username": username, "limit": limit}
        }
        
        response = await client.post(leetcode_url, json=payload)
        if response.status_code == 200:
            data = response.json()
            if "errors" in data:
                raise HTTPException(status_code=404, detail="User not found")
            return data["data"]["recentSubmissionList"]
        raise HTTPException(status_code=response.status_code, detail="Error fetching submissions")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request to LeetCode timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/daily", tags=["Daily Challenge"])
async def get_daily_challenge():
    try:
        query = """query questionOfToday {
            activeDailyCodingChallengeQuestion {
                date
                link
                question {
                    questionId
                    questionFrontendId
                    title
                    titleSlug
                    translatedTitle
                    difficulty
                    acRate
                    topicTags {
                        name
                        slug
                        nameTranslated: translatedName
                    }
                    content
                }
            }
        }"""
        
        payload = {"query": query}
        
        response = await client.post(leetcode_url, json=payload)
        if response.status_code == 200:
            data = response.json()
            return data["data"]["activeDailyCodingChallengeQuestion"]
        raise HTTPException(status_code=response.status_code, detail="Error fetching daily challenge")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request to LeetCode timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health", tags=["Utility"])
async def health_check():
    return {
        "status": "ok",
        "timestamp": time.time(),
        "questions_cached": len(cache.questions),
        "details_cached": len(cache.question_details),
        "cache_age_seconds": int(time.time() - cache.last_updated) if cache.last_updated else None
    }


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def home():
    return FileResponse(os.path.join(static_dir, 'index.html')) 

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
