import asyncio
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
import httpx
from typing import Dict
import uvicorn

app = FastAPI()
leetcode_url = "https://leetcode.com/graphql"
client = httpx.AsyncClient()

class QuestionCache:
    def __init__(self):
        self.questions: Dict[str, dict] = {}
        self.slug_to_id: Dict[str, str] = {}
        self.frontend_id_to_slug: Dict[str, str] = {}
        self.question_details: Dict[str, dict] = {}
        self.last_updated: float = 0
        self.update_interval: int = 3600
        self.lock = asyncio.Lock()

    async def initialize(self):
        async with self.lock:
            if not self.questions or (time.time() - self.last_updated) > self.update_interval:
                await self._fetch_all_questions()
                self.last_updated = time.time()

    async def _fetch_all_questions(self):
        query = """query problemsetQuestionList {
            problemsetQuestionList: questionList(
                categorySlug: ""
                limit: 10000
                skip: 0
                filters: {}
            ) {
                questions: data {
                    questionId
                    questionFrontendId
                    title
                    titleSlug
                }
            }
        }"""
        
        try:
            response = await client.post(leetcode_url, json={"query": query})
            if response.status_code == 200:
                data = response.json()
                questions = data["data"]["problemsetQuestionList"]["questions"]
                
                self.questions.clear()
                self.slug_to_id.clear()
                self.frontend_id_to_slug.clear()
                
                for q in questions:
                    self.questions[q["questionId"]] = q
                    self.slug_to_id[q["titleSlug"]] = q["questionId"]
                    self.frontend_id_to_slug[q["questionFrontendId"]] = q["titleSlug"]
        except Exception as e:
            print(f"Error updating questions: {e}")

cache = QuestionCache()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await cache.initialize()
    yield

app = FastAPI(lifespan=lifespan)

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

@app.get("/problems")
async def get_all_problems():
    await cache.initialize()
    return [{
        "id": q["questionId"],
        "frontend_id": q["questionFrontendId"],
        "title": q["title"],
        "title_slug": q["titleSlug"],
        "url": f"https://leetcode.com/problems/{q['titleSlug']}/"
    } for q in cache.questions.values()]

@app.get("/problems/{id_or_slug}")
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
    if question_id in cache.question_details:
        return cache.question_details[question_id]

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
        
    cache.question_details[question_id] = question_data
    return question_data

@app.get("/problems/{topic}")
async def get_problems_by_topic(topic: str):
    async with httpx.AsyncClient() as client:
        query = """query problemsetQuestionList($categorySlug: String, $filters: QuestionListFilterInput) {
            problemsetQuestionList: questionList(
                categorySlug: $categorySlug
                filters: $filters
            ) {
                questions: data {
                    questionId
                    title
                    titleSlug
                    difficulty
                    topicTags { name }
                }
            }
        }"""
        
        payload = {
            "query": query,
            "variables": {
                "categorySlug": "",
                "filters": {"tags": [topic]}
            }
        }
        
        try:
            response = await client.post(leetcode_url, json=payload)
            if response.status_code == 200:
                data = response.json()
                return data["data"]["problemsetQuestionList"]["questions"]
            raise HTTPException(status_code=response.status_code, detail="Error fetching problems by topic")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/{username}")
async def get_user_profile(username: str):
    async with httpx.AsyncClient() as client:
        query = """query userPublicProfile($username: String!) {
            matchedUser(username: $username) {
                username
                profile {
                    realName
                    websites
                    countryName
                    company
                    school
                    aboutMe
                    reputation
                    ranking
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
            }
        }"""
        
        payload = {
            "query": query,
            "variables": {"username": username},
            "operationName": "userPublicProfile"
        }
        
        try:
            response = await client.post(leetcode_url, json=payload)
            if response.status_code == 200:
                data = response.json()
                if not data.get("data", {}).get("matchedUser"):
                    raise HTTPException(status_code=404, detail="User not found")
                return data["data"]["matchedUser"]
            raise HTTPException(status_code=response.status_code, detail="Error fetching user profile")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/{username}/contests")
async def get_user_contest_history(username: str):
    async with httpx.AsyncClient() as client:
        query = """query userContestRankingInfo($username: String!) {
            userContestRanking(username: $username) {
                attendedContestsCount
                rating
                globalRanking
                totalParticipants
                topPercentage
            }
            userContestRankingHistory(username: $username) {
                attended
                trendDirection
                problemsSolved
                totalProblems
                finishTimeInSeconds
                rating
                ranking
            }
        }"""
        
        payload = {
            "query": query,
            "variables": {"username": username},
            "operationName": "userContestRankingInfo"
        }
        
        try:
            response = await client.post(leetcode_url, json=payload)
            if response.status_code == 200:
                data = response.json()
                if not data.get("data"):
                    raise HTTPException(status_code=404, detail="User not found")
                return data["data"]
            raise HTTPException(status_code=response.status_code, detail="Error fetching contest history")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/{username}/submissions")
async def get_recent_submissions(username: str, limit: int = 20):
    async with httpx.AsyncClient() as client:
        query = """query recentSubmissions($username: String!, $limit: Int) {
            recentSubmissionList(username: $username, limit: $limit) {
                title
                titleSlug
                timestamp
                statusDisplay
                lang
                url
            }
        }"""
        
        payload = {
            "query": query,
            "variables": {"username": username, "limit": limit}
        }
        
        try:
            response = await client.post(leetcode_url, json=payload)
            if response.status_code == 200:
                data = response.json()
                if "errors" in data:
                    raise HTTPException(status_code=404, detail="User not found")
                return data["data"]["recentSubmissionList"]
            raise HTTPException(status_code=response.status_code, detail="Error fetching submissions")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/daily")
async def get_daily_challenge():
    async with httpx.AsyncClient() as client:
        query = """query questionOfToday {
            activeDailyCodingChallengeQuestion {
                date
                link
                question {
                    questionId
                    questionFrontendId
                    title
                    titleSlug
                    difficulty
                    content
                }
            }
        }"""
        
        payload = {"query": query}
        
        try:
            response = await client.post(leetcode_url, json=payload)
            if response.status_code == 200:
                data = response.json()
                return data["data"]["activeDailyCodingChallengeQuestion"]
            raise HTTPException(status_code=response.status_code, detail="Error fetching daily challenge")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
