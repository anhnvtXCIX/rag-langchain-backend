async def _register(client, username: str) -> dict:
    resp = await client.post(
        "/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "supersecret1",
        },
    )
    assert resp.status_code == 200
    return resp.json()


async def test_upload_valid_txt_document_ends_up_ready(auth_client, fake_pipeline_rag):
    resp = await auth_client.post(
        "/documents/upload",
        files={
            "file": ("notes.txt", b"Some document content to process.", "text/plain")
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["original_filename"] == "notes.txt"

    list_resp = await auth_client.get("/documents")
    assert list_resp.status_code == 200
    documents = list_resp.json()
    assert len(documents) == 1
    assert documents[0]["status"] == "ready"


async def test_upload_disallowed_extension_rejected(auth_client):
    resp = await auth_client.post(
        "/documents/upload",
        files={"file": ("archive.zip", b"content", "application/zip")},
    )
    assert resp.status_code == 400


async def test_upload_disallowed_content_type_rejected(auth_client):
    resp = await auth_client.post(
        "/documents/upload",
        files={"file": ("notes.txt", b"content", "application/octet-stream")},
    )
    assert resp.status_code == 400


async def test_upload_oversized_file_rejected(auth_client):
    oversized = b"a" * (10 * 1024 * 1024 + 1)
    resp = await auth_client.post(
        "/documents/upload",
        files={"file": ("big.txt", oversized, "text/plain")},
    )
    assert resp.status_code == 413


async def test_update_document_reprocesses(auth_client, fake_pipeline_rag):
    upload_resp = await auth_client.post(
        "/documents/upload",
        files={"file": ("notes.txt", b"Original content.", "text/plain")},
    )
    document_id = upload_resp.json()["id"]

    resp = await auth_client.put(f"/documents/{document_id}")
    assert resp.status_code == 200
    # The response reflects the state set synchronously (pending) before the
    # background reprocessing task runs; by the time the request completes
    # (background tasks run in-process), the DB row itself is "ready".
    assert resp.json()["status"] == "pending"

    list_resp = await auth_client.get("/documents")
    assert list_resp.json()[0]["status"] == "ready"


async def test_update_nonexistent_document_returns_404(auth_client):
    resp = await auth_client.put("/documents/999999")
    assert resp.status_code == 404


async def test_delete_document_removes_it(auth_client, fake_pipeline_rag):
    upload_resp = await auth_client.post(
        "/documents/upload",
        files={"file": ("notes.txt", b"Content to delete.", "text/plain")},
    )
    document_id = upload_resp.json()["id"]

    delete_resp = await auth_client.delete(f"/documents/{document_id}")
    assert delete_resp.status_code == 200

    list_resp = await auth_client.get("/documents")
    assert list_resp.json() == []


async def test_delete_nonexistent_document_returns_404(auth_client):
    resp = await auth_client.delete("/documents/999999")
    assert resp.status_code == 404


async def test_user_cannot_access_another_users_document(
    auth_client, client, fake_pipeline_rag
):
    upload_resp = await auth_client.post(
        "/documents/upload",
        files={"file": ("private.txt", b"Private content.", "text/plain")},
    )
    document_id = upload_resp.json()["id"]

    other_user = await _register(client, "other_doc_user")
    other_headers = {"Authorization": f"Bearer {other_user['access_token']}"}

    get_resp = await client.get("/documents", headers=other_headers)
    assert get_resp.json() == []

    put_resp = await client.put(f"/documents/{document_id}", headers=other_headers)
    assert put_resp.status_code == 404

    delete_resp = await client.delete(
        f"/documents/{document_id}", headers=other_headers
    )
    assert delete_resp.status_code == 404
