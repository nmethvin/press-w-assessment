from fastapi.testclient import TestClient

from app.main import app


def test_chat_endpoint_follows_food_context() -> None:
    user_id = "context-test"
    client = TestClient(app)

    first = client.post("/api/chat", json={"user_id": user_id, "message": "i want to make a stew"}).json()
    second = client.post("/api/chat", json={"user_id": user_id, "message": "suggest one"}).json()

    assert first["policy"] == "food"
    assert second["policy"] == "food"
    assert "off-topic" not in second["message"].lower()
