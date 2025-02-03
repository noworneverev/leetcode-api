import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
import httpx
import uvicorn

url = "https://leetcode.com/graphql"

all_questions = []
question_details = {}
id_to_slug = {}
slug_to_id = {}
frontendid_to_slug = {}
slug_to_frontendid = {}

async def fetch_all_questions_data():
    async with httpx.AsyncClient() as client:
        payload = {
            "query": """query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
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
            }""",
            "variables": {"categorySlug": "", "limit": 10000, "skip": 0, "filters": {}}
        }
        try:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                global all_questions, id_to_slug, slug_to_id, frontendid_to_slug, slug_to_frontendid
                all_questions = data["data"]["problemsetQuestionList"]["questions"]
                id_to_slug.clear()
                slug_to_id.clear()
                frontendid_to_slug.clear()
                slug_to_frontendid.clear()
                for q in all_questions:
                    id_to_slug[q["questionId"]] = q["titleSlug"]
                    slug_to_id[q["titleSlug"]] = q["questionId"]
                    frontendid_to_slug[q["questionFrontendId"]] = q["titleSlug"]
                    slug_to_frontendid[q["titleSlug"]] = q["questionFrontendId"]
        except Exception as e:
            print(f"Error fetching question list: {e}")

async def fetch_question_data(title_slug: str):
    async with httpx.AsyncClient() as client:
        for _ in range(5):
            payload = {
                "query": """query questionData($titleSlug: String!) {
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
                }""",
                "variables": {"titleSlug": title_slug}
            }
            try:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    question = data["data"]["question"]
                    question["url"] = f"https://leetcode.com/problems/{title_slug}/"
                    return question                
            except Exception as e:
                print(f"Error fetching question data: {e}")
                await asyncio.sleep(1)
        return None

async def periodic_cache_update():
    while True:
        await fetch_all_questions_data()
        await asyncio.sleep(3600)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await fetch_all_questions_data()
    update_task = asyncio.create_task(periodic_cache_update())
    yield
    update_task.cancel()
    try:
        await update_task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan)

@app.get("/questions")
async def get_all_questions():
    return [{
        "id": q["questionId"],
        "frontend_id": q["questionFrontendId"],
        "title": q["title"],
        "title_slug": q["titleSlug"],
        "url": f"https://leetcode.com/problems/{q['titleSlug']}/"
    } for q in all_questions]

@app.get("/question/{identifier}")
async def get_question(identifier: str):
    if identifier in frontendid_to_slug:
        slug = frontendid_to_slug[identifier]
    elif identifier in slug_to_id:
        slug = identifier
    else:
        raise HTTPException(status_code=404, detail="Question not found")
    qid = slug_to_id[slug]
    if qid not in question_details:
        data = await fetch_question_data(slug)
        if not data:
            raise HTTPException(status_code=404, detail="Question data unavailable")
        question_details[qid] = data
    return question_details[qid]

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
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                if not data.get("data", {}).get("matchedUser"):
                    raise HTTPException(status_code=404, detail="User not found")
                return data["data"]["matchedUser"]
            raise HTTPException(status_code=response.status_code, detail="Error fetching user profile")
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
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                return data["data"]["activeDailyCodingChallengeQuestion"]
            raise HTTPException(status_code=response.status_code, detail="Error fetching daily challenge")
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
            response = await client.post(url, json=payload)
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
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                if "errors" in data:
                    raise HTTPException(status_code=404, detail="User not found")
                return data["data"]["recentSubmissionList"]
            raise HTTPException(status_code=response.status_code, detail="Error fetching submissions")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

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
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                return data["data"]["problemsetQuestionList"]["questions"]
            raise HTTPException(status_code=response.status_code, detail="Error fetching problems by topic")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
