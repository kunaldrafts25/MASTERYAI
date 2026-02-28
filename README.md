<p align="center">
  <img width="100%" src="https://capsule-render.vercel.app/api?type=waving&color=0:0d1117,50:161b22,100:1f6feb&height=200&section=header&text=MasteryAI&fontSize=80&fontColor=58a6ff&fontAlignY=35&desc=An%20adaptive%20learning%20platform%20that%20teaches%20like%20a%20great%20tutor%20%E2%80%94%20not%20a%20textbook.&descSize=16&descColor=8b949e&descAlignY=55&animation=fadeIn" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Next.js-14-000000?style=for-the-badge&logo=next.js&logoColor=white" />
  <img src="https://img.shields.io/badge/Llama_3.3-70B-FF6F00?style=for-the-badge&logo=meta&logoColor=white" />
  <img src="https://img.shields.io/badge/license-MIT-31C754?style=for-the-badge" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black" />
  <img src="https://img.shields.io/badge/TypeScript-5-3178C6?style=flat-square&logo=typescript&logoColor=white" />
  <img src="https://img.shields.io/badge/Tailwind-3.4-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white" />
  <img src="https://img.shields.io/badge/D3.js-7-F9A03C?style=flat-square&logo=d3.js&logoColor=white" />
  <img src="https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/Redis-7-DC382D?style=flat-square&logo=redis&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-compose-2496ED?style=flat-square&logo=docker&logoColor=white" />
</p>

<br>

<p align="center">
MasteryAI is a full-stack AI tutor that adapts in real-time to how you learn.<br>
It combines a multi-agent orchestrator, reinforcement learning, spaced repetition, and career intelligence<br>
to create personalized learning experiences — from your first "hello world" to job-ready proficiency.
</p>

<br>

## &nbsp; What Makes It Different

> **Transfer testing, not memorization.**
> Teaches concepts in one context (say, cooking recipes) and tests them in a completely different one (inventory management). If you can apply the idea in a new situation, you actually understand it.

> **9 specialized agents working together.**
> Instead of one monolithic prompt, a team of agents — teacher, examiner, diagnostic engine, motivation tracker, and more — coordinated through a ReAct-style orchestrator that reasons about what to do next.

> **Reinforcement learning replaces hardcoded rules.**
> Five RL layers (Thompson sampling bandits + Q-learning) continuously learn which teaching strategies, difficulty levels, and engagement approaches work best for each learner.

> **Career-aware learning paths.**
> Tell it you want to become a backend engineer, and it maps your current skills against real role requirements, calculates readiness scores, and builds a prioritized learning path.

<br>

## &nbsp; Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Next.js Frontend                      │
│   Session ← → Knowledge Map ← → Career ← → Analytics   │
│                  SSE Streaming (real-time)               │
└─────────────────────┬───────────────────────────────────┘
                      │
              Nginx Reverse Proxy
                      │
┌─────────────────────┴───────────────────────────────────┐
│                   FastAPI Backend                         │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │              Orchestrator (ReAct)                │    │
│  │   think → select agent → act → observe → loop   │    │
│  └──────┬──────┬──────┬──────┬──────┬──────┬───────┘    │
│         │      │      │      │      │      │            │
│    Teacher  Examiner  Diag  Review  RL   Career        │
│         │      │      │    Sched  Engine  Mapper        │
│         │      │      │      │      │      │            │
│    Curriculum  Analytics  Motivation                     │
│                                                          │
│  ┌──────────────┐  ┌────────────┐  ┌────────────────┐  │
│  │  Groq LLM    │  │  Knowledge │  │  Learner Store │  │
│  │  (llama-3.3) │  │  Graph     │  │  (SQLite/PG)   │  │
│  └──────────────┘  └────────────┘  └────────────────┘  │
└─────────────────────────────────────────────────────────┘
         │                                    │
    Redis Cache                         PostgreSQL
