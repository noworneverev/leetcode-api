# LeetCode API / LeetCode Sorted
[![Deployed on Vercel](https://img.shields.io/badge/Deployed%20on-Vercel-black?logo=vercel)](https://leetcode-api-pied.vercel.app) [![FastAPI](https://img.shields.io/badge/Powered%20By-FastAPI-%2300C7B7?logo=fastapi)](https://fastapi.tiangolo.com) [![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

*"Yet Another LeetCode API" - Because why reinvent the wheel? (But we did anyway 🛠️)*

A high-performance, caching-enabled API wrapper for LeetCode. Built with **FastAPI** to provide easy access to LeetCode problems, statistics, and user data. Ideal for building dashboards, analysis tools, or just exploring LeetCode data programmatically.

## ✨ Key Features

- **🔥 Always Fresh Data**: Auto-updating cache system ensures data is never stale.
- **⚡ Vercel-Ready**: Serverless architecture ready for one-click deployment.
- **🔓 No API Keys**: Open access with sensible rate limiting.
- **🛡️ Real Data**: Direct integration with LeetCode's GraphQL API.
- **📈 Advanced Stats**: Get detailed user skills, calendar heatmaps, and problem filters.

## 🚀 Core Services

| Service | Link | Description |
|---------|------|-------------|
| **Live API** | [**leetcode-api-pied.vercel.app**](https://leetcode-api-pied.vercel.app) | Base URL for API calls |
| **Interactive Docs** | [**/docs**](https://leetcode-api-pied.vercel.app/docs) | Test endpoints interactively |
| **Google Sheet** | [**View Sheet**](https://docs.google.com/spreadsheets/d/1sRWp95wqo3a7lLBbtNd_3KkTyGjx_9sctTOL5JOb6pA/edit?usp=sharing) | Daily updated DB with sorting |

> **Google Sheet Tip**: To filter/sort, select **Row 3** and go to **Data > Filter views > Create new filter view**.  

## ⚡ Quick Start

```bash
# Get today's daily challenge
curl https://leetcode-api-pied.vercel.app/daily

# Find a problem by ID/slug
curl https://leetcode-api-pied.vercel.app/problem/1
curl https://leetcode-api-pied.vercel.app/problem/two-sum

# Get user profile (try your LeetCode username!)
curl https://leetcode-api-pied.vercel.app/user/lee215
```

## 🔍 API Endpoints

### 🧩 Problems Endpoints
| Endpoint | Method | Description | Example |
|----------|--------|-------------|---------|
| `/problems` | GET | All LeetCode problems | [/problems](https://leetcode-api-pied.vercel.app/problems) |
| `/problems/filter` | GET | Filter problems (difficulty, etc) | [/problems/filter?difficulty=Easy](https://leetcode-api-pied.vercel.app/problems/filter?difficulty=Easy) |
| `/problem/{id_or_slug}` | GET | Get problem by ID/slug | [/problem/two-sum](https://leetcode-api-pied.vercel.app/problem/two-sum) |
| `/problem/{id}/similar` | GET | Get similar problems | [/problem/two-sum/similar](https://leetcode-api-pied.vercel.app/problem/two-sum/similar) |
| `/search` | GET | Search for problems | [/search?query=two%20sum](https://leetcode-api-pied.vercel.app/search?query=two%20sum) |
| `/random` | GET | Random problem (supports filters) | [/random?difficulty=Easy](https://leetcode-api-pied.vercel.app/random?difficulty=Easy) |
| `/stats` | GET | Global problem statistics | [/stats](https://leetcode-api-pied.vercel.app/stats) |
| `/tags` | GET | All topic tags w/ counts | [/tags](https://leetcode-api-pied.vercel.app/tags) |
| `/problems/tag/{slug}` | GET | Get problems by tag | [/problems/tag/array](https://leetcode-api-pied.vercel.app/problems/tag/array) |

### 👤 User Endpoints
| Endpoint | Method | Description | Example |
|----------|--------|-------------|---------|
| `/user/{username}` | GET | User profile & stats | [/user/lee215](https://leetcode-api-pied.vercel.app/user/lee215) |
| `/user/{username}/contests` | GET | User's recent contests | [/user/lee215/contests](https://leetcode-api-pied.vercel.app/user/lee215/contests) |
| `/user/{username}/submissions` | GET | User's recent submissions | [/user/lee215/submissions](https://leetcode-api-pied.vercel.app/user/lee215/submissions) |
| `/user/{username}/calendar` | GET | User's heatmap | [/user/lee215/calendar](https://leetcode-api-pied.vercel.app/user/lee215/calendar) |
| `/user/{username}/badges` | GET | User's badges | [/user/lee215/badges](https://leetcode-api-pied.vercel.app/user/lee215/badges) |
| `/user/{username}/skills` | GET | User's skills stats | [/user/lee215/skills](https://leetcode-api-pied.vercel.app/user/lee215/skills) |

### ⚡ Other
| Endpoint | Method | Description | Example |
|----------|--------|-------------|---------|
| `/daily` | GET | Today's coding challenge | [/daily](https://leetcode-api-pied.vercel.app/daily) |


## 🛠️ Local Setup

1. **Clone the repo**
    ```bash 
    git clone https://github.com/noworneverev/leetcode-api.git
    cd leetcode-api
    ```

2. **Set up virtual environment** (recommended)
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/MacOS
    venv\Scripts\activate     # Windows
    ```

3. **Install dependencies**
    ```bash 
    pip install -r requirements.txt
    ```

4. **Run the server**
    ```bash 
    python run.py
    ```
    Visit http://localhost:8000/docs for local Swagger docs!


## 🔄 Daily Updated Full Problems JSON

Get the latest LeetCode problems. Either run:
```bash 
python -m src.utils.download
```
or download `leetcode_questions.json`(updated daily) directly from the `data` folder.

---

### ⚠️ Disclaimer
This project is not affiliated with, endorsed, or sponsored by LeetCode. It is an independent project used for educational purposes. Use at your own risk.

### ✍️ Author
Made with ❤️ by [Yan-Ying Liao](http://noworneverev.github.io)