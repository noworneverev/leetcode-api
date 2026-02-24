import asyncio
import time
from contextlib import asynccontextmanager
from functools import lru_cache
from collections import OrderedDict
import httpx
from typing import Dict, Optional, List
import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request
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
        # Tags cache
        self.tags_cache: List[dict] = []
        self.tags_last_updated: float = 0
        self.tags_cache_duration: int = 3600  # Cache tags for 1 hour

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
                        
                        # Store topic tags if available (for /tags endpoint)
                        if "topicTags" in q:
                            q_data["topicTags"] = q["topicTags"]
                            
                        count += 1
            
            if count > 0:
                self.questions = temp_questions
                self.slug_to_id = temp_slug_to_id
                self.frontend_id_to_slug = temp_frontend_id_to_slug
                
                # Compute tags cache locally
                tag_counts = {}
                for q in self.questions.values():
                    if "topicTags" in q:
                        for tag in q["topicTags"]:
                            name = tag.get("name")
                            slug = tag.get("slug")
                            
                            if name and not slug:
                                # Generate slug from name if missing
                                slug = name.lower().replace(" ", "-")
                                # Update question tag data so it has the slug for future use
                                tag["slug"] = slug
                                
                            if slug and name:
                                if slug not in tag_counts:
                                    tag_counts[slug] = {"name": name, "slug": slug, "problem_count": 0}
                                tag_counts[slug]["problem_count"] += 1
                
                self.tags_cache = sorted(tag_counts.values(), key=lambda x: x["problem_count"], reverse=True)
                self.tags_last_updated = time.time()
                
                print(f"Loaded {count} questions from {self.data_file_path}")
                print(f"Computed {len(self.tags_cache)} tags from local data.")
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
async def get_random_problem(
    difficulty: Optional[str] = Query(None, description="Filter by difficulty: Easy, Medium, Hard"),
    tag: Optional[str] = Query(None, description="Filter by topic tag slug (e.g., 'array', 'dynamic-programming')")
):
    """
    Return a random problem. Optionally filter by difficulty and/or tag.
    """
    await cache.initialize()
    if not cache.questions:
        raise HTTPException(status_code=404, detail="No questions available")
    
    # Filter candidates
    candidates = list(cache.questions.values())
    
    if difficulty:
        difficulty_normalized = difficulty.capitalize()
        candidates = [q for q in candidates if q.get("difficulty") == difficulty_normalized]
    
    if tag:
        # For tag filtering, we need to check the detailed cache or fetch
        # This is a simplified version that works with cached details
        tag_lower = tag.lower().replace("-", " ")
        filtered = []
        for q in candidates:
            details = cache.question_details.get(q["questionId"])
            if details and details.get("topicTags"):
                tag_names = [t["name"].lower() for t in details["topicTags"]]
                if tag_lower in tag_names or tag.lower() in [t["name"].lower().replace(" ", "-") for t in details["topicTags"]]:
                    filtered.append(q)
        if filtered:
            candidates = filtered
    
    if not candidates:
        raise HTTPException(status_code=404, detail="No matching questions found")
    
    q = random.choice(candidates)
    return {
        "id": q["questionId"],
        "frontend_id": q["questionFrontendId"],
        "title": q["title"],
        "title_slug": q["titleSlug"],
        "difficulty": q["difficulty"],
        "url": f"https://leetcode.com/problems/{q['titleSlug']}/"
    }

@app.get("/problems/filter", tags=["Problems"])
async def filter_problems(
    difficulty: Optional[str] = Query(None, description="Filter by difficulty: Easy, Medium, Hard"),
    paid_only: Optional[bool] = Query(None, description="Filter by paid status"),
    has_solution: Optional[bool] = Query(None, description="Filter by has official solution"),
    limit: int = Query(50, ge=1, le=500, description="Number of results to return"),
    skip: int = Query(0, ge=0, description="Number of results to skip (for pagination)")
):
    """
    Filter problems by various criteria with pagination support.
    """
    await cache.initialize()
    
    results = list(cache.questions.values())
    
    # Apply filters
    if difficulty:
        difficulty_normalized = difficulty.capitalize()
        results = [q for q in results if q.get("difficulty") == difficulty_normalized]
    
    if paid_only is not None:
        results = [q for q in results if q.get("paidOnly") == paid_only]
    
    if has_solution is not None:
        results = [q for q in results if q.get("hasSolution") == has_solution]
    
    # Sort by frontend_id for consistent ordering
    results.sort(key=lambda x: int(x.get("questionFrontendId", 0) or 0))
    
    # Pagination
    total = len(results)
    results = results[skip:skip + limit]
    
    return {
        "total": total,
        "limit": limit,
        "skip": skip,
        "problems": [{
            "id": q["questionId"],
            "frontend_id": q["questionFrontendId"],
            "title": q["title"],
            "title_slug": q["titleSlug"],
            "url": f"https://leetcode.com/problems/{q['titleSlug']}/",
            "difficulty": q["difficulty"],
            "paid_only": q["paidOnly"],
            "has_solution": q["hasSolution"],
            "has_video_solution": q["hasVideoSolution"],
        } for q in results]
    }

