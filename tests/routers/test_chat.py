async def _register(client, username: str) -> dict:
    resp = await client.post(
        "/auth/register",
        json={"username": username, "email": f"{username}@example.com", "password": "supersecret1"},
    )
    assert resp.status_code == 200
    return resp.json()


async def test_create_and_list_sessions(auth_client):
    create_resp = await auth_client.post("/chat/sessions", json={"title": "My chat"})
    assert create_resp.status_code == 200
    session = create_resp.json()
    assert session["title"] == "My chat"

    list_resp = await auth_client.get("/chat/sessions")
    assert list_resp.status_code == 200
    titles = [s["title"] for s in list_resp.json()]
    assert "My chat" in titles


async def test_send_message_with_rag_available(auth_client, fake_rag):
    session_resp = await auth_client.post("/chat/sessions", json={"title": "Q&A"})
    session_id = session_resp.json()["id"]

    resp = await auth_client.post(
        f"/chat/sessions/{session_id}/messages", json={"content": "What is in the docs?"}
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["user_message"]["content"] == "What is in the docs?"
    assert body["assistant_message"]["content"] == "This is a fake generated answer."
    assert body["assistant_message"]["sources"] == [
        {"document_id": 1, "filename": "fake.txt", "snippet": "Fake retrieved chunk content."}
    ]


async def test_send_message_without_llm_configured_returns_503(auth_client):
    session_resp = await auth_client.post("/chat/sessions", json={"title": "No RAG"})
    session_id = session_resp.json()["id"]

    resp = await auth_client.post(
        f"/chat/sessions/{session_id}/messages", json={"content": "Hello?"}
    )
    assert resp.status_code == 503

    # No orphan user message should have been persisted.
    messages_resp = await auth_client.get(f"/chat/sessions/{session_id}/messages")
    assert messages_resp.status_code == 200
    assert messages_resp.json() == []


async def test_send_message_to_nonexistent_session_returns_404(auth_client, fake_rag):
    resp = await auth_client.post(
        "/chat/sessions/999999/messages", json={"content": "Hello?"}
    )
    assert resp.status_code == 404


async def test_list_messages_nonexistent_session_returns_404(auth_client):
    resp = await auth_client.get("/chat/sessions/999999/messages")
    assert resp.status_code == 404


async def test_user_cannot_access_another_users_session(auth_client, client):
    session_resp = await auth_client.post("/chat/sessions", json={"title": "Private"})
    session_id = session_resp.json()["id"]

    other_user = await _register(client, "other_user")
    other_headers = {"Authorization": f"Bearer {other_user['access_token']}"}

    resp = await client.get(
        f"/chat/sessions/{session_id}/messages", headers=other_headers
    )
    assert resp.status_code == 404
