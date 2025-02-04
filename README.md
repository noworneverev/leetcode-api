# LeetCode API 

*"Yet Another LeetCode API" - Because why reinvent the wheel? (But we did anyway 🛠️)*

[![Deployed on Vercel](https://img.shields.io/badge/Deployed%20on-Vercel-black?logo=vercel)](https://leetcode-api-pied.vercel.app) [![FastAPI](https://img.shields.io/badge/Powered%20By-FastAPI-%2300C7B7?logo=fastapi)](https://fastapi.tiangolo.com) [![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A no-nonsense LeetCode API service for developers who want LeetCode data without the scraping headaches. Perfect for:
- Building coding portfolios 🖼️
- Tracking practice stats 📊
- Creating LeetCode-powered apps 💻
- Just messing around with API endpoints 🤹

**Live Demo**: https://leetcode-api-pied.vercel.app  
**Interactive Docs**: https://leetcode-api-pied.vercel.app/docs

## 🚀 Quick Start

```bash
# Get today's daily challenge
curl https://leetcode-api-pied.vercel.app/daily

# Find a question by ID/slug
curl https://leetcode-api-pied.vercel.app/question/two-sum

# Get user profile (try your LeetCode username!)
curl https://leetcode-api-pied.vercel.app/user/lee215
```

## 🔍 API Endpoints

| Endpoint                        | Method | Description                         | Example                                                                                     |
|---------------------------------|--------|-------------------------------------|---------------------------------------------------------------------------------------------|
| `/questions`                    | GET    | All LeetCode questions              | [/questions](https://leetcode-api-pied.vercel.app/questions)                             |
| `/question/{id_or_slug}`        | GET    | Get question by ID/slug             | [/question/two-sum](https://leetcode-api-pied.vercel.app/question/two-sum)                |
| `/user/{username}`              | GET    | User profile & stats                | [/user/lee215](https://leetcode-api-pied.vercel.app/user/lee215)                      |
| `/daily`                        | GET    | Today's coding challenge            | [/daily](https://leetcode-api-pied.vercel.app/daily)                                      |
| `/problems/{topic}`             | GET    | Questions by topic (arrays, DP, etc) | [/problems/array](https://leetcode-api-pied.vercel.app/problems/array)                    |
| `/user/{username}/submissions`  | GET    | User's recent submissions           | [/user/lee215/submissions](https://leetcode-api-pied.vercel.app/user/lee215/submissions)         |


## 🛠️ Local Setup

1. Clone the repo
    ```bash 
    git clone https://github.com/yourusername/leetcode-api.git cd leetcode-api
    ```

2. Install dependencies
    ```bash 
    pip install -r requirements.txt
    ```

3. Run the server
    ```bash 
    python api.py
    ```

Visit http://localhost:8000/docs for local Swagger docs!

## 🤔 Why This API?
- Always Fresh Data 🥬
Auto-updating cache system (no stale LeetCode questions!)

- Vercel-Ready ⚡
One-click deployment with serverless architecture

- No API Keys 🔓
Free to use with sensible rate limits

- Real LeetCode Data 🔥
Direct integration with LeetCode's GraphQL API

---

*Disclaimer: This project isn't affiliated with LeetCode. Use at your own risk.*
Made with ❤️ by [Yan-Ying Liao](http://noworneverev.github.io)