@app.get("/stats", tags=["Problems"])
async def get_problem_stats():
    """
    Get overall statistics about problems.
    """
    await cache.initialize()
    
    questions = list(cache.questions.values())
    
    easy = sum(1 for q in questions if q.get("difficulty") == "Easy")
    medium = sum(1 for q in questions if q.get("difficulty") == "Medium")
    hard = sum(1 for q in questions if q.get("difficulty") == "Hard")
    free = sum(1 for q in questions if not q.get("paidOnly"))
    paid = sum(1 for q in questions if q.get("paidOnly"))
    with_solution = sum(1 for q in questions if q.get("hasSolution"))
    with_video = sum(1 for q in questions if q.get("hasVideoSolution"))
    
    return {
        "total": len(questions),
        "by_difficulty": {
            "easy": easy,
            "medium": medium,
            "hard": hard
        },
        "by_access": {
            "free": free,
            "paid": paid
        },
        "with_solution": with_solution,
        "with_video_solution": with_video
    }

@app.get("/tags", tags=["Problems"])
async def get_all_tags():
    """
    Get all available topic tags with problem counts.
    Served from local cache.
    """
    await cache.initialize()
    return cache.tags_cache

@app.get("/problems/tag/{tag_slug}", tags=["Problems"])
async def get_problems_by_tag(
    tag_slug: str,
    difficulty: Optional[str] = Query(None, description="Filter by difficulty: Easy, Medium, Hard"),
    limit: int = Query(50, ge=1, le=500, description="Number of results to return"),
    skip: int = Query(0, ge=0, description="Number of results to skip")
):
    """
    Get problems filtered by a specific topic tag.
    """
    try:
        query = """query problemsByTag($limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
            problemsetQuestionList: questionList(
                categorySlug: ""
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
        
        filters = {"tags": [tag_slug]}
        if difficulty:
            filters["difficulty"] = difficulty.upper()
        
        payload = {
            "query": query,
            "variables": {
                "limit": limit,
                "skip": skip,
                "filters": filters
            }
        }
        
        response = await client.post(leetcode_url, json=payload)
        if response.status_code == 200:
            data = response.json()
            result = data.get("data", {}).get("problemsetQuestionList", {})
            questions = result.get("questions", [])
            
            return {
                "tag": tag_slug,
                "total": result.get("total", 0),
                "limit": limit,
                "skip": skip,
                "problems": [{
                    "id": q["questionId"],
                    "frontend_id": q["questionFrontendId"],
                    "title": q["title"],
                    "title_slug": q["titleSlug"],
                    "url": f"https://leetcode.com/problems/{q['titleSlug']}/",
                    "difficulty": q["difficulty"],
                    "paid_only": q["paidOnly"],
                    "has_solution": q["hasSolution"],
                } for q in questions]
            }
        raise HTTPException(status_code=response.status_code, detail="Error fetching problems by tag")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request to LeetCode timed out")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/problem/{id_or_slug}/similar", tags=["Problems"])
async def get_similar_problems(id_or_slug: str):
    """
    Get similar problems for a given problem.
    """
    await cache.initialize()
    
    # First get the problem details
    if id_or_slug in cache.frontend_id_to_slug:
        slug = cache.frontend_id_to_slug[id_or_slug]
    elif id_or_slug in cache.slug_to_id:
        slug = id_or_slug
    else:
        raise HTTPException(status_code=404, detail="Question not found")
    
    question_id = cache.slug_to_id[slug]
    
    # Check if we have cached details
    cached = cache.question_details.get(question_id)
    if not cached:
        # Fetch the problem to get similar questions
        try:
            query = """query questionData($titleSlug: String!) {
                question(titleSlug: $titleSlug) {
                    similarQuestions
                }
            }"""
            
            payload = {
                "query": query,
                "variables": {"titleSlug": slug}
            }
            
            response = await client.post(leetcode_url, json=payload)
            if response.status_code == 200:
                data = response.json()
                cached = data.get("data", {}).get("question", {})
        except:
            raise HTTPException(status_code=500, detail="Error fetching problem details")
    
    similar_raw = cached.get("similarQuestions", "[]")
    if isinstance(similar_raw, str):
        import json
        try:
            similar = json.loads(similar_raw)
        except:
            similar = []
    else:
        similar = similar_raw or []
    
    return {
        "problem": slug,
        "similar": [{
            "title": s.get("title"),
            "title_slug": s.get("titleSlug"),
            "difficulty": s.get("difficulty"),
            "url": f"https://leetcode.com/problems/{s.get('titleSlug')}/"
        } for s in similar]
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
    except HTTPException:
        raise
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
    except HTTPException:
        raise
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/user/{username}/solved", tags=["Users"])
async def get_user_solved(
    username: str,
    x_leetcode_session: Optional[str] = Query(None, alias="x_leetcode_session", description="Your LEETCODE_SESSION cookie value. Get it from: DevTools → Application → Cookies → LEETCODE_SESSION. Without it, only ~20 recent solved problems are returned."),
):
    """
    Get all problems solved (Accepted) by a user.
    
    Pass your LEETCODE_SESSION cookie value in the 'x_leetcode_session' query parameter
    to fetch the complete solved list. Without it, only the 20 most recent
    accepted submissions are returned (LeetCode's public API limit).
    """
    leetcode_session = (x_leetcode_session or "").strip()
    
    try:
        if leetcode_session:
            # Authenticated path: use problemsetQuestionList with status=AC filter
            return await _get_solved_authenticated(username, leetcode_session)
        else:
            # Public path: limited to 20 most recent AC submissions
            return await _get_solved_public(username)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request to LeetCode timed out")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _get_solved_authenticated(username: str, leetcode_session: str):
    """Fetch ALL solved problems using authenticated LeetCode session."""
    query = """query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
        problemsetQuestionList: questionList(
            categorySlug: $categorySlug
            limit: $limit
            skip: $skip
            filters: $filters
        ) {
            total: totalNum
            questions: data {
                questionFrontendId
                titleSlug
                title
                difficulty
                status
            }
        }
    }"""

    headers = {
        "Cookie": f"LEETCODE_SESSION={leetcode_session}",
        "Referer": "https://leetcode.com",
    }

    seen_slugs = {}  # slug -> solved entry (dedup)
    skip = 0
    batch_size = 100
    total = None

    async with httpx.AsyncClient(timeout=30.0) as auth_client:
        while True:
            payload = {
                "query": query,
                "variables": {
                    "categorySlug": "",
                    "limit": batch_size,
                    "skip": skip,
                    "filters": {"status": "AC"},
                },
            }

            response = await auth_client.post(leetcode_url, json=payload, headers=headers)

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Error fetching from LeetCode (check your session cookie)",
                )

            data = response.json()
            if "errors" in data:
                raise HTTPException(status_code=401, detail="Invalid or expired session cookie")

            result = data.get("data", {}).get("problemsetQuestionList", {})
            if total is None:
                total = result.get("total", 0)

            questions = result.get("questions") or []
            if not questions:
                break

            for q in questions:
                slug = q.get("titleSlug", "")
                if slug and slug not in seen_slugs:
                    seen_slugs[slug] = {
                        "title_slug": slug,
                        "title": q.get("title", ""),
                        "difficulty": q.get("difficulty", ""),
                        "frontend_id": q.get("questionFrontendId", ""),
                    }

            skip += batch_size
            if skip >= total:
                break

            # Small delay to avoid rate limiting
            await asyncio.sleep(0.2)

    all_solved = list(seen_slugs.values())
    solved_slugs = list(seen_slugs.keys())

    return {
        "username": username,
        "total_solved": len(all_solved),
        "solved_slugs": solved_slugs,
        "solved": all_solved,
    }


async def _get_solved_public(username: str):
    """Fetch recent AC submissions (public, limited to ~20 by LeetCode)."""
    query = """query recentAcSubmissions($username: String!, $limit: Int!) {
        recentAcSubmissionList(username: $username, limit: $limit) {
            id
            title
            titleSlug
            timestamp
        }
    }"""

    payload = {
        "query": query,
        "variables": {"username": username, "limit": 20},
    }

    response = await client.post(leetcode_url, json=payload)
    if response.status_code == 200:
        data = response.json()
        if "errors" in data:
            raise HTTPException(status_code=404, detail="User not found")

        submissions = data.get("data", {}).get("recentAcSubmissionList") or []

        # Deduplicate by titleSlug
        seen = {}
        for sub in submissions:
            slug = sub.get("titleSlug")
            if slug and slug not in seen:
                seen[slug] = {
                    "title_slug": slug,
                    "title": sub.get("title", ""),
                    "timestamp": sub.get("timestamp", ""),
                }

        solved_list = list(seen.values())
        solved_slugs = list(seen.keys())

        return {
            "username": username,
            "total_solved": len(solved_list),
            "solved_slugs": solved_slugs,
            "solved": solved_list,
        }
    raise HTTPException(status_code=response.status_code, detail="Error fetching solved problems")


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


@app.get("/user/{username}/calendar", tags=["Users"])
async def get_user_calendar(username: str, year: int = None):
    try:
        query = """query userCalendar($username: String!, $year: Int) {
            matchedUser(username: $username) {
                userCalendar(year: $year) {
                    activeYears
                    streak
                    totalActiveDays
                    dccBadges {
                        timestamp
                        badge {
                            name
                            icon
                        }
                    }
                    submissionCalendar
                }
            }
        }"""
        
        payload = {
            "query": query,
            "variables": {"username": username, "year": year}
        }
        
        response = await client.post(leetcode_url, json=payload)
        if response.status_code == 200:
            data = response.json()
            if not data.get("data", {}).get("matchedUser"):
                raise HTTPException(status_code=404, detail="User not found")
            
            # submissionCalendar is a JSON string, parse it for convenience
            calendar_data = data["data"]["matchedUser"]["userCalendar"]
            import json
            if calendar_data.get("submissionCalendar"):
                calendar_data["submissionCalendar"] = json.loads(calendar_data["submissionCalendar"])
                
            return calendar_data
        raise HTTPException(status_code=response.status_code, detail="Error fetching calendar")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request to LeetCode timed out")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/{username}/badges", tags=["Users"])
async def get_user_badges(username: str):
    try:
        query = """query userBadges($username: String!) {
            matchedUser(username: $username) {
                badges {
                    id
                    name
                    shortName
                    displayName
                    icon
                    hoverText
                    medal {
                        slug
                        config {
                            iconGif
                            iconGifBackground
                        }
                    }
                    creationDate
                    category
                }
                upcomingBadges {
                    name
                    icon
                    progress
                }
            }
        }"""
        
        payload = {
            "query": query,
            "variables": {"username": username}
        }
        
        response = await client.post(leetcode_url, json=payload)
        if response.status_code == 200:
            data = response.json()
            if not data.get("data", {}).get("matchedUser"):
                raise HTTPException(status_code=404, detail="User not found")
            return data["data"]["matchedUser"]
        raise HTTPException(status_code=response.status_code, detail="Error fetching badges")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request to LeetCode timed out")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/{username}/skills", tags=["Users"])
async def get_user_skills(username: str):
    try:
        query = """query skillStats($username: String!) {
            matchedUser(username: $username) {
                tagProblemCounts {
                    advanced {
                        tagName
                        tagSlug
                        problemsSolved
                    }
                    intermediate {
                        tagName
                        tagSlug
                        problemsSolved
                    }
                    fundamental {
                        tagName
                        tagSlug
                        problemsSolved
                    }
                }
            }
        }"""
         
        payload = {
            "query": query,
            "variables": {"username": username}
        }
        
        response = await client.post(leetcode_url, json=payload)
        if response.status_code == 200:
            data = response.json()
            if not data.get("data", {}).get("matchedUser"):
                raise HTTPException(status_code=404, detail="User not found")
            return data["data"]["matchedUser"]["tagProblemCounts"]
        raise HTTPException(status_code=response.status_code, detail="Error fetching skills")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request to LeetCode timed out")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/contests", tags=["Contests"])
async def get_contests():
    try:
        query = """query upcomingContests {
            topTwoContests {
                title
                titleSlug
                startTime
                duration
                originStartTime
                isVirtual
            }
        }"""
        
        payload = {"query": query}
        
        response = await client.post(leetcode_url, json=payload)
        if response.status_code == 200:
            data = response.json()
            return data["data"]
        raise HTTPException(status_code=response.status_code, detail="Error fetching contests")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request to LeetCode timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def home():
    return FileResponse(os.path.join(static_dir, 'index.html')) 

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
