<div align="center">

# MasteryAI

**An AI tutor that actually adapts to you.**

Teaches in one context. Tests in another. If you can transfer the idea, you've mastered it.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=fff)](#)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=fff)](#)
[![Next.js](https://img.shields.io/badge/Next.js-14-000?logo=next.js&logoColor=fff)](#)
[![Gemini](https://img.shields.io/badge/Gemini_2.0-Flash-4285F4?logo=google&logoColor=fff)](#)
[![License](https://img.shields.io/badge/License-MIT-31C754)](#)

</div>

---

MasteryAI is a full-stack adaptive learning platform powered by 12 coordinated AI agents, a 5-layer reinforcement learning engine, SM-2 spaced repetition, agent deliberation, cross-session memory, and career intelligence. It doesn't just quiz you — it figures out how you learn best and adjusts everything in real-time.

<br>

## Highlights

**Transfer Testing** — Concepts are taught in one real-world context and tested in a completely different one. Memorization won't cut it. Understanding will.

**12-Agent Orchestration** — A ReAct-style orchestrator coordinates 12 specialized agents — teacher, examiner, diagnostic, curriculum, motivation, analytics, review scheduler, RL engine, career mapper, memory, proactive intelligence, and a deliberation protocol that resolves agent conflicts.

**5-Layer Reinforcement Learning** — Thompson Sampling, epsilon-greedy contextual bandits, and Q-Learning continuously learn which strategies, difficulty levels, actions, engagement profiles, and review schedules work best for each individual learner. No hardcoded rules.

**2-Tier Emotional Intelligence** — Tier 1 detects frustration, boredom, disengagement, and flow states with zero LLM calls. Tier 2 triggers deep LLM-powered emotional analysis only when signals warrant it.

**Cross-Session Memory** — A memory agent generates session summaries, teaching reflections, and recalls relevant past context. Detects cross-session patterns via journal tags — so the system remembers your breakthroughs and struggles.

**Career Intelligence** — Describe any tech role and MasteryAI generates its skill requirements, maps them to the knowledge graph, calculates your readiness score, and builds a prioritized learning path to get you there.

**Dynamic Topic Generation** — Type any topic and the system generates a full concept tree (4-15 nodes) with prerequisites, misconceptions, and transfer edges via LLM. No fixed course catalog.

**Real-Time Streaming** — Every agent action streams to the frontend via SSE. You can watch the system think, decide, teach, and test — as it happens.

<br>

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      Next.js Frontend                        │
│    Session  ·  Knowledge Map  ·  Career  ·  Calibration      │
│    Agent Log  ·  Welcome Screen  ·  Auth                     │
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
│         │      │      │                                      │
│     Memory  Proactive  Deliberation  Pedagogy                │
│                                                              │
│   ┌──────────────┐  ┌──────────────┐  ┌────────────────┐    │
│   │ Gemini 2.0   │  │  Knowledge   │  │ Learner Store  │    │
│   │ Flash (LLM)  │  │  Graph       │  │ (SQLite / PG)  │    │
│   └──────────────┘  └──────────────┘  └────────────────┘    │
│                                                              │
│   ┌──────────────┐  ┌──────────────┐  ┌────────────────┐    │
│   │ Tool Library │  │ Message Bus  │  │ LRU + Redis    │    │
│   │ + Composer   │  │ (pub/sub)    │  │ Cache          │    │
│   └──────────────┘  └──────────────┘  └────────────────┘    │
└──────────────────────────────────────────────────────────────┘
        │                                         │
   Redis Cache                              PostgreSQL
```

<br>

## Agents

| Agent | Role |
|:------|:-----|
| **Orchestrator** | ReAct loop — reasons about the learner's state and picks the right agent for each step |
| **Teacher** | Generates explanations using RL-selected strategies (analogy, Socratic, worked examples, debugging, explain-back) |
| **Examiner** | Creates transfer tests — teaches in context A, tests in context B. Self-validates test quality before presenting. |
| **Diagnostic** | Binary-search pre-assessment for experienced learners — probes existing knowledge boundary |
| **Curriculum** | Selects the next concept via transfer-optimized topological sort, detects decayed mastery |
| **Review Scheduler** | SM-2 spaced repetition with adaptive easiness factors, misconception penalties, and retention curves (R = e^(-t/S)) |
| **RL Engine** | 5 bandit + Q-learning layers that learn optimal strategies per learner |
| **Analytics** | Computes velocity, domain affinity, strategy effectiveness, session fatigue curves |
| **Motivation** | 2-tier emotional intelligence — rule-based state detection (Tier 1) + LLM-powered analysis (Tier 2) |
| **Career Mapper** | Maps skills to roles, calculates readiness scores, builds career learning paths |
| **Memory** | Cross-session narrative journal — generates summaries, recalls past context, detects patterns |
| **Proactive** | Predicts frustration risk, memory decay, transfer opportunities, and quick-win concepts |
| **Deliberation** | Multi-agent negotiation protocol — solicits opinions, detects conflicts, resolves via LLM when needed |
| **Pedagogy** | Pure computation (zero LLM) — aggregates signals, estimates readiness, computes blended confidence |
| **Tool Library** | Extended pedagogical tools: analogy, Socratic dialogue, composite exercises, misconception remediation, real-world scenarios |

<br>

## RL Engine

Five layers that replace hardcoded pedagogical rules with learned policies:

| Layer | Algorithm | Learns |
|:------|:----------|:-------|
| **StrategyBandit** | Thompson Sampling | Best teaching strategy per concept (5 strategies) |
| **DifficultyBandit** | Epsilon-greedy contextual | Optimal difficulty level, mastery threshold, retest multiplier |
| **ActionQLearner** | Tabular Q-Learning | State → action mapping (teach / practice / test / reteach / skip / ask) |
| **EngagementBandit** | Epsilon-greedy contextual | Best engagement detection profile per session context |
| **SchedulerBandit** | Epsilon-greedy contextual | Optimal SM-2 parameter profile for long-term retention |

Hyperparameters auto-scale by experience: beginners use high exploration (α=0.2, ε=0.3), veterans converge (α=0.05, ε=0.05).

<br>

## Tech Stack

| Layer | Technologies |
|:------|:-------------|
| **Backend** | Python 3.11, FastAPI, Pydantic v2, Gemini 2.0 Flash (primary), Groq/Llama 3.3 (fallback), JWT + bcrypt |
| **Frontend** | Next.js 14, React 18, TypeScript, Tailwind CSS, D3.js, Recharts, react-markdown |
| **Data** | PostgreSQL 16, SQLite (dev), Redis 7 |
| **Infra** | Docker Compose, Nginx |

<br>

## Project Structure

```
masteryai/
├── backend/
│   ├── agents/        orchestrator, teacher, examiner, diagnostic, rl_engine,
│   │                  curriculum, motivation, memory, proactive, deliberation,
│   │                  analytics, review_scheduler, pedagogy, tool_library, ...
│   ├── auth/          JWT authentication + route guards
│   ├── models/        pydantic models (learner, concept, career, events, journal)
│   ├── routes/        API endpoints (session, career, analytics, graph, topics, learner)
│   ├── services/      LLM client, knowledge graph, learner store, cache,
│   │                  concept generator, career role generator
│   ├── data/          seed data (knowledge_graph.json, career_roles.json)
│   ├── middleware.py  rate limiting (60 req/min per IP)
│   ├── config.py
│   └── main.py
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── session/        chat-based learning interface with SSE
│       │   ├── knowledge-map/  D3.js interactive knowledge graph
│       │   ├── career/         career roles + readiness dashboard
│       │   ├── calibration/    confidence vs mastery analysis
│       │   ├── agent-log/      real-time agent reasoning viewer
│       │   ├── login/          auth pages
│       │   └── register/
│       ├── components/   ChatInput, ChatMessage, ChatSidebar, KnowledgeGraph,
│       │                 MarkdownContent, WelcomeScreen
│       └── lib/          api, auth, sse utilities
├── tests/             112 tests (unit, integration, RL, live LLM)
├── docs/              presentation, system flow, use cases
├── nginx/             reverse proxy config
└── docker-compose.yml
```

<br>

## Quick Start

### Docker (recommended)

```bash
git clone https://github.com/kunaldrafts25/MASTERYAI.git
cd masteryai
echo "GEMINI_API_KEY=your_key_here" > .env
docker compose up --build
```

Open **http://localhost** — done.

### Manual

**Backend**

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY=your_key_here
uvicorn backend.main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend && npm install && npm run dev
```

Open **http://localhost:3000**.

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

### Knowledge Graph
```
GET   /api/v1/graph/                                   Full graph (filterable by domain/learner)
GET   /api/v1/graph/concept/{concept_id}               Concept details
GET   /api/v1/graph/path/{learner_id}/{role_id}        Optimal learning path
```

### Topics
```
POST  /api/v1/topics/generate                          Generate concept tree for any topic
POST  /api/v1/topics/expand                            Expand a concept deeper or laterally
GET   /api/v1/topics/domains                           Available domains
GET   /api/v1/topics/suggestions                       Topic suggestions
```

### Learner
```
GET   /api/v1/learner/{id}/state                       Full learner state
GET   /api/v1/learner/{id}/calibration                 Confidence calibration data
GET   /api/v1/learner/{id}/rl-policy                   RL policy parameters
GET   /api/v1/learner/{id}/reviews                     Scheduled reviews
GET   /api/v1/learner/{id}/retention/{concept_id}      Retention estimate
PUT   /api/v1/learner/{id}/career-target               Set career target
GET   /api/v1/learner/{id}/sessions                    Session history
```

### Analytics
```
GET   /api/v1/analytics/{learner_id}                   Full learning analytics
GET   /api/v1/analytics/{learner_id}/patterns          Learning pattern analysis
```

### Health
```
GET   /api/v1/health                                   Status + concept/role counts + LLM stats
```

<br>

## Configuration

| Variable | Default | Description |
|:---------|:--------|:------------|
| `GEMINI_API_KEY` | — | Google Gemini API key (primary LLM) |
| `GROQ_API_KEY` | — | Groq API key (fallback LLM) |
| `LLM_PROVIDER` | `gemini` | LLM provider (`gemini` or `groq`) |
| `LLM_MODEL` | `gemini-2.0-flash` | Model to use |
| `DATABASE_URL` | `sqlite:///masteryai.db` | Database connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis for caching |
| `JWT_SECRET` | `change-me-in-production` | JWT signing secret |
| `JWT_EXPIRY_HOURS` | `24` | Token TTL |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed origins |
| `LLM_TEMPERATURE` | `0.7` | LLM temperature |
| `LLM_MAX_TOKENS` | `4096` | Max output tokens per LLM call |
| `MAX_REACT_STEPS` | `5` | Max orchestrator reasoning steps |
| `CACHE_MAX` | `1000` | In-memory LRU cache size |

<br>

## Tests

```bash
python -m pytest tests/ -x -q                     # all 112 tests
python -m pytest tests/test_rl.py -x -q            # RL engine (44 tests)
python -m pytest tests/test_integration.py -q       # multi-turn scenarios (28 tests)
python -m pytest tests/test_quant_journey.py -q     # quant analyst journey (11 tests)
python -m pytest tests/test_learning_loop.py -q     # learning loop (10 tests)
python -m pytest tests/test_auth.py -q              # authentication (7 tests)
python -m pytest tests/test_career.py -q            # career system (5 tests)

GEMINI_API_KEY=key python -m pytest tests/test_live.py -q   # live LLM (7 tests)
```

<br>

## How a Session Works

```
1.  Learner picks a topic (or types any topic — system generates a concept tree)
2.  Diagnostic agent probes existing knowledge via binary search (if experienced)
3.  Deliberation protocol runs — 5 agents vote on the best next concept
4.  Curriculum agent finalizes selection via RL-optimized topological sort
5.  Memory agent recalls relevant past context ("last time you struggled with...")
6.  RL engine picks the best teaching strategy via Thompson Sampling
7.  Teacher explains the concept using the selected strategy
8.  Motivation agent monitors emotional state (frustration, boredom, flow)
9.  Examiner creates a transfer test in a different context (self-validated)
10. Learner responds → orchestrator evaluates understanding
11. All 5 RL layers update: strategy, difficulty, action, engagement, scheduler
12. SM-2 scheduler queues the concept for spaced review
13. Memory agent records session summary + teaching reflections in journal
14. Career mapper recalculates readiness scores across all target roles
15. Loop continues — every step adapts based on RL signals
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
