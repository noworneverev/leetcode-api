# LeetCode API 
[![Deployed on Vercel](https://img.shields.io/badge/Deployed%20on-Vercel-black?logo=vercel)](https://leetcode-api-pied.vercel.app) [![FastAPI](https://img.shields.io/badge/Powered%20By-FastAPI-%2300C7B7?logo=fastapi)](https://fastapi.tiangolo.com) [![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

*"Yet Another LeetCode API" - Because why reinvent the wheel? (But we did anyway 🛠️)*

## 🚀 Core Services
- **Live Demo**: [leetcode-api-pied.vercel.app](https://leetcode-api-pied.vercel.app)
- **Interactive Docs**: [docs.leetcode-api.vercel.app](https://leetcode-api-pied.vercel.app/docs)
- **Google Sheet Integration**: [View Sheet](https://docs.google.com/spreadsheets/d/1sRWp95wqo3a7lLBbtNd_3KkTyGjx_9sctTOL5JOb6pA/edit?usp=sharing)  
  *(Daily updated LeetCode question database with sorting/filtering)*

A no-nonsense LeetCode API service for developers who want LeetCode data without the scraping headaches. Perfect for:
- Building coding portfolios 🖼️
- Tracking practice stats 📊
- Creating LeetCode-powered apps 💻
- Just messing around with API endpoints 🤹

## ⚡ Quick Start

```bash
# Get today's daily challenge
curl https://leetcode-api-pied.vercel.app/daily

# Find a question by ID/slug
curl https://leetcode-api-pied.vercel.app/problem/two-sum

# Get user profile (try your LeetCode username!)
curl https://leetcode-api-pied.vercel.app/user/lee215
```

## 🔍 API Endpoints

| Endpoint                        | Method | Description                         | Example                                                                                     |
|---------------------------------|--------|-------------------------------------|---------------------------------------------------------------------------------------------|
| `/problems`                    | GET    | All LeetCode problems              | [/problems](https://leetcode-api-pied.vercel.app/problems)                             |
| `/problem/{id_or_slug}`        | GET    | Get problem by ID/slug             | [/problem/two-sum](https://leetcode-api-pied.vercel.app/problem/two-sum)                |
| `/problems/{topic}`             | GET    | Problems by topic (arrays, DP, etc) | [/problems/array](https://leetcode-api-pied.vercel.app/problems/array)                    |
| `/user/{username}`              | GET    | User profile & stats                | [/user/lee215](https://leetcode-api-pied.vercel.app/user/lee215)                      |
| `/user/{username}/contests`  | GET    | User's recent contests           | [/user/lee215/contests](https://leetcode-api-pied.vercel.app/user/lee215/contests)         |
| `/user/{username}/submissions`  | GET    | User's recent submissions           | [/user/lee215/submissions](https://leetcode-api-pied.vercel.app/user/lee215/submissions)         |
| `/daily`                        | GET    | Today's coding challenge            | [/daily](https://leetcode-api-pied.vercel.app/daily)                                      |


## 🛠️ Local Setup

1. Clone the repo
    ```bash 
    git clone https://github.com/yourusername/leetcode-api.git
    cd leetcode-api
    ```

2. Set up virtual environment (recommended)
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/MacOS
    venv\Scripts\activate     # Windows
    ```

4. Install dependencies
    ```bash 
    pip install -r requirements.txt
    ```

5. Run the server
    ```bash 
    python run.py
    ```
    Visit http://localhost:8000/docs for local Swagger docs!


## 🔄 Daily Updated Full Problems JSON

Get the latest LeetCode problems. Either run:
```bash 
python -m src.utils.download
```
or download  `leetcode_questions.json`(updated daily) directly from the `data` folder.

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