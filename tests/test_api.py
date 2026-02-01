"""
Unit tests for LeetCode API endpoints.

These tests use FastAPI's TestClient to test the API endpoints
without needing to actually run the server.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import json

from src.api.api import app, cache


# Create test client
client = TestClient(app)


def create_mock_response(status_code: int, json_data: dict):
    """Create a mock response object that works with async client."""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = json_data
    return mock_response


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def setup_cache():
    """Ensure cache has some test data before each test and mock initialize."""
    # Save original state
    original_questions = cache.questions.copy() if cache.questions else {}
    original_slug_to_id = cache.slug_to_id.copy() if cache.slug_to_id else {}
    original_frontend_id_to_slug = cache.frontend_id_to_slug.copy() if cache.frontend_id_to_slug else {}
    original_last_updated = cache.last_updated
    
    # Add some test questions to the cache for tests that need them
    cache.questions = {
        "1": {
            "questionId": "1",
            "questionFrontendId": "1",
            "title": "Two Sum",
            "titleSlug": "two-sum",
            "difficulty": "Easy",
            "paidOnly": False,
            "hasSolution": True,
            "hasVideoSolution": True
        },
        "2": {
            "questionId": "2",
            "questionFrontendId": "2",
            "title": "Add Two Numbers",
            "titleSlug": "add-two-numbers",
            "difficulty": "Medium",
            "paidOnly": False,
            "hasSolution": True,
            "hasVideoSolution": False
        }
    }
    cache.slug_to_id = {
        "two-sum": "1",
        "add-two-numbers": "2"
    }
    cache.frontend_id_to_slug = {
        "1": "two-sum",
        "2": "add-two-numbers"
    }
    cache.last_updated = 1000000000
    
    # Mock the initialize method to prevent it from fetching real data
    with patch.object(cache, 'initialize', new_callable=AsyncMock) as mock_init:
        yield
    
    # Restore original state (optional, for isolation)


# ============================================================================
# Test: Home Page
# ============================================================================

class TestHomePage:
    """Tests for the home page endpoint."""

    def test_home_returns_html(self):
        """Test that the home page returns HTML content."""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


# ============================================================================
# Test: Health Check
# ============================================================================

class TestHealthCheck:
    """Tests for the health check endpoint."""

    def test_health_check_returns_ok(self):
        """Test that health check returns status ok."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data
        assert "questions_cached" in data
        assert "details_cached" in data


# ============================================================================
# Test: Problems Endpoints
# ============================================================================

