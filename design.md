# MasteryAI — Design Document

**AI-Powered Learning & Career Intelligence Platform**
**February 2026 | Hackathon Idea Submission**

---

## The Problem in One Sentence

Every learning platform today measures **completion** — MasteryAI measures **understanding**.

Students finish courses, earn certificates, and feel confident. Then they fail interviews. The gap between "I completed the course" and "I can actually apply this" is where careers stall and billions in education investment are wasted.

No existing tool validates whether a learner can **transfer** knowledge to a new, unfamiliar context — which is the actual definition of understanding.

---

## The Solution in One Sentence

An autonomous multi-agent AI system where a competing **Examiner** and **Teacher** validate real understanding through LLM-generated transfer tests, track misconceptions across sessions, and map validated skills to career readiness in real-time.

---

## How It Works

```
 LEARNER                         MASTERYAI AGENTS
 ───────                         ────────────────

 "I understand closures"
         │
         ▼
 ┌───────────────────┐
 │  EXAMINER AGENT   │  Generates a problem in a NOVEL context
 │  (Goal: find gaps)│  the learner has NEVER seen before.
 │                   │  Includes traps based on common misconceptions.
 └─────────┬─────────┘
           │
 Learner attempts ──────▶  Examiner evaluates against rubric
           │
      ┌────┴────┐
   PASSED     FAILED
      │          │
      ▼          ▼
 ┌─────────┐ ┌───────────────────┐
 │ MASTERED │ │  TEACHER AGENT    │  Detects the SPECIFIC misconception.
 │          │ │  (Goal: fix gaps) │  Selects a different teaching strategy
 │ Career   │ │                   │  than last time. Targets the exact
 │ readiness│ │  Reteaches, then  │  wrong mental model.
 │ updates  │ │  Examiner retests │
 │ ↑ +3.2%  │ │  in ANOTHER new   │
 └─────────┘ │  context.          │
             └───────────────────┘
```

**The key insight:** The Examiner and Teacher have **competing objectives**. The Examiner tries to *fail* you (find gaps). The Teacher tries to *help* you (fill gaps). This productive tension drives toward genuine mastery — not comfortable completion.

---

## What Makes This Genuinely Novel

| Innovation | What Exists Today | What MasteryAI Does Differently |
|------------|-------------------|---------------------------------|
| **Transfer Testing** | ALEKS: static item banks. Khan Academy: fixed exercises. Duolingo: templates. | LLM generates **unique problems in unfamiliar contexts** every time. Tests application, not recognition. Cannot be gamed. |
| **Misconception Tracking** | No platform tracks *what you incorrectly believe* — only *what you don't know*. | Detects specific misconceptions (e.g., "confuses closure variable capture timing"), tracks them across sessions, and targets remediation. |
| **Confidence Calibration** | Well-studied in psychology. Implemented in zero learning platforms. | Measures the gap between what you *think* you know and what you *actually* know. Treats metacognitive accuracy as a skill. |
| **Competing Agents** | All AI tutors use a single agent that both teaches and tests. | Separate agents with separate goals. Examiner is adversarial. Teacher is supportive. Orchestrator decides what happens next. |
| **Mastery-Gated Career Mapping** | LinkedIn: self-reported skills. Coursera: completion certificates. | Career readiness updates ONLY from transfer-test-validated mastery. Not self-reports. Not certificates. |
| **Cross-Domain Transfer Paths** | Every platform teaches domains in isolation. | Knowledge graph connects concepts across fields. Learning Python closures before web middleware saves ~20% learning time via measured transfer edges. |

**The novelty is not in any single feature — it's in the closed loop:**
Transfer test → Misconception detection → Adaptive reteaching → Re-validation → Career readiness update → Next concept selection — all with persistent state across sessions.

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     FRONTEND (Next.js)                            │
│  Learning Session │ Knowledge Map (D3.js) │ Career Dashboard     │
│  (Chat + Code)    │ (Interactive Graph)    │ (Readiness + Gaps)   │
└────────────────────────────┬─────────────────────────────────────┘
                             │  WebSocket + REST
