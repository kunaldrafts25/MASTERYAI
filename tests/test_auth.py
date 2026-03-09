import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_register(client):
    res = await client.post("/api/v1/auth/register", json={
        "email": "alice@test.com", "password": "pass1234", "name": "Alice",
    })
    assert res.status_code == 200
    data = res.json()
    assert "token" in data
    assert "learner_id" in data


async def test_register_duplicate(client):
    await client.post("/api/v1/auth/register", json={
        "email": "dup@test.com", "password": "pass1234", "name": "Dup1",
    })
    res = await client.post("/api/v1/auth/register", json={
        "email": "dup@test.com", "password": "pass1234", "name": "Dup2",
    })
    assert res.status_code == 409


async def test_login(client):
    await client.post("/api/v1/auth/register", json={
        "email": "bob@test.com", "password": "secret99", "name": "Bob",
    })
    res = await client.post("/api/v1/auth/login", json={
        "email": "bob@test.com", "password": "secret99",
    })
    assert res.status_code == 200
    assert "token" in res.json()


async def test_login_wrong_password(client):
    await client.post("/api/v1/auth/register", json={
        "email": "carol@test.com", "password": "right123", "name": "Carol",
    })
    res = await client.post("/api/v1/auth/login", json={
        "email": "carol@test.com", "password": "wrong123",
    })
    assert res.status_code == 401


async def test_protected_route_no_token(client):
    res = await client.get("/api/v1/learner/fake-id/state")
    assert res.status_code in (401, 403)


async def test_protected_route_with_token(client):
    reg = await client.post("/api/v1/auth/register", json={
        "email": "dave@test.com", "password": "pass1234", "name": "Dave",
    })
    data = reg.json()
    res = await client.get(
        f"/api/v1/learner/{data['learner_id']}/state",
        headers={"Authorization": f"Bearer {data['token']}"},
    )
    assert res.status_code == 200
    assert res.json()["learner_id"] == data["learner_id"]


async def test_cannot_access_other_learner(client):
    reg1 = await client.post("/api/v1/auth/register", json={
        "email": "eve@test.com", "password": "pass1234", "name": "Eve",
    })
    reg2 = await client.post("/api/v1/auth/register", json={
        "email": "frank@test.com", "password": "pass1234", "name": "Frank",
    })
    res = await client.get(
        f"/api/v1/learner/{reg2.json()['learner_id']}/state",
        headers={"Authorization": f"Bearer {reg1.json()['token']}"},
    )
    assert res.status_code == 403