```

<br>

## &nbsp; The Agent System

| Agent | What It Does |
|:------|:-------------|
| **Orchestrator** | ReAct loop — reasons about the learner's state and picks the right agent for each step |
| **Teacher** | Generates explanations using RL-selected strategies (analogy, worked examples, Socratic, etc.) |
| **Examiner** | Creates transfer tests — teaches in context A, tests in context B |
| **Diagnostic** | Pre-assessment for experienced learners — probes what they already know |
| **Curriculum** | Picks the next concept based on prerequisites, mastery, and learning velocity |
| **Review Scheduler** | SM-2 spaced repetition — schedules reviews at optimal intervals |
| **RL Engine** | 5 bandit/Q-learning layers that learn optimal strategies per learner |
| **Analytics** | Computes velocity, strategy effectiveness, time patterns, and learning insights |
| **Motivation** | Detects engagement states (flow, bored, frustrated) and suggests interventions |
| **Career Mapper** | Maps skills to roles, calculates readiness, builds career learning paths |

<br>

## &nbsp; The RL Engine

Five layers that replace hardcoded pedagogical rules with learned policies:

| Layer | Algorithm | What It Learns |
|:------|:----------|:---------------|
| **StrategyBandit** | Thompson Sampling (Beta) | Which teaching strategy works best |
| **DifficultyBandit** | Thompson Sampling (Beta) | Optimal difficulty level |
| **ActionQLearner** | Tabular Q-Learning | State → action mapping (teach, test, review, skip) |
| **EngagementBandit** | Thompson Sampling (Beta) | Best engagement approach per mood |
| **SchedulerBandit** | Thompson Sampling (Beta) | Optimal review timing multiplier |

<br>

## &nbsp; Project Structure

```
masteryai/
├── backend/
│   ├── agents/          # orchestrator, teacher, examiner, diagnostic, etc.
│   ├── auth/            # JWT authentication + route guards
│   ├── db/              # database connection + schema
│   ├── events/          # SSE event bus, streaming utilities
│   ├── models/          # pydantic models (learner, concept, career, events)
│   ├── routes/          # API endpoints (session, career, analytics, etc.)
│   ├── services/        # LLM client, knowledge graph, learner store, cache
│   ├── data/            # seed data (knowledge_graph.json, career_roles.json)
│   ├── config.py        # all settings from env vars
│   └── main.py          # FastAPI app entry point
├── frontend/
│   └── src/app/
│       ├── session/        # main learning interface with SSE streaming
│       ├── knowledge-map/  # D3.js interactive knowledge graph
│       ├── career/         # career roles + readiness dashboard
│       ├── calibration/    # diagnostic pre-assessment
│       ├── agent-log/      # real-time agent reasoning viewer
│       └── login/          # auth pages
├── tests/               # 105+ tests (unit, integration, RL, live LLM)
├── docs/                # system flow, use cases, roadmap
├── nginx/               # reverse proxy config
└── docker-compose.yml   # full stack deployment
```

<br>

## &nbsp; Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- A [Groq API key](https://console.groq.com) (free tier works)

### Quick Start with Docker

```bash
git clone https://github.com/your-username/masteryai.git
cd masteryai

echo "GROQ_API_KEY=your_key_here" > .env

docker compose up --build
```

Open [http://localhost](http://localhost) — the app is ready.

### Manual Setup

<details>
<summary><b>Backend</b></summary>
<br>

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

pip install -r requirements.txt

export GROQ_API_KEY=your_key_here
export USE_MOCK_LLM=false

uvicorn backend.main:app --reload --port 8000
```
</details>

<details>
<summary><b>Frontend</b></summary>
<br>

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).
</details>

<details>
<summary><b>Mock Mode (no API key needed)</b></summary>
<br>

```bash
export USE_MOCK_LLM=true
uvicorn backend.main:app --reload --port 8000
```

The mock LLM returns deterministic responses — great for hacking on the frontend or running tests.
</details>

<br>

## &nbsp; API Reference

<details>
<summary><b>Authentication</b></summary>
<br>

| Method | Path | Description |
|:-------|:-----|:------------|
| `POST` | `/api/v1/auth/register` | Create account |
| `POST` | `/api/v1/auth/login` | Get JWT token |
</details>

