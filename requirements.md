# Requirements Document: MasteryAI — AI-Powered Learning & Career Intelligence Platform

**Version:** 1.0
**Date:** February 2026
**Status:** Idea Submission / First Round
**Author:** Technical Founder

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Problem Definition](#2-problem-definition)
3. [Target Users](#3-target-users)
4. [Functional Requirements](#4-functional-requirements)
5. [Non-Functional Requirements](#5-non-functional-requirements)
6. [System Constraints](#6-system-constraints)
7. [Data Requirements](#7-data-requirements)
8. [Integration Requirements](#8-integration-requirements)
9. [Success Criteria & Metrics](#9-success-criteria--metrics)
10. [Assumptions & Dependencies](#10-assumptions--dependencies)
11. [Glossary](#11-glossary)

---

## 1. Project Overview

### 1.1 Vision Statement

MasteryAI is an autonomous, multi-agent AI system that transforms how people learn and plan careers. Instead of delivering content and hoping learners absorb it, MasteryAI operates as a **mastery certification engine that teaches as a side effect** — validating true understanding through LLM-generated transfer tests, maintaining persistent learner mental models, and connecting validated skills to real career outcomes.

### 1.2 Problem Statement Alignment

> **Hackathon Problem:** Build an AI-powered solution that helps people learn faster, work smarter, or become more productive while building or understanding technology.

MasteryAI directly addresses this across all four suggested categories:

| Category | How MasteryAI Addresses It |
|----------|---------------------------|
| **Learning assistants/tutors** | Autonomous AI tutor with adversarial mastery validation, adaptive teaching strategies, and persistent learner modeling |
| **Developer productivity tools** | Validates real engineering skills, eliminates wasted time on ineffective learning paths, shows precise skill gaps for career targets |
| **AI tools that simplify complex concepts** | Multi-domain knowledge graph connects concepts across fields, shows how skills transfer and combine |
| **Knowledge organization / skill-building** | Evidence-based skill building with objective mastery metrics, cross-domain knowledge synthesis, career-aligned learning paths |

### 1.3 Core Innovation Thesis

Current AI tutors are **stateless responders** — they answer questions without knowing what you actually understand. MasteryAI is fundamentally different in five ways:

1. **Transfer Testing:** LLM generates novel problems in unfamiliar contexts to validate real understanding, not pattern recognition
2. **Persistent Mental Models:** System maintains evolving model of each learner's knowledge, misconceptions, and learning patterns across sessions
3. **Competing Agent Architecture:** An Examiner agent tries to find gaps while a Teacher agent tries to fill them — productive tension drives mastery
4. **Cross-Domain Intelligence:** Knowledge graph connects concepts across subjects, identifying transfer opportunities and prerequisite chains
5. **Mastery-Gated Career Mapping:** Career readiness is derived from validated skills only — not self-reports, not certificates, not course completions

---

## 2. Problem Definition

### 2.1 Problem 1: The Illusion of Mastery (False Confidence)

**Description:** Learners consistently overestimate their understanding. They watch tutorials, follow along, and believe they comprehend the material. When faced with novel problems requiring application of that knowledge, they fail. This is the Dunning-Kruger effect applied to learning — the less you truly understand, the more confident you feel.

**Evidence:**
- Dunning-Kruger effect is well-documented across educational research
- Bootcamp graduates consistently report readiness but fail technical interviews
- Self-paced online courses have <15% completion rates, and completers often can't apply skills
- No existing platform validates transfer of learning to novel contexts

**Impact:** Learners enter job markets unprepared, face rejection, lose confidence, and waste months or years on ineffective learning. Employers waste resources on candidates whose certificates don't reflect real ability.

**Requirement Derived:** The system MUST validate understanding through transfer testing — generating novel problems in contexts the learner has NOT seen, requiring application rather than recognition.

### 2.2 Problem 2: Disconnected Learning Experiences

**Description:** Current platforms teach skills in isolation. A learner studies Python on one platform, algorithms on another, databases on a third. No system connects these domains to show how concepts reinforce each other, what the prerequisite chains are, or how skill combinations create career capabilities.

**Evidence:**
- Online learning platforms organize by course, not by concept
- No system tracks how mastering recursion in Python accelerates learning tree traversal in data structures
- Learners accumulate random skills without strategic direction
- Career advice platforms don't understand learning dependencies

**Impact:** Random skill accumulation without clear direction. Learners don't know what to learn next, what they're missing, or how their skills combine.

**Requirement Derived:** The system MUST maintain a multi-domain knowledge graph with explicit prerequisite edges, cross-domain transfer edges, and concept-to-skill mappings. Learning paths MUST leverage transfer opportunities across domains.

### 2.3 Problem 3: Career Path Opacity

**Description:** Career planning relies on subjective methods — personality tests, interest surveys, generic advice. Job descriptions list requirements but don't provide learning paths. No system objectively measures "readiness" for a specific role based on validated competencies.

**Evidence:**
- 40% of college graduates work in jobs not requiring their degree (Federal Reserve)
- 60% of learners report confusion about career paths (LinkedIn Learning survey)
- Career counseling uses outdated information and personal bias
- No platform connects validated skill levels to specific job role requirements

**Impact:** People make expensive, high-stakes career decisions based on guesswork. Education investments are misaligned with career outcomes.

**Requirement Derived:** The system MUST map validated mastery scores to specific career role requirements, provide real-time career readiness projections, identify precise skill gaps, and generate optimized learning paths toward target roles.

### 2.4 Problem 4: Static, Non-Adaptive Systems

**Description:** Current learning tools are reactive — they respond when asked. They have no memory of the learner's evolving understanding, no ability to detect and track misconceptions over time, and no autonomous goal-seeking behavior. Every session starts from scratch.

**Evidence:**
- ChatGPT has no persistent memory of your knowledge state
- Khan Academy tracks completion but not misconception patterns
- No platform adapts teaching strategy based on what has historically worked for the individual
- ALEKS comes closest with knowledge spaces but uses static item banks, not generative testing

**Impact:** One-size-fits-all education that fails most learners. Teaching strategies that don't work are repeated. Misconceptions go undetected and compound.

**Requirement Derived:** The system MUST maintain persistent learner state across sessions, track misconceptions individually, adapt teaching strategies based on measured effectiveness per learner, and operate autonomously with goal-driven behavior.

---

## 3. Target Users

### 3.1 Primary Users

#### Self-Directed Learners (Career Changers, Upskilling Professionals)
- **Profile:** Adults learning technology skills for career advancement or transition
- **Pain Point:** Unsure if they actually understand what they've studied; don't know what to learn next
- **Need:** Validated skill assessment, clear learning path to career goal, confidence calibration
- **Example:** "I've been learning Python for 3 months from YouTube. Am I actually job-ready?"

#### Computer Science Students
- **Profile:** University students or bootcamp participants studying CS fundamentals
- **Pain Point:** Courses move at fixed pace; can't assess own gaps; exam feedback is delayed
- **Need:** Real-time mastery validation, misconception detection before exams, cross-course connections
- **Example:** "I passed the midterm but I still can't write a recursive function from scratch."

#### Junior Developers (First 1-3 Years)
- **Profile:** Early-career developers wanting to level up systematically
- **Pain Point:** Don't know what they don't know; imposter syndrome vs. actual gaps
- **Need:** Objective skill assessment, targeted gap-filling, career progression mapping
- **Example:** "I want to become a senior engineer. What specific skills am I missing?"

### 3.2 Secondary Users (Future Phases)

#### Hiring Managers / Technical Recruiters
- **Need:** Verified skill assessments for candidates (replace whiteboard interviews)
- **Value:** MasteryAI mastery certificates backed by transfer test data

#### Educators / Course Creators
- **Need:** Analytics on where learners consistently struggle; misconception data
- **Value:** Improve course content based on real misconception patterns

#### Organizations (L&D Teams)
- **Need:** Workforce skill mapping, upskilling program effectiveness measurement
- **Value:** Objective data on team skill levels and training ROI

---

## 4. Functional Requirements

### 4.1 Multi-Agent System (FR-AGENT)

#### FR-AGENT-01: Orchestrator Agent
The system SHALL implement an Orchestrator Agent that:
- Receives all events from specialist agents and learner interactions
- Maintains the master learner state
- Decides the next action in the learning loop (teach, test, review, advance, diagnose)
- Dispatches tasks to specialist agents
- Operates as a goal-driven state machine with defined transitions
- Handles failures gracefully (agent timeout, LLM errors, ambiguous results)

#### FR-AGENT-02: Examiner Agent
The system SHALL implement an Examiner Agent that:
- Generates transfer tests using LLM for any concept in the knowledge graph
- Creates problems in contexts the learner has NOT previously encountered
- Designs adversarial distractors based on known misconceptions for the concept
- Produces structured rubrics for evaluating learner responses
- Evaluates free-form responses against rubrics with misconception detection
- Assigns mastery scores (0.0-1.0) and confidence calibration gaps
- Generates tests at multiple difficulty tiers:
  - Tier 1: Application in familiar context (practice)
  - Tier 2: Application in novel context (transfer test)
  - Tier 3: Application with edge cases and adversarial conditions (deep mastery)
  - Tier 4: Cross-domain application requiring concept synthesis

#### FR-AGENT-03: Teacher Agent
The system SHALL implement a Teacher Agent that:
- Teaches concepts using multiple strategies: Socratic questioning, worked examples, analogy-based explanation, debugging exercises, explain-back prompts
- Selects teaching strategy based on learner profile (what has worked best for this individual)
- Adapts in real-time if selected strategy isn't working (within a session)
- Addresses specific detected misconceptions with targeted remediation
- Uses research data (search results, scraped content) to provide current, relevant examples
- Tracks strategy effectiveness per learner per concept

#### FR-AGENT-04: Curriculum Agent
The system SHALL implement a Curriculum Agent that:
- Generates optimal learning paths through the knowledge graph
- Respects prerequisite constraints (cannot learn X before mastering Y)
- Exploits cross-domain transfer opportunities (learns concepts in the order that maximizes transfer)
- Adjusts paths in real-time as mastery data changes
- Accounts for individual learning velocity per domain
- Handles multiple career targets simultaneously (union of required skills)
- Re-plans when teaching fails repeatedly (alternative concept ordering)

#### FR-AGENT-05: Career Mapper Agent
The system SHALL implement a Career Mapper Agent that:
- Maps validated mastery scores to career role requirements
- Calculates real-time career readiness scores (0.0-1.0) per target role
- Identifies precise skill gaps with estimated time-to-close
- Generates skill-to-role breakdowns showing which concepts contribute to which requirements
- Updates projections after every mastery event
- Supports multiple simultaneous career targets
- Incorporates job market demand data (future: real-time; MVP: curated dataset)

### 4.2 Mastery Validation System (FR-MASTERY)

#### FR-MASTERY-01: Transfer Test Generation
The system SHALL generate transfer tests that:
- Present the target concept in a context the learner has NOT previously encountered
- Require genuine application of understanding, not pattern matching or recall
- Include scenarios where common misconceptions lead to plausible but incorrect answers
- Are unique per generation (not drawn from a fixed item bank)
- Include structured rubrics with scoring criteria
- Support multiple response formats: free-text explanation, code writing, multiple-choice with justification, debugging exercises

#### FR-MASTERY-02: Misconception Detection
The system SHALL detect and track misconceptions by:
- Maintaining a library of common misconceptions per concept (pre-authored + LLM-discovered)
- Analyzing learner responses for misconception indicators
- Distinguishing between "doesn't know" (lack of knowledge) and "knows wrong" (active misconception)
- Tracking misconception resolution over time (detected → addressed → resolved → verified)
- Using misconception data to inform future test generation and teaching

#### FR-MASTERY-03: Confidence Calibration
The system SHALL track learner confidence calibration by:
- Requesting self-assessment before transfer tests (1-10 confidence rating)
- Comparing self-assessment to actual transfer test performance
- Computing calibration gap (self-reported confidence minus actual mastery score)
- Tracking calibration trends over time (improving, stable, persistently overconfident)
- Displaying calibration data to learners as a metacognitive tool
- Using calibration data to prioritize testing (high-confidence, low-mastery concepts first)

#### FR-MASTERY-04: Mastery Scoring
The system SHALL assign mastery scores using:
- Transfer test performance (primary signal, weighted 60%)
- Explanation quality when asked to teach the concept back (weighted 20%)
- Consistency across multiple test contexts (weighted 10%)
- Time decay — mastery degrades without periodic re-validation (weighted 10%)
- Clear thresholds: <0.4 = not mastered, 0.4-0.7 = partial, ≥0.7 = mastered
- Requirement: minimum 2 transfer tests passed in different contexts for "mastered" status

### 4.3 Knowledge Graph (FR-GRAPH)

#### FR-GRAPH-01: Concept Representation
Each concept in the knowledge graph SHALL include:
- Unique identifier, name, and domain classification
- Description and difficulty tier (1-5)
- Prerequisite concepts (directed edges, must be mastered before this concept)
- Cross-domain transfer edges (with transfer strength 0.0-1.0 and description)
- Common misconceptions (with indicators and remediation strategies)
- Mastery criteria (number of transfer tests required, minimum score, decay period)
- Teaching contexts (contexts used during instruction — separate from testing contexts)
- Testing contexts (reserved for transfer test generation, NOT used in teaching)

#### FR-GRAPH-02: Multi-Domain Support
The knowledge graph SHALL:
- Support unlimited domain definitions (MVP: 3 domains — Python, Data Structures, Web Development)
- Define cross-domain transfer edges explicitly (e.g., "recursion" in Python → "tree traversal" in Data Structures)
- Support concept composition (multiple concepts combine to form a "skill" required by career roles)
- Allow independent domain expansion without modifying existing domains
- Enforce domain-specific mastery criteria where appropriate

#### FR-GRAPH-03: Knowledge Graph Operations
The system SHALL support:
- Prerequisite chain resolution (transitive closure — all prerequisites of prerequisites)
- Transfer opportunity identification (what mastered concepts accelerate unmastered ones?)
- Optimal path computation (shortest path from current state to target skill set, weighted by estimated learning time and transfer bonuses)
- Concept dependency visualization (interactive graph showing mastered/unmastered/in-progress)

### 4.4 Learner State Management (FR-STATE)

#### FR-STATE-01: Persistent Learner Profile
The system SHALL maintain per-learner state including:
- Per-concept mastery data: status, score, confidence, calibration gap, misconceptions, test history, strategy effectiveness
- Learning profile: overall velocity, domain-specific velocities, preferred teaching strategy, calibration trend, engagement pattern
- Career targets with readiness scores and skill gap analyses
- Full session history (for audit and adaptation)

#### FR-STATE-02: State Persistence
- Learner state SHALL persist across sessions (stored in database, not in-memory only)
- State SHALL be updated in real-time as events occur (not batched)
- State history SHALL be queryable (track how mastery evolved over time)
- State SHALL support export (learner owns their data)

#### FR-STATE-03: Time Decay & Spaced Repetition
- Mastery scores SHALL decay over time based on configurable decay curves
- The system SHALL schedule re-validation tests for decaying concepts
- Decay rate SHALL be personalized (learners who demonstrate strong initial mastery decay slower)
- Spaced repetition intervals SHALL follow evidence-based schedules (modified SM-2 algorithm adapted for transfer tests rather than flashcards)

### 4.5 Career Intelligence (FR-CAREER)

#### FR-CAREER-01: Role Database
The system SHALL maintain a career role database including:
- Role title, description, and level (junior, mid, senior)
- Required skills (composed of knowledge graph concepts with minimum mastery thresholds)
- Nice-to-have skills (additional concepts that increase readiness score)
- Market demand indicator (growing, stable, declining)
- Salary range data
- Related roles (for career path exploration)

#### FR-CAREER-02: Readiness Calculation
Career readiness SHALL be calculated as:
- Weighted sum of validated mastery scores for required skills
- Weights based on skill importance to the role
- Only transfer-test-validated mastery counts (not self-reported, not course completion)
- Score range: 0.0 (no relevant skills) to 1.0 (all required skills mastered)
- Granular breakdown showing per-skill readiness

#### FR-CAREER-03: Gap Analysis
The system SHALL provide:
- Ordered list of missing skills for each target role
- Estimated hours to close each gap (based on learner's measured velocity)
- Recommended learning sequence (respecting prerequisites and transfer opportunities)
- Comparison across target roles (which role is closest? which has best ROI?)

### 4.6 User Interface (FR-UI)

#### FR-UI-01: Learning Session Interface
- Chat-like interface for learning interactions (teacher/examiner exchanges)
- Code editor component for programming exercises
- Real-time feedback on responses
- Session context display (current concept, progress in learning path)
- Confidence self-assessment prompts before tests

#### FR-UI-02: Knowledge Map Visualization
- Interactive graph visualization of the knowledge graph
- Color-coded nodes: mastered (green), in-progress (yellow), untouched (gray), decayed (orange)
- Edge visualization showing prerequisites and transfer connections
- Zoom/filter by domain
- Click-to-inspect concept details and mastery data

#### FR-UI-03: Career Dashboard
- Career readiness score per target role (bar chart / radial chart)
- Skill gap breakdown per role
- Time-to-ready estimates
- Recommended next concepts prioritized by career impact
- Historical readiness trend line

#### FR-UI-04: Calibration Dashboard
- Confidence vs. actual mastery scatter plot (per concept)
- Calibration trend over time (line chart)
- Highlighting concepts with largest calibration gaps
- Metacognitive insights ("You tend to overestimate your understanding of X-type concepts")

#### FR-UI-05: Agent Decision Log (Transparency)
- Display what agents decided and why (human-readable summaries)
- Show which teaching strategy was selected and why
- Show why specific transfer test contexts were chosen
- Builds trust and demonstrates autonomous agent behavior to hackathon judges

### 4.7 Research & Content Pipeline (FR-RESEARCH)

#### FR-RESEARCH-01: Search Integration
- The system SHALL search for current information on topics using web search APIs (Serper/Google)
- Search results SHALL inform teaching examples and transfer test contexts
- The system SHALL extract "People Also Ask" data for generating relevant test questions

#### FR-RESEARCH-02: Content Scraping
- The system SHALL scrape top search results for detailed content
- Scraped content SHALL be summarized and used as teaching material context
- Content SHALL be cached to avoid redundant API calls

---

## 5. Non-Functional Requirements

### 5.1 Performance (NFR-PERF)

| Metric | Hackathon Target | Production Target |
|--------|-----------------|-------------------|
| Transfer test generation latency | <5 seconds | <2 seconds |
| Response evaluation latency | <3 seconds | <1.5 seconds |
| Teaching response latency | <3 seconds | <2 seconds |
| Knowledge graph query latency | <100ms | <50ms |
| Learner state read/write | <200ms | <100ms |
| Career readiness recalculation | <500ms | <200ms |
| UI initial load time | <3 seconds | <1.5 seconds |

### 5.2 Scalability (NFR-SCALE)

| Metric | Hackathon | 6-Month Target | 12-Month Target |
|--------|-----------|----------------|-----------------|
| Concurrent learners | 1-5 (demo) | 500 | 10,000 |
| Knowledge graph concepts | 30-50 | 500+ | 2,000+ |
| Domains | 3 | 10+ | 20+ |
| Career roles | 5-10 | 50+ | 200+ |
| Session history per learner | 10 sessions | 500 sessions | Unlimited |

### 5.3 Reliability (NFR-REL)

- System SHALL handle LLM API failures gracefully (retry with backoff, fallback to cached test templates)
- System SHALL not lose learner state on crash (write-ahead logging or transactional writes)
- System SHALL handle malformed LLM responses (JSON parsing failures, rubric inconsistencies)
- Agent failures SHALL not crash the system — Orchestrator degrades gracefully

### 5.4 Security (NFR-SEC)

- Learner data SHALL be stored securely (encrypted at rest for production)
- LLM API keys SHALL not be exposed to the client
- User authentication SHALL be implemented (production; hackathon may use demo mode)
- Learner data SHALL be exportable and deletable (GDPR-style data rights)

### 5.5 Observability (NFR-OBS)

- All agent decisions SHALL be logged with reasoning
- LLM call latency, token usage, and cost SHALL be tracked
- Mastery validation outcomes SHALL be tracked for system-level analysis
- Error rates per agent SHALL be monitored

### 5.6 Cost Efficiency (NFR-COST)

| Metric | Target |
|--------|--------|
| LLM cost per learning session (30 min) | <$0.15 (Sonnet) |
| LLM cost per transfer test generation | <$0.01 |
| LLM cost per response evaluation | <$0.005 |
| Monthly infrastructure (production, 1K users) | <$200 |
| Cache hit rate for test templates | >40% |

---

## 6. System Constraints

### 6.1 Technical Constraints

- **LLM Dependency:** Core functionality requires LLM API access (Claude or GPT-4). System cannot function without it. Mitigation: cache templates, pre-generate tests.
- **LLM Output Reliability:** LLM may produce malformed JSON, inconsistent rubrics, or low-quality tests. Mitigation: structured output schemas, validation layers, retry logic.
- **Latency Floor:** LLM inference has inherent latency (500ms-3s). Mitigation: speculative pre-generation, streaming responses, parallel agent execution.
- **Knowledge Graph Authoring:** Initial knowledge graph requires manual curation. Mitigation: start narrow (3 domains), expand systematically with structured templates.
- **Single-Player Only (MVP):** No collaborative or social features. Individual learner focus.

### 6.2 Scope Constraints

- **No content hosting:** MasteryAI validates mastery and teaches interactively. It does NOT host videos, courses, or static content.
- **No job board:** Career mapping shows readiness, not job listings. Not a recruitment platform.
- **No VR/AR:** All interactions via web interface.
- **No blockchain/Web3:** Credentials stored in standard database.
- **No model training:** Uses existing LLM APIs, does not train custom models.

### 6.3 Hackathon-Specific Constraints

- **Timeline:** 48-72 hours from idea approval to demo
- **Team Size:** 1-2 engineers
- **Budget:** <$50 in API costs for development + demo
- **Demo Duration:** 2-5 minute live demonstration
- **Infrastructure:** Must deploy without complex infrastructure (single server, managed services)

---

## 7. Data Requirements

### 7.1 Knowledge Graph Data

#### MVP Domains and Concept Counts

**Domain 1: Python Programming (15 concepts)**
- Variables & Types, Control Flow, Functions, Scope & Namespaces, Closures, Recursion, List Comprehensions, Generators, Decorators, Classes & Objects, Inheritance, Exception Handling, File I/O, Modules & Packages, Async Basics

**Domain 2: Data Structures (10 concepts)**
- Arrays & Lists, Stacks, Queues, Hash Maps, Linked Lists, Trees (Binary), Tree Traversal, Graphs, Sorting Algorithms, Search Algorithms

**Domain 3: Web Development Fundamentals (8 concepts)**
- HTTP Protocol, REST APIs, Request/Response Cycle, Authentication Basics, Database Queries (SQL), API Design, Middleware Concepts, Error Handling in APIs

**Cross-Domain Transfer Edges (examples):**
- Python:Recursion → DS:Tree Traversal (strength: 0.7)
- Python:Closures → Web:Middleware (strength: 0.5)
- Python:Decorators → Web:Middleware (strength: 0.6)
- Python:Exception Handling → Web:Error Handling (strength: 0.8)
- DS:Hash Maps → Web:Database Queries (strength: 0.3)
- Python:Async → Web:Request/Response (strength: 0.6)

#### Misconception Library (Examples)

| Concept | Misconception ID | Description | Indicator |
|---------|-----------------|-------------|-----------|
| Closures | closure_late_binding | Confuses closure variable capture timing | Expects loop closure to capture iteration value |
| Recursion | recursion_vs_iteration | Thinks recursion is just a different loop syntax | Cannot identify when recursion is necessary vs. iteration |
| Scope | scope_vs_closure | Confuses function scope with closure capture | Cannot explain variable lifetime after function returns |
| Mutable Defaults | mutable_default_shared | Doesn't know default args are evaluated once | Uses mutable default without realizing shared state |
| Inheritance | is_a_vs_has_a | Uses inheritance where composition is appropriate | Creates deep inheritance hierarchies for unrelated concepts |
| Hash Maps | hash_collision_ignored | Assumes hash maps are O(1) always | Cannot reason about worst-case performance |
| REST | rest_vs_rpc | Treats REST as remote procedure call | Designs APIs around verbs instead of resources |
| SQL | join_confusion | Cannot distinguish join types | Incorrect results on LEFT JOIN vs INNER JOIN |

### 7.2 Career Role Data (MVP)

| Role | Required Concepts | Level |
|------|------------------|-------|
| Junior Python Developer | Variables, Control Flow, Functions, Scope, Classes, Exceptions, File I/O, Modules | Entry |
| Junior Backend Engineer | All Python + REST APIs, HTTP, Database Queries, Auth, Error Handling | Entry |
| Data Structures TA | All Python + All DS concepts | Entry |
| Junior Full-Stack Developer | All Python + All Web + Lists, Hash Maps, Trees | Mid |
| ML Engineer (Entry) | All Python + All DS + Recursion deep mastery, Generators, Decorators | Mid |

### 7.3 Learner Data (Generated)

- Per-concept mastery scores, confidence ratings, test results
- Teaching strategy effectiveness records
- Misconception detection and resolution history
- Session timestamps and duration
- Career target selections and readiness history

---

## 8. Integration Requirements

### 8.1 External APIs

| Integration | Purpose | Hackathon | Production |
|-------------|---------|-----------|------------|
| **Claude API (Anthropic)** | Agent reasoning, test generation, response evaluation | Required | Required |
| **Serper API** | Web search for current topic research | Optional | Required |
| **Web Scraping (HTTP)** | Fetch content from top search results | Optional | Required |
| **O*NET API** | Job role data, skill requirements, market trends | Not needed | Required |
| **GitHub API** | Code-based skill validation, portfolio analysis | Not needed | Future |

### 8.2 Internal Service Communication

- All agents communicate through the Orchestrator (hub-and-spoke pattern)
- Communication is synchronous for MVP (agent function calls)
- Production: event-driven with message queue (Redis Streams or similar)
- Structured event schema for all inter-agent messages

---

## 9. Success Criteria & Metrics

### 9.1 Hackathon Success Criteria

| Criterion | Measurement | Target |
|-----------|-------------|--------|
| **Demo Impact** | Does the "confidence calibration catch" moment land with judges? | Judges visibly react |
| **Technical Depth** | Can we explain agent coordination when asked? | Clear 60-second explanation |
| **Differentiation** | Can we articulate in 30 seconds why this isn't a ChatGPT wrapper? | Distinct from all comparisons |
| **Working Demo** | End-to-end flow works live without crashes | Zero failures during demo |
| **Problem-Solution Fit** | Judges agree the solution addresses the stated problem | Positive judge feedback |

### 9.2 Validation Metrics (Post-Hackathon)

| Metric | Description | Target |
|--------|-------------|--------|
| **Calibration Improvement** | Does the gap between self-assessment and test performance shrink over 10+ sessions? | >30% reduction in calibration gap |
| **Transfer Test Validity** | Do transfer-test-passers outperform recognition-test-passers on real tasks? | Statistically significant difference |
| **Misconception Detection Rate** | % of failed tests with specific misconception identified (vs. generic "wrong") | >60% |
| **User Retention** | Weekly active return rate | >30% (exceptional for ed-tech) |
| **Mastery Durability** | Re-test pass rate after 30 days | >70% |
| **Cross-Domain Transfer** | Does mastering concept A in domain X measurably accelerate concept B in domain Y? | Measurable speed increase |
| **Cost Per Mastery Event** | Total LLM cost / validated mastery events | <$0.50 |

### 9.3 Long-Term Business Metrics

| Metric | Target (12 months) |
|--------|-------------------|
| Registered learners | 10,000+ |
| Domains supported | 10+ |
| Concepts in knowledge graph | 500+ |
| Career roles mapped | 50+ |
| Career readiness correlation | Positive correlation between readiness score and job outcomes |
| Revenue | B2C subscriptions validated OR B2B talent pipeline pilot signed |

---

## 10. Assumptions & Dependencies

### 10.1 Assumptions

1. **LLM Quality:** Claude/GPT-4 class models can reliably generate transfer tests, evaluate free-form responses, and detect misconceptions with acceptable accuracy (>80% agreement with human evaluator).
2. **Transfer Testing Validity:** Transfer tests generated by LLMs are a valid proxy for real-world application ability. This assumption must be validated post-hackathon.
3. **Misconception Patterns:** Common misconceptions are relatively stable and can be pre-catalogued per concept. Novel misconceptions can be LLM-detected.
4. **Career Mapping Accuracy:** The mapping from validated concept mastery to career readiness is meaningful and actionable. Requires validation against actual job outcomes.
5. **User Willingness:** Learners are willing to be challenged and shown their gaps, rather than just given answers. The "ego hit" of low mastery scores is outweighed by the value of honest feedback.

### 10.2 Dependencies

| Dependency | Risk Level | Mitigation |
|------------|:----------:|------------|
| Claude/GPT-4 API availability | Low | Multi-provider fallback; cache test templates |
| LLM structured output reliability | Medium | Validation layer, retry logic, fallback templates |
| Knowledge graph quality | Medium | Start narrow (3 domains), manual curation, expert review |
| Hackathon infrastructure | Low | Use managed services (Railway/Fly.io), test deployment early |
| Serper API availability | Low | Fallback to static research data for MVP |

---

## 11. Glossary

| Term | Definition |
|------|-----------|
| **Transfer Test** | A test that presents a concept in a context the learner has not previously encountered, requiring application of understanding rather than recall |
| **Misconception** | A systematic incorrect mental model about a concept, distinct from simple lack of knowledge |
| **Mastery Score** | A 0.0-1.0 score representing validated understanding, based primarily on transfer test performance |
| **Calibration Gap** | The difference between a learner's self-reported confidence and their actual mastery score |
| **Knowledge Graph** | A directed graph of concepts with prerequisite edges, transfer edges, and career role mappings |
| **Transfer Edge** | A weighted connection between concepts in different domains indicating that mastery of one accelerates learning the other |
| **Agent** | An autonomous component with a specific goal, access to specific data, and decision-making authority within its domain |
| **Orchestrator** | The central coordinating agent that receives events from all agents and decides the next action in the learning loop |
| **Mastery-Gated** | A property or metric that only updates based on transfer-test-validated mastery, not self-reports or course completion |
| **Spaced Repetition** | Evidence-based scheduling of review/re-testing to combat memory decay, adapted here for transfer tests |
| **Career Readiness Score** | A 0.0-1.0 score representing how close a learner's validated skills are to the requirements of a specific career role |
| **Teaching Strategy** | A specific pedagogical approach (Socratic, example-based, debugging exercise, analogy, explain-back) used by the Teacher Agent |

---

*End of Requirements Document*