class TestProblemsEndpoints:
    """Tests for problem-related endpoints."""

    def test_get_all_problems(self):
        """Test fetching all problems from cache."""
        response = client.get("/problems")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        
        # Check structure of first problem
        problem = data[0]
        assert "id" in problem
        assert "frontend_id" in problem
        assert "title" in problem
        assert "title_slug" in problem
        assert "url" in problem
        assert "difficulty" in problem

    def test_get_problem_by_slug(self):
        """Test fetching a specific problem by slug."""
        with patch("src.api.api.fetch_with_retry") as mock_fetch:
            mock_fetch.return_value = {
                "data": {
                    "question": {
                        "questionId": "1",
                        "questionFrontendId": "1",
                        "title": "Two Sum",
                        "content": "<p>Test content</p>",
                        "difficulty": "Easy",
                        "isPaidOnly": False
                    }
                }
            }
            
            response = client.get("/problem/two-sum")
            assert response.status_code == 200
            data = response.json()
            assert data["title"] == "Two Sum"

    def test_get_problem_by_frontend_id(self):
        """Test fetching a specific problem by frontend ID."""
        with patch("src.api.api.fetch_with_retry") as mock_fetch:
            mock_fetch.return_value = {
                "data": {
                    "question": {
                        "questionId": "1",
                        "questionFrontendId": "1",
                        "title": "Two Sum",
                        "content": "<p>Test content</p>",
                        "difficulty": "Easy",
                        "isPaidOnly": False
                    }
                }
            }
            
            response = client.get("/problem/1")
            assert response.status_code == 200

    def test_get_problem_not_found(self):
        """Test 404 when problem doesn't exist."""
        response = client.get("/problem/nonexistent-problem")
        assert response.status_code == 404

    def test_search_problems(self):
        """Test searching problems by title."""
        response = client.get("/search?query=sum")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["title"] == "Two Sum"

    def test_search_problems_no_results(self):
        """Test search with no matching results."""
        response = client.get("/search?query=xyz123notfound")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_random_problem(self):
        """Test getting a random problem."""
        response = client.get("/random")
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "title" in data
        assert "title_slug" in data

    def test_random_problem_with_difficulty_filter(self):
        """Test getting a random problem with difficulty filter."""
        response = client.get("/random?difficulty=Easy")
        assert response.status_code == 200
        data = response.json()
        assert data["difficulty"] == "Easy"

    def test_filter_problems(self):
        """Test filtering problems."""
        response = client.get("/problems/filter")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "limit" in data
        assert "skip" in data
        assert "problems" in data
        assert isinstance(data["problems"], list)

    def test_filter_problems_by_difficulty(self):
        """Test filtering problems by difficulty."""
        response = client.get("/problems/filter?difficulty=Easy")
        assert response.status_code == 200
        data = response.json()
        for problem in data["problems"]:
            assert problem["difficulty"] == "Easy"

    def test_filter_problems_pagination(self):
        """Test filtering problems with pagination."""
        response = client.get("/problems/filter?limit=1&skip=0")
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 1
        assert len(data["problems"]) <= 1

    def test_get_stats(self):
        """Test getting problem statistics."""
        response = client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "by_difficulty" in data
        assert "by_access" in data
        assert "easy" in data["by_difficulty"]
        assert "medium" in data["by_difficulty"]
        assert "hard" in data["by_difficulty"]

    def test_get_all_tags(self):
        """Test getting all topic tags."""
        with patch("src.api.api.client.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": {
                    "problemsetQuestionList": {
                        "total": 100,
                        "questions": [
                            {"topicTags": [{"name": "Array", "slug": "array"}, {"name": "Hash Table", "slug": "hash-table"}]},
                            {"topicTags": [{"name": "Array", "slug": "array"}, {"name": "Two Pointers", "slug": "two-pointers"}]}
                        ]
                    }
                }
            }
            mock_post.return_value = mock_response
            
            response = client.get("/tags")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) >= 2  # At least 2 unique tags
            # Array should appear first (highest count)
            assert data[0]["slug"] == "array"
            assert data[0]["problem_count"] == 2

    def test_get_problems_by_tag(self):
        """Test getting problems by tag."""
        with patch("src.api.api.client.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": {
                    "problemsetQuestionList": {
                        "total": 100,
                        "questions": [
                            {
                                "questionId": "1",
                                "questionFrontendId": "1",
                                "title": "Two Sum",
                                "titleSlug": "two-sum",
                                "difficulty": "Easy",
                                "paidOnly": False,
                                "hasSolution": True,
                                "hasVideoSolution": True
                            }
                        ]
                    }
                }
            }
            mock_post.return_value = mock_response
            
            response = client.get("/problems/tag/array")
            assert response.status_code == 200
            data = response.json()
            assert data["tag"] == "array"
            assert "total" in data
            assert "problems" in data

    def test_get_similar_problems(self):
        """Test getting similar problems."""
        # First, add to the question_details cache
        from src.api.api import cache
        cache.question_details.set("1", {
            "similarQuestions": '[{"title": "Three Sum", "titleSlug": "three-sum", "difficulty": "Medium"}]'
        })
        
        response = client.get("/problem/two-sum/similar")
        assert response.status_code == 200
        data = response.json()
        assert data["problem"] == "two-sum"
        assert "similar" in data
        assert isinstance(data["similar"], list)


