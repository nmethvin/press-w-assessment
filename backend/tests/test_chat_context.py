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


def test_chat_endpoint_returns_active_recipe() -> None:
    user_id = "active-recipe-test"
    client = TestClient(app)

    response = client.post("/api/chat", json={"user_id": user_id, "message": "suggest chicken potato stew"}).json()
    active = client.get(f"/api/active-recipe/{user_id}").json()["active_recipe"]

    assert response["active_recipe"] is not None
    assert active["recipes"][0]["title"] == "Chicken Potato Stew"
