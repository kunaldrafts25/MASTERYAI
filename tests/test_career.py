import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _register(client):
    res = await client.post("/api/v1/auth/register", json={
        "email": "career@test.com", "password": "pass1234", "name": "Career Tester",
    })
    data = res.json()
    return data["token"], data["learner_id"]


async def test_get_all_roles(client):
    res = await client.get("/api/v1/career/roles")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
    assert len(res.json()) >= 1


async def test_get_role_detail(client):
    roles_res = await client.get("/api/v1/career/roles")
    role_id = roles_res.json()[0]["id"]
    res = await client.get(f"/api/v1/career/roles/{role_id}")
    assert res.status_code == 200
    assert res.json()["id"] == role_id


async def test_role_not_found(client):
    res = await client.get("/api/v1/career/roles/nonexistent_role")
    assert res.status_code == 404


async def test_readiness(client):
    token, learner_id = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}
    roles_res = await client.get("/api/v1/career/roles")
    role_id = roles_res.json()[0]["id"]

    res = await client.get(f"/api/v1/career/readiness/{learner_id}/{role_id}", headers=headers)
    assert res.status_code == 200
    assert "readiness" in res.json()
    assert 0 <= res.json()["readiness"]["overall_score"] <= 1


async def test_update_career_targets(client):
    token, learner_id = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}
    res = await client.put(
        f"/api/v1/learner/{learner_id}/career-target",
        json={"role_ids": ["junior_python_developer"]},
        headers=headers,
    )
    assert res.status_code == 200
    assert "junior_python_developer" in res.json()["career_targets"]