# ============================================================================
# Test: User Endpoints
# ============================================================================

class TestUserEndpoints:
    """Tests for user-related endpoints."""

    def test_get_user_profile(self):
        """Test fetching user profile."""
        with patch("src.api.api.client.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": {
                    "matchedUser": {
                        "username": "testuser",
                        "profile": {
                            "realName": "Test User",
                            "ranking": 1000
                        }
                    }
                }
            }
            mock_post.return_value = mock_response
            
            response = client.get("/user/testuser")
            assert response.status_code == 200
            data = response.json()
            assert data["username"] == "testuser"

    def test_get_user_not_found(self):
        """Test 404 when user doesn't exist."""
        with patch("src.api.api.client.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": {"matchedUser": None}
            }
            mock_post.return_value = mock_response
            
            response = client.get("/user/nonexistentuser123")
            assert response.status_code == 404


    def test_get_user_contests(self):
        """Test fetching user contest history."""
        with patch("src.api.api.client.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": {
                    "userContestRanking": {
                        "attendedContestsCount": 10,
                        "rating": 1500
                    },
                    "userContestRankingHistory": []
                }
            }
            mock_post.return_value = mock_response
            
            response = client.get("/user/testuser/contests")
            assert response.status_code == 200
            data = response.json()
            assert "userContestRanking" in data

    def test_get_user_submissions(self):
        """Test fetching user submissions."""
        with patch("src.api.api.client.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": {
                    "recentSubmissionList": [
                        {"id": "123", "title": "Two Sum", "status": "Accepted"}
                    ]
                }
            }
            mock_post.return_value = mock_response
            
            response = client.get("/user/testuser/submissions")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    def test_get_user_submissions_with_limit(self):
        """Test fetching user submissions with custom limit."""
        with patch("src.api.api.client.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": {
                    "recentSubmissionList": []
                }
            }
            mock_post.return_value = mock_response
            
            response = client.get("/user/testuser/submissions?limit=50")
            assert response.status_code == 200

    def test_get_user_calendar(self):
        """Test fetching user calendar/submission heatmap."""
        with patch("src.api.api.client.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": {
                    "matchedUser": {
                        "userCalendar": {
                            "activeYears": [2023, 2024],
                            "streak": 10,
                            "totalActiveDays": 100,
                            "submissionCalendar": '{"1704067200": 5}',
                            "dccBadges": []
                        }
                    }
                }
            }
            mock_post.return_value = mock_response
            
            response = client.get("/user/testuser/calendar")
            assert response.status_code == 200
            data = response.json()
            assert "activeYears" in data
            assert "streak" in data
            # submissionCalendar should be parsed from JSON string to dict
            assert isinstance(data["submissionCalendar"], dict)

    def test_get_user_badges(self):
        """Test fetching user badges."""
        with patch("src.api.api.client.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": {
                    "matchedUser": {
                        "badges": [
                            {"id": "1", "name": "Annual Badge", "icon": "icon.png"}
                        ],
                        "upcomingBadges": []
                    }
                }
            }
            mock_post.return_value = mock_response
            
            response = client.get("/user/testuser/badges")
            assert response.status_code == 200
            data = response.json()
            assert "badges" in data
            assert "upcomingBadges" in data

    def test_get_user_skills(self):
        """Test fetching user skill stats."""
        with patch("src.api.api.client.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": {
                    "matchedUser": {
                        "tagProblemCounts": {
                            "advanced": [{"tagName": "Dynamic Programming", "problemsSolved": 50}],
                            "intermediate": [{"tagName": "Array", "problemsSolved": 100}],
                            "fundamental": [{"tagName": "Math", "problemsSolved": 30}]
                        }
                    }
                }
            }
            mock_post.return_value = mock_response
            
            response = client.get("/user/testuser/skills")
            assert response.status_code == 200
            data = response.json()
            assert "advanced" in data
            assert "intermediate" in data
            assert "fundamental" in data