<details>
<summary><b>Learning Sessions</b></summary>
<br>

| Method | Path | Description |
|:-------|:-----|:------------|
| `POST` | `/api/v1/session/start` | Start a learning session |
| `POST` | `/api/v1/session/{id}/respond` | Submit an answer or chat |
| `POST` | `/api/v1/session/start/stream` | Start session with SSE streaming |
| `POST` | `/api/v1/session/{id}/respond/stream` | Respond with SSE streaming |
| `GET` | `/api/v1/session/{id}/events` | Get session event history |
</details>

<details>
<summary><b>Career Intelligence</b></summary>
<br>

| Method | Path | Description |
|:-------|:-----|:------------|
| `POST` | `/api/v1/career/generate-role` | Generate a career role from description |
| `GET` | `/api/v1/career/roles` | List all career roles |
| `GET` | `/api/v1/career/roles/{id}` | Get role details |
| `GET` | `/api/v1/career/readiness/{learner_id}/{role_id}` | Calculate career readiness |
</details>

<details>
<summary><b>Analytics & Data</b></summary>
<br>

| Method | Path | Description |
|:-------|:-----|:------------|
| `GET` | `/api/v1/analytics/{learner_id}` | Full learning analytics |
| `GET` | `/api/v1/analytics/{learner_id}/patterns` | Learning pattern analysis |
| `GET` | `/api/v1/graph/concepts` | Knowledge graph data |
| `GET` | `/api/v1/topics/` | Available topics |
| `GET` | `/api/v1/learner/{id}` | Learner profile |
</details>

<br>

## &nbsp; Environment Variables

| Variable | Default | Description |
|:---------|:--------|:------------|
| `GROQ_API_KEY` | — | Groq API key for LLM calls |
| `USE_MOCK_LLM` | `true` | Use mock LLM (no API key needed) |
| `LLM_MODEL` | `llama-3.3-70b-versatile` | Model to use |
| `DATABASE_URL` | `sqlite:///masteryai.db` | Database connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection for caching |
| `JWT_SECRET` | `change-me-in-production` | Secret for JWT signing |
| `JWT_EXPIRY_HOURS` | `24` | Token expiration time |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed CORS origins |
| `LOG_LEVEL` | `INFO` | Logging level |

<br>

## &nbsp; Running Tests

```bash
# all tests (mock mode, no API key needed)
python -m pytest tests/ -x -q

# live LLM tests (needs GROQ_API_KEY)
GROQ_API_KEY=your_key python -m pytest tests/test_live.py -x -q

# specific suites
python -m pytest tests/test_rl.py -x -q        # RL engine
python -m pytest tests/test_integration.py -q   # multi-turn scenarios
python -m pytest tests/test_career.py -q        # career system
python -m pytest tests/test_auth.py -q          # authentication
```

<br>

## &nbsp; How a Session Works

```
 1.  Learner picks a topic (e.g., "Python")
 2.  Concept generator builds a prerequisite tree via LLM
 3.  Diagnostic agent probes what the learner already knows
 4.  Curriculum agent picks the first concept to teach
 5.  RL engine selects the best teaching strategy
 6.  Teacher agent explains the concept in a real-world context
 7.  Examiner creates a transfer test (different context than teaching)
 8.  Learner responds → orchestrator evaluates understanding
 9.  SM-2 scheduler queues the concept for future review
10.  Loop continues — each step adapts based on RL signals
```

All of this streams in real-time via SSE — the frontend shows agent thinking, tool usage, and responses as they happen.

<br>

## &nbsp; License

MIT

<br>

---

<br>

<p align="center">
  <img width="100%" src="https://capsule-render.vercel.app/api?type=waving&color=0:0d1117,50:161b22,100:1f6feb&height=120&section=footer" />
</p>

<p align="center">
  <samp>
    "My teachers were teaching with GPT — so I thought, let GPT be my teacher."
  </samp>
</p>

<p align="center">
  Built from scratch with curiosity and optimism by <b>Kunal</b>
</p>

<p align="center">
  <sub>If this resonated with you, leave a star — it means more than you think.</sub>
</p>