┌────────────────────────────▼─────────────────────────────────────┐
│                      API LAYER (FastAPI)                          │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│                    ORCHESTRATOR AGENT                              │
│              (State machine — decides what happens next)           │
│                                                                    │
│         ┌──────────┬──────────────┬──────────────┐                │
│         ▼          ▼              ▼              ▼                │
│   ┌──────────┐ ┌────────┐ ┌───────────┐ ┌────────────┐          │
│   │ EXAMINER │ │TEACHER │ │CURRICULUM │ │  CAREER    │          │
│   │          │ │        │ │           │ │  MAPPER    │          │
│   │ Generate │ │ 5 teach│ │ Optimal   │ │            │          │
│   │ transfer │ │ strat- │ │ cross-    │ │ Skill→Role │          │
│   │ tests    │ │ egies  │ │ domain    │ │ mapping    │          │
│   │ Evaluate │ │ Adapt  │ │ learning  │ │ Readiness  │          │
│   │ Detect   │ │ per    │ │ paths     │ │ scores     │          │
│   │ miscon-  │ │ learner│ │           │ │ Gap        │          │
│   │ ceptions │ │        │ │           │ │ analysis   │          │
│   └──────────┘ └────────┘ └───────────┘ └────────────┘          │
│                                                                    │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│                       DATA LAYER                                  │
│                                                                    │
│  Knowledge Graph          Learner State         Career Data       │
│  (33 concepts,            (Per-concept          (5-10 roles,      │
│   3 domains,               mastery, miscon-      skill→concept    │
│   transfer edges,          ceptions, strategy    mappings,        │
│   misconception            history, calibra-     readiness        │
│   templates)               tion data)            scores)          │
│                                                                    │
│  MVP: JSON files          MVP: SQLite            MVP: JSON files  │
│  Prod: Neo4j              Prod: PostgreSQL       Prod: PostgreSQL │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                    Claude API (LLM reasoning engine)
```

### Five Agents, Five Goals

| Agent | Goal | Key Capability |
|-------|------|----------------|
| **Orchestrator** | Maximize learning efficiency | State machine deciding: teach, test, reteach, or advance. Routes events between agents. |
| **Examiner** | Find gaps in understanding | Generates novel transfer tests via LLM. Evaluates responses. Detects specific misconceptions. |
| **Teacher** | Fill gaps effectively | 5 strategies (Socratic, examples, analogy, debugging, explain-back). Selects based on what works for *this* learner. |
| **Curriculum** | Optimal learning path | Cross-domain path optimization. Exploits transfer edges to order concepts for maximum acceleration. |
| **Career Mapper** | Accurate readiness projection | Maps validated mastery → career skills → role readiness. Updates in real-time after every mastery event. |

---

## The Core Learning Loop

```
1. TEACH ──▶ 2. PRACTICE ──▶ 3. SELF-ASSESS ──▶ 4. TRANSFER TEST ──▶ 5. EVALUATE
   │              (same           "Rate your         (NOVEL context,      │
   │              context,         confidence          never-before-       │
   │              build            1-10"               seen, with          │
   │              confidence)                          misconception    ┌──┴──┐
   │                                                   traps)        Pass  Fail
   │                                                                  │     │
   │                                                                  ▼     ▼
   │                                                          ┌──────┐ ┌────────┐
   │                                                          │MASTER│ │DIAGNOSE│
   │                                                          │      │ │miscon- │
   │                                                          │Update│ │ception │
   │                                                          │career│ │        │
   │                                                          │score │ │Switch  │
   │                                                          │      │ │teaching│
   │◀─────────────────── Next concept ────────────────────────│      │ │strategy│
   │                                                          └──────┘ │        │
   │◀──────────────────── Reteach + retest ───────────────────────────│        │
                                                                       └────────┘