# ============================================================================
# Test: Daily Challenge
# ============================================================================

class TestDailyChallenge:
    """Tests for daily challenge endpoint."""

    def test_get_daily_challenge(self):
        """Test fetching the daily challenge."""
        with patch("src.api.api.client.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": {
                    "activeDailyCodingChallengeQuestion": {
                        "date": "2024-01-15",
                        "link": "/problems/two-sum/",
                        "question": {
                            "questionId": "1",
                            "title": "Two Sum",
                            "difficulty": "Easy"
                        }
                    }
                }
            }
            mock_post.return_value = mock_response
            
            response = client.get("/daily")
            assert response.status_code == 200
            data = response.json()
            assert "date" in data
            assert "question" in data


# ============================================================================
# Test: Contests
# ============================================================================

class TestContests:
    """Tests for contests endpoint."""

    def test_get_contests(self):
        """Test fetching upcoming contests."""
        with patch("src.api.api.client.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": {
                    "topTwoContests": [
                        {
                            "title": "Weekly Contest 380",
                            "titleSlug": "weekly-contest-380",
                            "startTime": 1705161600,
                            "duration": 5400
                        }
                    ]
                }
            }
            mock_post.return_value = mock_response
            
            response = client.get("/contests")
            assert response.status_code == 200
            data = response.json()
            assert "topTwoContests" in data


# ============================================================================
# Test: LRU Cache
# ============================================================================

class TestLRUCache:
    """Tests for the LRU cache implementation."""

    def test_lru_cache_basic_operations(self):
        """Test basic get/set operations."""
        from src.api.api import LRUCache
        
        lru = LRUCache(max_size=3)
        
        # Set values
        lru.set("a", {"value": 1})
        lru.set("b", {"value": 2})
        lru.set("c", {"value": 3})
        
        # Get values
        assert lru.get("a") == {"value": 1}
        assert lru.get("b") == {"value": 2}
        assert lru.get("c") == {"value": 3}
        assert lru.get("nonexistent") is None

    def test_lru_cache_eviction(self):
        """Test that LRU eviction works correctly."""
        from src.api.api import LRUCache
        
        lru = LRUCache(max_size=2)
        
        lru.set("a", {"value": 1})
        lru.set("b", {"value": 2})
        
        # Access 'a' to make it recently used
        lru.get("a")
        
        # Add 'c', should evict 'b' (least recently used)
        lru.set("c", {"value": 3})
        
        assert lru.get("a") == {"value": 1}
        assert lru.get("b") is None  # evicted
        assert lru.get("c") == {"value": 3}

    def test_lru_cache_contains(self):
        """Test __contains__ method."""
        from src.api.api import LRUCache
        
        lru = LRUCache(max_size=5)
        lru.set("key1", {"data": "test"})
        
        assert "key1" in lru
        assert "key2" not in lru

    def test_lru_cache_len(self):
        """Test __len__ method."""
        from src.api.api import LRUCache
        
        lru = LRUCache(max_size=5)
        assert len(lru) == 0
        
        lru.set("a", {})
        lru.set("b", {})
        assert len(lru) == 2


# ============================================================================
# Test: Error Handling
# ============================================================================

class TestErrorHandling:
    """Tests for error handling scenarios."""

    def test_timeout_handling(self):
        """Test that timeout errors are handled properly."""
        import httpx
        
        with patch("src.api.api.client.post") as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Timeout")
            
            response = client.get("/user/testuser")
            assert response.status_code == 504
            assert "timed out" in response.json()["detail"].lower()

    def test_generic_error_handling(self):
        """Test that generic errors are handled properly."""
        with patch("src.api.api.client.post") as mock_post:
            mock_post.side_effect = Exception("Some error")
            
            response = client.get("/user/testuser")
            assert response.status_code == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
