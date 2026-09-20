"""AI Assistant chat endpoint tests."""

from __future__ import annotations


def test_ai_chat_h_message(client, student_headers):
    """Test that 'Hi' message returns 200."""
    response = client.post(
        "/api/v1/ai/chat",
        json={"message": "Hi", "history": []},
        headers=student_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert "reply" in body


def test_ai_chat_create_sample_message(client, student_headers):
    """Test that 'Create a sample' message returns 200."""
    response = client.post(
        "/api/v1/ai/chat",
        json={"message": "Create a sample", "history": []},
        headers=student_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert "reply" in body


def test_ai_chat_conversation_history(client, student_headers):
    """Test conversation with history preserves context."""
    response1 = client.post(
        "/api/v1/ai/chat",
        json={"message": "Hi", "history": []},
        headers=student_headers,
    )
    assert response1.status_code == 200
    
    response2 = client.post(
        "/api/v1/ai/chat",
        json={
            "message": "What is my attendance?",
            "history": [
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": response1.json()["reply"]},
            ],
        },
        headers=student_headers,
    )
    assert response2.status_code == 200


def test_ai_chat_rejects_empty_message(client, student_headers):
    """Test that empty message returns 422."""
    response = client.post(
        "/api/v1/ai/chat",
        json={"message": "", "history": []},
        headers=student_headers,
    )
    assert response.status_code == 422


def test_ai_chat_accepts_missing_history(client, student_headers):
    """Test that missing history field (undefined) works correctly."""
    response = client.post(
        "/api/v1/ai/chat",
        json={"message": "Hi"},
        headers=student_headers,
    )
    assert response.status_code == 200


def test_ai_chat_rejects_invalid_history_role(client, student_headers):
    """Test that invalid role in history returns 422."""
    response = client.post(
        "/api/v1/ai/chat",
        json={"message": "Hi", "history": [{"role": "User", "content": "test"}]},
        headers=student_headers,
    )
    assert response.status_code == 422


def test_ai_chat_greetings_are_conversational(client, student_headers):
    """A bare greeting gets a short friendly reply, not an announcement dump."""
    for greeting in ("Hi", "Hello", "Hey", "hello!", "HI"):
        response = client.post(
            "/api/v1/ai/chat",
            json={"message": greeting, "history": []},
            headers=student_headers,
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["success"] is True
        assert "reply" in body
        # Greetings must not trigger a formal announcement list.
        assert "Latest announcements" not in body["reply"]
        # No tools are needed to make small talk.
        assert body["tools_used"] == []


def test_ai_chat_greeting_plus_question_still_routes(client, student_headers):
    """A greeting followed by a real question must still reach the tools."""
    response = client.post(
        "/api/v1/ai/chat",
        json={"message": "Hi, what is my attendance?", "history": []},
        headers=student_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "get_my_attendance" in body["tools_used"]
