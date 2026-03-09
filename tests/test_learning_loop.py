import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _register(client):
    res = await client.post("/api/v1/auth/register", json={
        "email": "learner@test.com", "password": "pass1234", "name": "Learner",
    })
    data = res.json()
    return data["token"], data["learner_id"]


async def test_start_session(client):
    token, learner_id = await _register(client)
    res = await client.post(
        "/api/v1/session/start",
        json={"learner_id": learner_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "session_id" in data
    assert "action" in data


async def test_session_respond(client):
    token, learner_id = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}
    start = await client.post("/api/v1/session/start", json={"learner_id": learner_id}, headers=headers)
    session_id = start.json()["session_id"]

    res = await client.post(
        f"/api/v1/session/{session_id}/respond",
        json={"response_type": "answer", "content": "Variables store data in memory"},
        headers=headers,
    )
    assert res.status_code == 200
    assert "action" in res.json()


async def test_graph_public(client):
    res = await client.get("/api/v1/graph")
    assert res.status_code == 200
    data = res.json()
    assert "nodes" in data
    assert len(data["nodes"]) > 0


async def test_career_roles_public(client):
    res = await client.get("/api/v1/career/roles")
    assert res.status_code == 200
    roles = res.json()
    assert len(roles) > 0


async def test_health(client):
    res = await client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["concepts_loaded"] > 0


async def test_react_produces_valid_actions(client):
    token, learner_id = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}
    start = await client.post("/api/v1/session/start", json={"learner_id": learner_id}, headers=headers)
    data = start.json()
    valid_actions = (
        "teach", "decay_check", "complete", "transfer_test", "practice",
        "self_assess", "mastered_and_advance", "mastered_all_done",
        "retest", "reteach", "chat_response", "continue", "error",
        "concept_selected", "mastered", "career_info",
    )
    assert data["action"] in valid_actions


async def test_session_has_agent_reasoning(client):
    token, learner_id = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}
    start = await client.post("/api/v1/session/start", json={"learner_id": learner_id}, headers=headers)
    data = start.json()
    assert "agent_reasoning" in data
    assert len(data["agent_reasoning"]) > 0


async def test_generate_topic(client):
    token, _ = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}
    res = await client.post(
        "/api/v1/topics/generate",
        json={"topic": "machine learning", "depth": 6},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["concepts_generated"] >= 3
    assert data["concepts_added"] >= 3
    assert data["domain"] is not None
    for c in data["concepts"]:
        assert "id" in c
        assert "name" in c
        assert "prerequisites" in c


async def test_generate_then_session(client):
    """Generate concepts for a new topic, then start a session that teaches them."""
    token, learner_id = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    # generate concepts for a fresh topic
    gen = await client.post(
        "/api/v1/topics/generate",
        json={"topic": "rust programming", "depth": 6},
        headers=headers,
    )
    assert gen.status_code == 200
    gen_data = gen.json()
    generated_ids = {c["id"] for c in gen_data["concepts"]}

    # start a learning session — curriculum should pick from ALL domains including generated
    start = await client.post(
        "/api/v1/session/start",
        json={"learner_id": learner_id},
        headers=headers,
    )
    assert start.status_code == 200
    data = start.json()
    assert data["action"] != "complete", "Session should not be complete when concepts exist"
    assert data["action"] in ("teach", "concept_selected", "transfer_test", "decay_check")


async def test_list_domains(client):
    res = await client.get("/api/v1/topics/domains")
    assert res.status_code == 200
    data = res.json()
    assert "domains" in data
    assert data["total_concepts"] > 0