```

**The "Holy Shit" Moment (what wins the demo):**
1. Learner self-assesses: "I understand closures — 8/10"
2. System generates transfer test in a context they've never seen (e.g., rate limiter factory)
3. Learner gives the common wrong answer (late-binding misconception)
4. System reveals: **"Confidence: 8/10. Actual: 3/10. Calibration gap: 0.5. Here's exactly where your mental model breaks..."**
5. Targeted reteaching via debugging exercise (code containing their exact misconception)
6. Re-test in yet another new context. Pass.
7. Knowledge graph node turns green. Career readiness ticks up on the dashboard.

---

## Knowledge Graph (Multi-Domain)

```
         PYTHON                          DATA STRUCTURES
  ┌────────────────────┐          ┌─────────────────────┐
  │ variables→control  │          │ arrays → stacks     │
  │ flow→functions→    │          │   │                  │
  │ scope→closures→    │─ ─ ─ ─ ─│→ trees→traversal    │
  │ decorators         │ transfer │                      │
  │     │              │  edges   │ hash_maps → graphs  │
  │ recursion ─ ─ ─ ─ ─│─ ─ ─ ─ ─│→ tree_traversal     │
  │ exceptions ─ ─ ─ ─ │─ ─ ─ ┐  │                      │
  └────────────────────┘      │  └─────────────────────┘
                              │
                              │   WEB DEVELOPMENT
                              │  ┌─────────────────────┐
                              └──│→ error_handling      │
  closures ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │→ middleware           │
  decorators ─ ─ ─ ─ ─ ─ ─ ─ ─ │→ middleware           │
                                 │ http→rest→auth→      │
                                 │ api_design            │
                                 └─────────────────────┘

  ── Prerequisite (must master first)
  ─ ─ Transfer edge (mastery accelerates learning by 12-32%)
```

**33 concepts across 3 domains.** Each concept has:
- Prerequisite chain (enforced ordering)
- Cross-domain transfer edges (learning path optimization)
- Common misconceptions with detection indicators
- Separate teaching contexts and testing contexts (never overlap)
- Mastery criteria (minimum 2 transfer tests passed)

---

## Career Intelligence

Career readiness is **derived from validated mastery only**:

```
Example: Learner targeting "Junior Backend Engineer"

Python Fundamentals  ████████░░░░░ 44%   (4/8 concepts mastered)
Advanced Python      ███░░░░░░░░░░ 19%   (1/4 mastered)
Web Fundamentals     ░░░░░░░░░░░░░  0%   (not started)
Data Handling        █░░░░░░░░░░░░  7%   (0/3 mastered)
API Design           ░░░░░░░░░░░░░  0%   (not started)

Overall Readiness:   ████░░░░░░░░░░░░ 15.8%

