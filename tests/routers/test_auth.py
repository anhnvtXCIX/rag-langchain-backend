from sqlalchemy import select

from app.core.security import decode_token
from app.models.user import User


async def test_register_returns_usable_token(client):
    resp = await client.post(
        "/auth/register",
        json={"username": "alice", "email": "alice@example.com", "password": "supersecret1"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    payload = decode_token(body["access_token"])
    assert payload["sub"] == "alice"


async def test_register_duplicate_username_rejected(client):
    payload = {"username": "bob", "email": "bob@example.com", "password": "supersecret1"}
    first = await client.post("/auth/register", json=payload)
    assert first.status_code == 200

    duplicate = await client.post(
        "/auth/register",
        json={**payload, "email": "bob2@example.com"},
    )
    assert duplicate.status_code == 400


async def test_register_duplicate_email_rejected(client):
    payload = {"username": "carol", "email": "carol@example.com", "password": "supersecret1"}
    first = await client.post("/auth/register", json=payload)
    assert first.status_code == 200

    duplicate = await client.post(
        "/auth/register",
        json={**payload, "username": "carol2"},
    )
    assert duplicate.status_code == 400


async def test_login_happy_path(client):
    payload = {"username": "dave", "email": "dave@example.com", "password": "supersecret1"}
    await client.post("/auth/register", json=payload)

    resp = await client.post(
        "/auth/login", json={"username": "dave", "password": "supersecret1"}
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_login_wrong_password_rejected(client):
    payload = {"username": "erin", "email": "erin@example.com", "password": "supersecret1"}
    await client.post("/auth/register", json=payload)

    resp = await client.post(
        "/auth/login", json={"username": "erin", "password": "wrongpassword"}
    )
    assert resp.status_code == 401


async def test_login_unknown_username_rejected(client):
    resp = await client.post(
        "/auth/login", json={"username": "ghost", "password": "supersecret1"}
    )
    assert resp.status_code == 401


async def test_login_inactive_user_forbidden(client, db_session):
    payload = {"username": "frank", "email": "frank@example.com", "password": "supersecret1"}
    await client.post("/auth/register", json=payload)

    result = await db_session.execute(select(User).where(User.username == "frank"))
    user = result.scalar_one()
    user.is_active = False
    await db_session.commit()

    resp = await client.post(
        "/auth/login", json={"username": "frank", "password": "supersecret1"}
    )
    assert resp.status_code == 403


async def test_protected_route_without_token_rejected(client):
    resp = await client.get("/chat/sessions")
    assert resp.status_code in (401, 403)


async def test_protected_route_with_garbage_token_rejected(client):
    resp = await client.get(
        "/chat/sessions", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert resp.status_code == 401
