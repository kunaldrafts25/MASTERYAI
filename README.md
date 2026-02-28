<div align="center">

# MasteryAI

**An AI tutor that actually adapts to you.**

Teaches in one context. Tests in another. If you can transfer the idea, you've mastered it.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=fff)](#)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=fff)](#)
[![Next.js](https://img.shields.io/badge/Next.js-14-000?logo=next.js&logoColor=fff)](#)
[![Llama 3.3](https://img.shields.io/badge/Llama_3.3-70B-FF6F00?logo=meta&logoColor=fff)](#)
[![License](https://img.shields.io/badge/License-MIT-31C754)](#)

</div>

---

MasteryAI is a full-stack adaptive learning platform powered by 9 coordinated AI agents, a 5-layer reinforcement learning engine, SM-2 spaced repetition, and career intelligence. It doesn't just quiz you — it figures out how you learn best and adjusts everything in real-time.

<br>

## Highlights

**Transfer Testing** — Concepts are taught in one real-world context and tested in a completely different one. Memorization won't cut it. Understanding will.

**Multi-Agent Orchestration** — A ReAct-style orchestrator coordinates 9 specialized agents (teacher, examiner, diagnostic, curriculum, motivation, analytics, review scheduler, RL engine, career mapper) — each responsible for one part of the learning experience.

**Reinforcement Learning** — Five bandit and Q-learning layers continuously learn which strategies, difficulty levels, timing, and engagement approaches work best for each individual learner. No hardcoded rules.

**Career Intelligence** — Describe any tech role and MasteryAI generates its skill requirements, maps them to the knowledge graph, calculates your readiness score, and builds a prioritized learning path to get you there.

**Real-Time Streaming** — Every agent action streams to the frontend via SSE. You can watch the system think, decide, teach, and test — as it happens.

<br>

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      Next.js Frontend                        │
│    Session  ·  Knowledge Map  ·  Career  ·  Agent Log        │
│                    SSE Streaming (real-time)                  │
└──────────────────────────┬───────────────────────────────────┘
                           │
                    Nginx Reverse Proxy
                           │
┌──────────────────────────┴───────────────────────────────────┐
│                      FastAPI Backend                          │
│                                                              │
│   ┌────────────────────────────────────────────────────┐     │
│   │               Orchestrator (ReAct)                 │     │
│   │    think  →  select agent  →  act  →  observe      │     │
│   └─────┬──────┬──────┬──────┬──────┬──────┬───────────┘     │
│         │      │      │      │      │      │                 │
│     Teacher Examiner Diag  Review   RL   Career              │
│         │      │      │   Sched   Engine  Mapper             │
│     Curriculum  Analytics  Motivation                        │
│                                                              │
│   ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐    │
│   │  Groq LLM   │  │  Knowledge   │  │  Learner Store  │    │
│   │ (llama-3.3) │  │  Graph       │  │  (SQLite / PG)  │    │
│   └─────────────┘  └──────────────┘  └─────────────────┘    │
└──────────────────────────────────────────────────────────────┘
        │                                         │
   Redis Cache                              PostgreSQL
```

<br>

## Agents

| Agent | Role |
|:------|:-----|
| **Orchestrator** | ReAct loop — reasons about the learner's state and picks the right agent for each step |
| **Teacher** | Generates explanations using RL-selected strategies (analogy, Socratic, worked examples, etc.) |
| **Examiner** | Creates transfer tests — teaches in context A, tests in context B |
| **Diagnostic** | Pre-assessment for experienced learners — probes existing knowledge |
| **Curriculum** | Selects the next concept based on prerequisites, mastery level, and velocity |
| **Review Scheduler** | SM-2 spaced repetition — schedules reviews at mathematically optimal intervals |
| **RL Engine** | 5 bandit + Q-learning layers that learn optimal strategies per learner |
| **Analytics** | Computes velocity, strategy effectiveness, time-of-day patterns, learning insights |
| **Motivation** | Detects engagement states (flow, bored, frustrated) and suggests interventions |
| **Career Mapper** | Maps skills to roles, calculates readiness scores, builds career learning paths |

<br>

## RL Engine

Five layers that replace hardcoded pedagogical rules with learned policies:

| Layer | Algorithm | Learns |
|:------|:----------|:-------|
| **StrategyBandit** | Thompson Sampling | Best teaching strategy per concept |
| **DifficultyBandit** | Thompson Sampling | Optimal difficulty level |
| **ActionQLearner** | Tabular Q-Learning | State → action mapping (teach / test / review / skip) |
| **EngagementBandit** | Thompson Sampling | Best engagement approach per mood |
| **SchedulerBandit** | Thompson Sampling | Optimal review timing multiplier |

<br>

## Tech Stack

| Layer | Technologies |
|:------|:-------------|
| **Backend** | Python 3.11, FastAPI, Pydantic, Groq (Llama 3.3 70B), JWT + bcrypt |
| **Frontend** | Next.js 14, React 18, TypeScript, Tailwind CSS, D3.js, Recharts, Monaco Editor |
| **Data** | PostgreSQL 16, SQLite (dev), Redis 7 |
| **Infra** | Docker Compose, Nginx |

<br>

## Project Structure

```
masteryai/
├── backend/
│   ├── agents/        orchestrator, teacher, examiner, diagnostic, rl_engine, ...
│   ├── auth/          JWT authentication + route guards
│   ├── db/            database connection + schema
│   ├── events/        SSE event bus + streaming utilities
│   ├── models/        pydantic models (learner, concept, career, events)
│   ├── routes/        API endpoints (session, career, analytics, graph, topics)
│   ├── services/      LLM client, knowledge graph, learner store, cache
│   ├── data/          seed data (knowledge_graph.json, career_roles.json)
│   ├── config.py
│   └── main.py
├── frontend/
│   └── src/app/
│       ├── session/        learning interface with SSE streaming
│       ├── knowledge-map/  D3.js interactive knowledge graph
│       ├── career/         career roles + readiness dashboard
│       ├── calibration/    diagnostic pre-assessment
│       ├── agent-log/      real-time agent reasoning viewer
│       └── login/          auth pages
├── tests/             105+ tests (unit, integration, RL, live LLM)
├── docs/              system flow, use cases, roadmap
├── nginx/             reverse proxy config
└── docker-compose.yml
```

<br>

## Quick Start

### Docker (recommended)

```bash
git clone https://github.com/kunaldrafts25/MASTERYAI.git
cd masteryai
echo "GROQ_API_KEY=your_key_here" > .env
docker compose up --build
```

Open **http://localhost** — done.

### Manual

**Backend**

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export GROQ_API_KEY=your_key_here
uvicorn backend.main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend && npm install && npm run dev
```

Open **http://localhost:3000**.

### Mock Mode

No API key? No problem. Run with deterministic mock responses:

```bash
export USE_MOCK_LLM=true
uvicorn backend.main:app --reload --port 8000
```

<br>

## API

### Auth
```
POST  /api/v1/auth/register        Create account
POST  /api/v1/auth/login            Get JWT token
```

### Sessions
```
POST  /api/v1/session/start                Start a learning session
POST  /api/v1/session/{id}/respond         Submit answer or chat
POST  /api/v1/session/start/stream         Start session (SSE)
POST  /api/v1/session/{id}/respond/stream  Respond (SSE)
GET   /api/v1/session/{id}/events          Session event history
```

### Career
```
POST  /api/v1/career/generate-role                     Generate role from description
GET   /api/v1/career/roles                             List all roles
GET   /api/v1/career/roles/{id}                        Role details
GET   /api/v1/career/readiness/{learner_id}/{role_id}  Career readiness score
```

### Analytics & Data
```
GET   /api/v1/analytics/{learner_id}            Full learning analytics
GET   /api/v1/analytics/{learner_id}/patterns   Learning pattern analysis
GET   /api/v1/graph/concepts                    Knowledge graph
GET   /api/v1/topics/                           Available topics
GET   /api/v1/learner/{id}                      Learner profile
```

<br>

## Configuration

| Variable | Default | Description |
|:---------|:--------|:------------|
| `GROQ_API_KEY` | — | Groq API key for LLM calls |
| `USE_MOCK_LLM` | `true` | Use deterministic mock LLM |
| `LLM_MODEL` | `llama-3.3-70b-versatile` | Model to use |
| `DATABASE_URL` | `sqlite:///masteryai.db` | Database connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis for caching |
| `JWT_SECRET` | `change-me-in-production` | JWT signing secret |
| `JWT_EXPIRY_HOURS` | `24` | Token TTL |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed origins |

<br>

## Tests

```bash
python -m pytest tests/ -x -q                    # all tests (mock mode)
python -m pytest tests/test_rl.py -x -q           # RL engine
python -m pytest tests/test_integration.py -q      # multi-turn scenarios
python -m pytest tests/test_career.py -q           # career system
python -m pytest tests/test_auth.py -q             # authentication

GROQ_API_KEY=key python -m pytest tests/test_live.py -q   # live LLM
```

<br>

## How a Session Works

```
1.  Learner picks a topic
2.  Concept generator builds a prerequisite tree via LLM
3.  Diagnostic agent probes existing knowledge (if experienced)
4.  Curriculum agent selects the first concept
5.  RL engine picks the best teaching strategy
6.  Teacher explains the concept in a real-world context
7.  Examiner creates a transfer test in a different context
8.  Learner responds → orchestrator evaluates understanding
9.  SM-2 scheduler queues the concept for spaced review
10. Loop continues — every step adapts based on RL signals
```

Everything streams in real-time via SSE.

<br>

---

<div align="center">
<br>

<samp>"My teachers were teaching with GPT — so I thought, let GPT be my teacher."</samp>

<br>

Built from scratch with curiosity and optimism by **Kunal**

<br>

[![MIT License](https://img.shields.io/badge/License-MIT-31C754?style=flat)](#) &nbsp; [![Star this repo](https://img.shields.io/github/stars/kunaldrafts25/MASTERYAI?style=social)](https://github.com/kunaldrafts25/MASTERYAI)

<sub>If this resonated with you, a star would mean the world.</sub>

<br>
</div>
