from fastapi.testclient import TestClient

from app.main import app


def test_chat_endpoint_follows_food_context() -> None:
    user_id = "context-test"
    client = TestClient(app)
    chat = client.post(f"/api/chats/{user_id}").json()["chat"]

    first = client.post(
        "/api/chat",
        json={"user_id": user_id, "chat_id": chat["chat_id"], "message": "i want to make a stew"},
    ).json()
    second = client.post(
        "/api/chat",
        json={"user_id": user_id, "chat_id": chat["chat_id"], "message": "suggest one"},
    ).json()

    assert first["policy"] == "food"
    assert second["policy"] == "food"
    assert "off-topic" not in second["message"].lower()


def test_chat_endpoint_returns_active_recipe() -> None:
    user_id = "active-recipe-test"
    client = TestClient(app)
    chat = client.post(f"/api/chats/{user_id}").json()["chat"]

    response = client.post(
        "/api/chat",
        json={"user_id": user_id, "chat_id": chat["chat_id"], "message": "suggest chicken potato stew"},
    ).json()
    loaded = client.get(f"/api/chats/{user_id}/{chat['chat_id']}").json()

    assert response["active_recipe"] is not None
    assert loaded["active_recipe"]["recipes"][0]["title"] == "Chicken Potato Stew"
    assert loaded["messages"][1]["content_payload"]["recipes"][0]["title"] == "Chicken Potato Stew"


def test_new_chat_starts_clean_without_destroying_previous_chat() -> None:
    user_id = "new-chat-test"
    client = TestClient(app)
    first_chat = client.post(f"/api/chats/{user_id}").json()["chat"]

    client.post(
        "/api/chat",
        json={"user_id": user_id, "chat_id": first_chat["chat_id"], "message": "suggest chicken potato stew"},
    )
    second_chat = client.post(f"/api/chats/{user_id}").json()["chat"]
    first_loaded = client.get(f"/api/chats/{user_id}/{first_chat['chat_id']}").json()
    second_loaded = client.get(f"/api/chats/{user_id}/{second_chat['chat_id']}").json()
    chats = client.get(f"/api/chats/{user_id}").json()["chats"]

    assert first_loaded["active_recipe"] is not None
    assert second_loaded["messages"] == []
    assert second_loaded["active_recipe"] is None
    assert {chat["chat_id"] for chat in chats} >= {first_chat["chat_id"], second_chat["chat_id"]}


def test_general_follow_up_preserves_active_recipe() -> None:
    user_id = "preserve-active-recipe-test"
    client = TestClient(app)
    chat = client.post(f"/api/chats/{user_id}").json()["chat"]

    first = client.post(
        "/api/chat",
        json={"user_id": user_id, "chat_id": chat["chat_id"], "message": "suggest chicken potato stew"},
    ).json()
    second = client.post(
        "/api/chat",
        json={"user_id": user_id, "chat_id": chat["chat_id"], "message": "how will i know the chicken is done?"},
    ).json()

    assert first["active_recipe"] is not None
    assert second["policy"] == "food"
    assert second["active_recipe"] is not None
    assert second["active_recipe"]["recipes"][0]["title"] == "Chicken Potato Stew"