Top Gap: Web Fundamentals (+30% impact, ~10.5 hours)
Next Recommended: python.classes (+3.2% readiness impact)
Estimated time to ready: ~42.5 hours
```

The dashboard updates **in real-time** after every mastery event via WebSocket — the learner sees their career score climb as they prove understanding.

---

## Technology Stack

| Layer | Choice | Why |
|-------|--------|-----|
| **Frontend** | Next.js 14 + D3.js + Monaco Editor | Interactive knowledge graph, code editor for exercises, SSR |
| **Backend** | Python FastAPI | Async-native (critical for LLM calls), Pydantic for structured agent I/O |
| **Database** | SQLite (MVP) → PostgreSQL + Neo4j | Zero-config for hackathon; graph DB when concepts exceed 500 |
| **LLM** | Claude API (Sonnet) | Best structured output reliability for inter-agent JSON passing |
| **Real-time** | WebSocket | Live career dashboard updates, streaming teaching content, agent event log |

**Cost estimate:** ~$0.15 per 30-minute learning session. ~$3 total for hackathon demo.

---

## What the Demo Looks Like

**4 screens, 1 live interaction:**

1. **Learning Session** — Chat interface + code editor. Learner interacts with Teacher and Examiner through the Orchestrator.

2. **Knowledge Map** — Interactive D3.js graph. Nodes colored by mastery status (green/yellow/gray). Click any node for details. Transfer edges shown as dotted lines between domains.

3. **Career Dashboard** — Readiness bars per skill. Gap analysis. Trend line showing readiness climbing over sessions. Updates live when a concept is mastered.

4. **Agent Decision Log** — Real-time transparency showing *why* each agent made each decision. "Examiner detected misconception closure_late_binding with 0.85 confidence. Orchestrator switching from Socratic to debugging exercise strategy."

---

## Implementation Feasibility (48-72 Hours)

| Hours | Deliverable |
|:-----:|-------------|
| 0-8 | Data models + knowledge graph (JSON) + LLM client wrapper |
| 8-18 | Examiner Agent (transfer test generation + evaluation) + Teacher Agent (3 strategies) |
| 18-28 | Orchestrator state machine + full learning loop working via API |
| 28-40 | Frontend: session UI, knowledge graph viz, career dashboard, agent log |
| 40-48 | Integration, polish, demo rehearsal |

**What we build:** 15 Python concepts deep, 2 domains shallow, 5 career roles, full transfer testing loop, all 4 UI screens.

**What we scope out (architecture supports, don't build yet):** Spaced repetition scheduling, real job market data, user auth, full curriculum optimization algorithm, mobile responsive.

---

## Competitive Position

```
                    MasteryAI  ChatGPT  Khan Academy  ALEKS  LinkedIn
                    ─────────  ───────  ────────────  ─────  ────────
Transfer Testing      ★★★★★     ☆         ★            ★★      ☆
Misconception Track   ★★★★★     ☆         ★            ★★      ☆
Persistent State      ★★★★      ★         ★★★          ★★★★    ★★
Multi-Domain Graph    ★★★★      ★★★★★     ★★★          ★       ★★★★
Career Mapping        ★★★★      ☆         ☆            ☆       ★★★
Confidence Calibratn  ★★★★★     ☆         ☆            ☆       ☆
Adaptive Teaching     ★★★★      ★★        ★★           ★★★★    ☆
Agent Autonomy        ★★★★      ★         ☆            ★★      ☆
```

**Defensible moat:** Misconception pattern data + teaching strategy effectiveness data + calibration curves compound over time and can't be replicated without users.

---

## Risks We're Honest About

| Risk | Mitigation |
|------|-----------|
| LLM generates bad tests | Pre-validate test templates for all MVP concepts. Self-critique step. Fallback to cached templates. |
| LLM evaluation is unreliable | Constrain response formats. Rubric-based scoring with explicit criteria. Dual evaluation for critical decisions. |
| Learners get frustrated failing | Frame positively ("finding growth edges"). Show progress visually. Sandwich hard tests between wins. |
| Career mapping feels arbitrary | Full transparency on concept→skill→role mapping. Allow user disputes. Humble framing. |
| Big tech copies it | Speed. Data moat from user misconception patterns. Open-source knowledge graph format for ecosystem lock-in. |

---

## Why This Wins

**Problem-Solution Fit:** "Helps people learn faster" is the problem statement. MasteryAI doesn't just help people learn — it **proves** they learned, catches them when they haven't, and connects validated skills to career outcomes.

**Technical Depth:** Multi-agent coordination with competing objectives, persistent learner mental models, LLM-generated adversarial testing — this is not a ChatGPT wrapper.

**Clear Differentiation:** One sentence: *"ChatGPT answers questions. MasteryAI validates answers."*

**Demonstrable in 2 Minutes:** A judge claims 8/10 confidence, scores 3/10, system shows them exactly what they misunderstand, reteaches with a different strategy, re-tests, and their career score climbs. That's the demo.

---

*MasteryAI: The AI tutor that doesn't let you fool yourself.*
