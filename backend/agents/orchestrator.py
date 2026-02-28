import json
import logging
import uuid
from datetime import datetime
from backend.agents.base import BaseAgent
from backend.agents.examiner import examiner_agent
from backend.agents.teacher import teacher_agent
from backend.agents.curriculum import curriculum_agent
from backend.agents.career_mapper import career_mapper_agent
from backend.agents.rl_engine import get_rl_engine, REWARD_MASTERY, REWARD_TEST_PASS_MULT, REWARD_TEST_FAIL, REWARD_MISCONCEPTION, REWARD_RESOLVED, REWARD_STEP
from backend.agents.review_scheduler import review_scheduler
from backend.agents.motivation import motivation_agent
from backend.agents.analytics import analytics_agent
from backend.agents.message_bus import message_bus, AgentMessage
from backend.agents.tools import Tool, tool_registry
from backend.models.learner import LearnerState, ConceptMastery, TestResult, RubricScore
from backend.models.events import AgentEvent, Session
from backend.services.knowledge_graph import knowledge_graph
from backend.services.learner_store import learner_store

from backend.config import settings
from backend.events.types import StreamEvent

logger = logging.getLogger(__name__)

MAX_REACT_STEPS = settings.max_react_steps
MAX_REASONING_HISTORY = settings.max_reasoning_history


class OrchestratorAgent(BaseAgent):
    name = "orchestrator"

    def __init__(self):
        self.active_sessions: dict[str, Session] = {}
        self._tools_registered = False

    def _ensure_tools(self):
        if self._tools_registered:
            return
        self._tools_registered = True

        tool_registry.register(Tool(
            name="teach",
            description="Teach a concept to the learner using a specific strategy. Use when starting a new concept or reteaching after failure.",
            parameters={"concept_id": "str - the concept to teach", "strategy": "str (optional) - teaching strategy"},
            handler=self._tool_teach,
        ))
        tool_registry.register(Tool(
            name="generate_test",
            description="Generate a transfer test to assess deep understanding. Use after teaching and practice to validate mastery.",
            parameters={"concept_id": "str", "difficulty": "int 1-3 (default 2)"},
            handler=self._tool_generate_test,
        ))
        tool_registry.register(Tool(
            name="evaluate_response",
            description="Evaluate the learner's answer to a test. Returns score, misconceptions, and rubric breakdown.",
            parameters={"response": "str - the learner's answer text"},
            handler=self._tool_evaluate,
        ))
        tool_registry.register(Tool(
            name="generate_practice",
            description="Generate practice problems in familiar contexts. Use after teaching, before the real transfer test.",
            parameters={"concept_id": "str"},
            handler=self._tool_practice,
        ))
        tool_registry.register(Tool(
            name="select_next_concept",
            description="Ask curriculum agent for the next concept to teach based on learner's progress and career goals.",
            parameters={},
            handler=self._tool_next_concept,
        ))
        tool_registry.register(Tool(
            name="mark_mastered",
            description="Mark a concept as mastered after passing a transfer test (score >= 0.7). Updates learner state and career readiness.",
            parameters={"concept_id": "str", "score": "float"},
            handler=self._tool_mark_mastered,
        ))
        tool_registry.register(Tool(
            name="ask_learner",
            description="Ask the learner a question — self-assessment (confidence 1-10), clarification, or open-ended chat.",
            parameters={"question": "str", "question_type": "str: self_assess|clarify|chat"},
            handler=self._tool_ask_learner,
        ))
        tool_registry.register(Tool(
            name="check_career_impact",
            description="Check how mastering a concept would affect career readiness scores. Informational — does not change state.",
            parameters={"concept_id": "str"},
            handler=self._tool_career_impact,
        ))

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    async def _load_session(self, session_id: str) -> Session | None:
        session = self.active_sessions.get(session_id)
        if session:
            return session
        session = await learner_store.get_session(session_id)
        if session:
            self.active_sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Session | None:
        return self.active_sessions.get(session_id)

    # ------------------------------------------------------------------
    # Public API — same signatures as before
    # ------------------------------------------------------------------

    def _resolve_topic_to_concept(self, topic: str) -> str | None:
        topic_lower = topic.lower().strip()
        if not topic_lower:
            return None
        # 1. Exact ID match
        if knowledge_graph.get_concept(topic_lower):
            return topic_lower
        # 2. Exact name match (case-insensitive)
        for c in knowledge_graph.get_all_concepts():
            if topic_lower == c.name.lower():
                return c.id
        # 3. Substring match
        for c in knowledge_graph.get_all_concepts():
            if topic_lower in c.name.lower() or topic_lower in c.id.lower():
                return c.id
        return None

    async def _generate_topic_concepts(self, topic: str, learner: LearnerState, event_bus=None) -> str | None:
        # generate concepts on the fly for topics not already in the knowledge graph
        from backend.services.concept_generator import concept_generator

        if event_bus:
            await self._emit(event_bus, StreamEvent.agent_thinking("orchestrator", f"Building a learning path for \"{topic}\"..."))

        try:
            concepts = await concept_generator.generate_concept_tree(
                topic=topic,
                depth=10,
                learner_experience=learner.experience_level,
            )
            if not concepts:
                logger.warning(f"No concepts generated for topic '{topic}'")
                return None

            knowledge_graph.add_concepts(concepts)
            logger.info(f"Generated {len(concepts)} concepts for topic '{topic}'")

            if event_bus:
                await self._emit(event_bus, StreamEvent.tool_complete(
                    "generate_concepts", f"Created {len(concepts)} concepts for {topic}", "orchestrator"
                ))

            # Return the first (most foundational) concept
            return concepts[0].id
        except Exception as e:
            logger.error(f"Failed to generate concepts for topic '{topic}': {e}")
            return None

    async def start_session(self, learner: LearnerState, event_bus=None, topic: str | None = None) -> dict:
        self._ensure_tools()
        session = Session(learner_id=learner.learner_id)
        self.active_sessions[session.session_id] = session

        # If user specified a topic, resolve or generate concepts for it
        if topic:
            concept_id = self._resolve_topic_to_concept(topic)
            if not concept_id:
                # Topic not in graph — dynamically generate a concept tree
                concept_id = await self._generate_topic_concepts(topic, learner, event_bus)
            if concept_id:
                session.current_concept = concept_id
                logger.info(f"User requested topic '{topic}' resolved to concept '{concept_id}'")

        # let agents post recommendations to the bus
        curriculum_agent.post_recommendations(learner, session.session_id)
        review_scheduler.post_review_recommendations(learner, session.session_id)
        analytics_agent.post_analytics_observation(learner, session.session_id)

        result = await self._react_loop(session, learner, "session_start", "", event_bus=event_bus)
        result["session_id"] = session.session_id
        return result

    async def handle_response(self, session_id: str, learner: LearnerState,
                              response_type: str, content: str,
                              confidence: float | None = None,
                              event_bus=None) -> dict:
        self._ensure_tools()
        session = await self._load_session(session_id)
        if not session:
            return {"error": "Session not found"}

        logger.info(f"handling {response_type} in state={session.current_state} concept={session.current_concept}")

        # store self-assessment before entering the loop
        if response_type == "self_assessment":
            conf = (confidence or 5) / 10.0
            session.self_assessment = conf
            cid = session.current_concept
            if cid:
                if cid not in learner.concept_states:
                    learner.concept_states[cid] = ConceptMastery(concept_id=cid)
                learner.concept_states[cid].self_reported_confidence = conf
                await learner_store.update_learner(learner)

        trigger_map = {
            "answer": f"learner_answer (current_state={session.current_state})",
            "self_assessment": "self_assessment_received",
            "chat": "chat_message",
        }
        trigger = trigger_map.get(response_type, f"learner_input ({response_type})")

        return await self._react_loop(session, learner, trigger, content, event_bus=event_bus)

    # ------------------------------------------------------------------
    # ReAct loop — the core of the agentic orchestrator
    # ------------------------------------------------------------------

    async def _react_loop(self, session: Session, learner: LearnerState,
                          trigger: str, user_content: str, event_bus=None) -> dict:
        context = self._build_context(session, learner, trigger, user_content)
        final_result = None
        llm_calls = 0

        # Store event_bus on session so tool handlers can access it
        session._event_bus = event_bus

        for step in range(MAX_REACT_STEPS):
            await self._emit(event_bus, StreamEvent.agent_thinking("orchestrator", "Deciding next action..."))
            decision = await self._reason(context, step, session)
            llm_calls += 1
            await self._emit(event_bus, StreamEvent.thinking_complete())

            reasoning_text = decision.get("reasoning", "no reasoning provided")
            session.reasoning_history.append(f"[step {step + 1}] {reasoning_text}")
            if len(session.reasoning_history) > MAX_REASONING_HISTORY:
                session.reasoning_history = session.reasoning_history[-MAX_REASONING_HISTORY:]

            tool_name = decision.get("tool", "")
            tool_args = decision.get("args", {})
            respond = decision.get("respond_to_learner", True)

            tool = tool_registry.get(tool_name)
            if not tool or not tool.handler:
                logger.warning(f"invalid tool '{tool_name}', falling back to state-based default")
                final_result = await self._fallback(session, learner, trigger, user_content)
                break

            logger.info(f"[react step {step + 1}] tool={tool_name} args={tool_args} respond={respond}")

            # Emit tool start
            agent_label = self._tool_agent_label(tool_name)
            await self._emit(event_bus, StreamEvent.tool_start(tool_name, agent=agent_label))

            result = await tool.handler(session=session, learner=learner, **tool_args)
            llm_calls += result.pop("_llm_calls", 0)

            # Emit tool complete
            await self._emit(event_bus, StreamEvent.tool_complete(tool_name, agent=agent_label))

            session.current_state = self._infer_state(tool_name)

            # Emit phase change
            action = result.get("action", "")
            if action:
                concept_name = ""
                if session.current_concept:
                    c = knowledge_graph.get_concept(session.current_concept)
                    concept_name = c.name if c else session.current_concept
                await self._emit(event_bus, StreamEvent.phase_change(action, concept=concept_name))

            if respond or step == MAX_REACT_STEPS - 1 or llm_calls >= settings.max_llm_calls_per_loop:
                final_result = result
                break

            # add observation for next reasoning step
            observation = json.dumps(result, default=str)[:500]
            context += f"\n\nOBSERVATION from {tool_name}: {observation}"

        if final_result is None:
            final_result = await self._fallback(session, learner, trigger, user_content)

        # persist agent messages for the session
        session.agent_messages = message_bus.serialize(session.session_id)
        await learner_store.save_session(session)

        formatted = self._format_response(session, learner, final_result)

        # Stream the text content as chunks if event_bus is active
        if event_bus is not None:
            text = self._extract_text(formatted)
            if text:
                # Stream in chunks for a typing effect
                chunk_size = 40
                for i in range(0, len(text), chunk_size):
                    chunk = text[i:i + chunk_size]
                    is_final = (i + chunk_size) >= len(text)
                    await self._emit(event_bus, StreamEvent.text_chunk(chunk, final=is_final))

            await self._emit(event_bus, StreamEvent.result(formatted))
            await self._emit(event_bus, StreamEvent.stream_complete())

        return formatted

    def _tool_agent_label(self, tool_name: str) -> str:
        return {
            "teach": "teacher",
            "generate_test": "examiner",
            "evaluate_response": "examiner",
            "generate_practice": "examiner",
            "ask_learner": "orchestrator",
            "select_next_concept": "curriculum",
            "mark_mastered": "orchestrator",
            "check_career_impact": "career_mapper",
        }.get(tool_name, "orchestrator")

    def _extract_text(self, response: dict) -> str:
        content = response.get("content", {})
        if isinstance(content, str):
            return content
        if isinstance(content, dict):
            return (
                content.get("explanation")
                or content.get("teaching_content")
                or content.get("message")
                or content.get("problem_statement")
                or content.get("question")
                or ""
            )
        return ""

    # ------------------------------------------------------------------
    # Reasoning — the LLM decides what to do
    # ------------------------------------------------------------------

    async def _reason(self, context: str, step: int, session: Session) -> dict:
        remaining = MAX_REACT_STEPS - step
        tool_descs = tool_registry.get_tool_descriptions()

        # gather available concept IDs for the LLM (all domains)
        available_concepts = [c.id for c in knowledge_graph.get_all_concepts()]

        # get RL suggestion for the current context
        rl_hint = ""
        if "current concept" in context.lower() or "session_start" in context.lower():
            try:
                from backend.agents.rl_engine import get_rl_engine
                # extract learner from context isn't possible here, so hint is best-effort
                rl_hint = f"\nRL POLICY HINT: The RL engine recommends exploring actions based on learned Q-values. Trust the adaptive thresholds."
            except Exception:
                pass

        system = f"""You are the orchestrator of MasteryAI, an intelligent learning system with multiple specialist agents.
Your job is to reason about what the learner needs and choose the right action.

AVAILABLE TOOLS:
{tool_descs}

VALID CONCEPT IDs (use these exact IDs):
{available_concepts[:20]}
{rl_hint}

RULES:
- Pick exactly ONE tool per step. Always set respond_to_learner to true.
- For session_start: if agent recommendations mention decayed concepts, use generate_test with that concept_id. Otherwise use teach with the recommended concept_id.
- After teaching content is delivered and learner answers (state=teaching/reteaching), use generate_practice.
- After practice (state=practicing), use ask_learner with question_type "self_assess".
- After self-assessment, use generate_test.
- After evaluate_response: the tool handles mastery/retest/reteach decisions automatically based on adaptive RL thresholds.
- For chat messages, use ask_learner with question_type "chat".
- You have {remaining} step(s) remaining.

Return JSON only: {{"tool": "tool_name", "args": {{}}, "reasoning": "your step-by-step thinking", "respond_to_learner": true}}"""

        result = await self._llm_call(system, context)
        # validate
        if "tool" not in result:
            result["tool"] = self._infer_tool_from_context(context, session)
            result["args"] = {}
            result["respond_to_learner"] = True
        return result

    def _infer_tool_from_context(self, context: str, session: Session) -> str:
        state = session.current_state
        if state in ("teaching", "reteaching"):
            return "generate_practice"
        if state == "practicing":
            return "ask_learner"
        if state in ("testing", "retesting"):
            return "evaluate_response"
        if state == "self_assessing":
            return "generate_test"
        return "teach"

    # ------------------------------------------------------------------
    # Context builder
    # ------------------------------------------------------------------

    def _build_context(self, session: Session, learner: LearnerState,
                       trigger: str, user_content: str) -> str:
        concept = knowledge_graph.get_concept(session.current_concept) if session.current_concept else None

        mastered = [cid for cid, cs in learner.concept_states.items() if cs.status == "mastered"]
        active_misconceptions = []
        strategies_tried = {}
        if session.current_concept and session.current_concept in learner.concept_states:
            cs = learner.concept_states[session.current_concept]
            active_misconceptions = cs.misconceptions_active
            strategies_tried = cs.teaching_strategies_tried

        bus_messages = message_bus.get_messages(session.session_id, limit=5)
        agent_advice = "\n".join(
            f"- [{m.source_agent}] ({m.message_type}) {m.content}" for m in bus_messages
        ) if bus_messages else "None"

        past_reasoning = "\n".join(session.reasoning_history[-5:]) if session.reasoning_history else "None"

        last_test_summary = "None"
        if session.last_test:
            lt = session.last_test
            last_test_summary = f"context={lt.get('context_description', '?')}, concept={lt.get('concept_id', '?')}"

        return f"""TRIGGER: {trigger}
LEARNER INPUT: {user_content or '(none)'}

SESSION STATE:
- Current concept: {concept.name + ' (' + session.current_concept + ')' if concept else session.current_concept or 'None'}
- UI state: {session.current_state}
- Strategy: {session.current_strategy or 'None'}
- Tests passed/failed: {session.tests_passed}/{session.tests_failed}
- Concepts mastered this session: {session.concepts_mastered}
- Self-assessment: {session.self_assessment}

LEARNER PROFILE:
- Experience: {learner.experience_level}
- Mastered: {mastered[:10]}
- Calibration trend: {learner.learning_profile.calibration_trend}
- Active misconceptions: {active_misconceptions}
- Strategies tried for current concept: {strategies_tried}

LAST TEST: {last_test_summary}
LAST EVALUATION: {json.dumps(session.last_evaluation, default=str)[:200] if session.last_evaluation else 'None'}

AGENT RECOMMENDATIONS:
{agent_advice}

YOUR PAST REASONING:
{past_reasoning}"""

    # ------------------------------------------------------------------
    # State inference for frontend
    # ------------------------------------------------------------------

    def _infer_state(self, tool_name: str) -> str:
        return {
            "teach": "teaching",
            "generate_test": "testing",
            "evaluate_response": "evaluating",
            "generate_practice": "practicing",
            "ask_learner": "self_assessing",
            "select_next_concept": "idle",
            "mark_mastered": "idle",
            "check_career_impact": "idle",
        }.get(tool_name, "idle")

    # ------------------------------------------------------------------
    # Response formatter — preserves existing API contract
    # ------------------------------------------------------------------

    def _format_response(self, session: Session, learner: LearnerState, result: dict) -> dict:
        action = result.get("action", "continue")
        response = {
            "action": action,
            "concept": self._concept_info(session.current_concept) if session.current_concept else None,
            "content": result.get("content", {}),
            "agent_reasoning": session.reasoning_history[-1] if session.reasoning_history else "",
            "events": [e.model_dump() for e in session.events[-5:]],
        }
        for key in ("evaluation", "calibration", "career_readiness", "next_concept",
                     "next_content", "misconceptions_detected", "state_update"):
            if key in result:
                response[key] = result[key]
        return response

    # ------------------------------------------------------------------
    # Fallback — deterministic behavior when LLM can't decide
    # ------------------------------------------------------------------

    async def _fallback(self, session: Session, learner: LearnerState,
                        trigger: str, user_content: str) -> dict:
        logger.warning("using deterministic fallback")
        cid = session.current_concept
        concept = knowledge_graph.get_concept(cid) if cid else None

        if "session_start" in trigger:
            decayed = curriculum_agent.get_decayed_concepts(learner)
            if decayed:
                return await self._tool_generate_test(session=session, learner=learner,
                                                     concept_id=decayed[0], difficulty=1)
            next_cid = curriculum_agent.select_next_concept(learner)
            if next_cid:
                return await self._tool_teach(session=session, learner=learner, concept_id=next_cid)
            return {"action": "complete", "content": {"message": "All concepts mastered!"}}

        if "self_assessment" in trigger and cid:
            return await self._tool_generate_test(session=session, learner=learner, concept_id=cid)

        if "learner_answer" in trigger:
            state = session.current_state
            if state in ("testing", "retesting") and cid:
                return await self._tool_evaluate(session=session, learner=learner, response=user_content)
            if state in ("teaching", "reteaching") and cid:
                return await self._tool_practice(session=session, learner=learner, concept_id=cid)
            if state == "practicing" and concept:
                return await self._tool_ask_learner(
                    session=session, learner=learner,
                    question=f"Rate your confidence on {concept.name} from 1-10.",
                    question_type="self_assess"
                )

        return {"action": "continue", "content": {"message": "Let's keep going."}}

    # ------------------------------------------------------------------
    # Tool handlers
    # ------------------------------------------------------------------

    async def _tool_teach(self, *, session: Session, learner: LearnerState,
                          concept_id: str = "", strategy: str = "", **_kw) -> dict:
        if not concept_id:
            concept_id = session.current_concept or ""
        concept_id = self._resolve_concept_id(concept_id)
        concept = knowledge_graph.get_concept(concept_id)
        if not concept:
            return {"action": "error", "content": {"message": f"Concept {concept_id} not found"}}

        teaching = await teacher_agent.teach(concept, learner, strategy=strategy or None)

        session.current_concept = concept_id
        session.last_teaching_content = teaching
        session.current_strategy = teaching.get("strategy_used", "socratic")
        if concept_id not in session.concepts_covered:
            session.concepts_covered.append(concept_id)

        if concept_id not in learner.concept_states:
            learner.concept_states[concept_id] = ConceptMastery(
                concept_id=concept_id, status="introduced", introduced_at=datetime.utcnow()
            )
        else:
            learner.concept_states[concept_id].status = "introduced"
        await learner_store.update_learner(learner)

        event = self._event(
            "TEACHING_STARTED", learner.learner_id, session.session_id,
            {"concept": concept_id, "strategy": session.current_strategy},
            f"Teaching {concept.name} using {session.current_strategy}."
        )
        session.events.append(event)

        career_readiness = career_mapper_agent.calculate_all_readiness(learner)

        return {
            "action": "teach",
            "content": teaching,
            "career_readiness": [r.model_dump() for r in career_readiness],
            "_llm_calls": 1,
        }

    async def _tool_generate_test(self, *, session: Session, learner: LearnerState,
                                  concept_id: str = "", difficulty: int = 2, **_kw) -> dict:
        if not concept_id:
            concept_id = session.current_concept or ""
        concept_id = self._resolve_concept_id(concept_id)
        concept = knowledge_graph.get_concept(concept_id)
        if not concept:
            return {"action": "error", "content": {"message": f"Concept {concept_id} not found"}}

        test = await examiner_agent.generate_transfer_test(concept, learner, difficulty_tier=difficulty)
        session.current_concept = concept_id
        session.last_test = test

        event = self._event(
            "TRANSFER_TEST_GENERATED", learner.learner_id, session.session_id,
            {"concept": concept_id, "context": test.get("context_description", "")},
            f"Transfer test generated for {concept.name}."
        )
        session.events.append(event)

        action = "decay_check" if "session_start" in (session.reasoning_history[-1] if session.reasoning_history else "") else "transfer_test"

        return {"action": action, "content": test, "_llm_calls": 1}

    async def _tool_evaluate(self, *, session: Session, learner: LearnerState,
                             response: str = "", **_kw) -> dict:
        concept_id = session.current_concept
        concept = knowledge_graph.get_concept(concept_id) if concept_id else None
        if not concept:
            return {"action": "error", "content": {"message": "No active concept to evaluate"}}

        evaluation = await examiner_agent.evaluate_response(concept, session.last_test or {}, response)
        score = evaluation.get("total_score", 0.0)
        misconceptions = evaluation.get("misconceptions_detected", [])
        misconception_ids = [m.get("misconception_id", "") for m in misconceptions if isinstance(m, dict)]

        cs = learner.concept_states.get(concept_id)
        if not cs:
            cs = ConceptMastery(concept_id=concept_id)
            learner.concept_states[concept_id] = cs

        test_result = TestResult(
            test_id=str(uuid.uuid4()),
            context=session.last_test.get("context_description", "") if session.last_test else "",
            score=score,
            misconceptions_detected=misconception_ids,
            rubric_scores=[
                RubricScore(criterion=r.get("criterion", ""), score=r.get("score", 0), evidence=r.get("evidence", ""))
                for r in evaluation.get("rubric_scores", [])
            ],
            learner_response_summary=response[:200],
            evaluator_reasoning=evaluation.get("reasoning", ""),
            confidence_at_time=session.self_assessment or 0.0,
        )
        cs.transfer_tests.append(test_result)
        cs.mastery_score = score
        session.total_transfer_tests += 1
        session.last_evaluation = evaluation

        conf_normalized = session.self_assessment or 0.0
        cs.calibration_gap = round(conf_normalized - score, 3)

        if session.last_test:
            ctx = session.last_test.get("context_description", "")
            if ctx and ctx not in cs.contexts_encountered:
                cs.contexts_encountered.append(ctx)

        calibration = {
            "self_assessment": round(conf_normalized, 2),
            "actual_score": round(score, 2),
            "gap": round(conf_normalized - score, 3),
        }

        # post evaluation to bus so orchestrator's next reasoning step sees it
        message_bus.post(AgentMessage(
            source_agent="examiner",
            target_agent="orchestrator",
            message_type="observation",
            content=f"Evaluation: score={score:.2f}, misconceptions={misconception_ids}, level={evaluation.get('understanding_level', '?')}",
            metadata={"score": score, "misconceptions": misconception_ids},
            session_id=session.session_id,
        ))

        # RL-learned thresholds (replaces hardcoded 0.7 / 0.4)
        engine = get_rl_engine(learner)
        mastery_threshold = engine.select_mastery_threshold(learner, concept_id)
        retest_multiplier = engine.select_retest_multiplier(learner, concept_id)
        retest_threshold = mastery_threshold * retest_multiplier

        if score >= mastery_threshold:
            result = await self._handle_mastery(session, learner, cs, concept_id, score,
                                                misconception_ids, evaluation, calibration)
            # schedule first spaced repetition review
            review_scheduler.schedule_review(learner, concept_id, score)
            # RL reward: mastery achieved
            reward = REWARD_MASTERY + REWARD_TEST_PASS_MULT * score
            for mid in misconception_ids:
                if mid in cs.misconceptions_resolved:
                    reward += REWARD_RESOLVED
        elif score >= retest_threshold:
            result = await self._handle_retest(session, learner, cs, concept_id, score,
                                               evaluation, calibration)
            reward = REWARD_TEST_PASS_MULT * score + REWARD_STEP
        else:
            result = await self._handle_reteach(session, learner, cs, concept_id, score,
                                                misconception_ids, evaluation, calibration)
            reward = REWARD_TEST_FAIL + REWARD_MISCONCEPTION * len(misconception_ids)

        # update RL engine
        strategy = session.current_strategy or "socratic"
        engine.update_strategy(strategy, score)
        difficulty = session.last_test.get("difficulty_tier", 2) if session.last_test else 2
        engine.update_difficulty(learner, concept_id, difficulty, mastery_threshold, reward)

        prev_state = engine.get_action_state_key(learner, session, concept_id)
        engine.update_action(prev_state, "test", reward, prev_state)

        learner.rl_policy = engine.to_dict()
        await learner_store.update_learner(learner)

        # track engagement
        motivation_agent.record_interaction(
            session.session_id, evaluation.get("reasoning", ""),
            score=score, is_test_result=True
        )
        motivation_agent.post_observation(session.session_id, learner)
        session.engagement_state = motivation_agent.detect_state(session.session_id)

        return result

    async def _handle_mastery(self, session, learner, cs, concept_id, score,
                              misconception_ids, evaluation, calibration):
        cs.status = "mastered"
        cs.mastered_at = datetime.utcnow()
        cs.last_validated = datetime.utcnow()
        for mid in misconception_ids:
            if mid in cs.misconceptions_active:
                cs.misconceptions_active.remove(mid)
                cs.misconceptions_resolved.append(mid)
        session.tests_passed += 1
        session.concepts_mastered.append(concept_id)
        learner.learning_profile.total_concepts_mastered += 1
        await learner_store.update_learner(learner)

        # celebrate milestones
        if learner.learning_profile.total_concepts_mastered == 1:
            motivation_agent.celebrate_milestone(learner, "first_mastery", session.session_id)
        else:
            motivation_agent.celebrate_milestone(learner, "concept_mastered", session.session_id)

        career_readiness = career_mapper_agent.calculate_all_readiness(learner)

        event = self._event(
            "CONCEPT_MASTERED", learner.learner_id, session.session_id,
            {"concept": concept_id, "score": score, "calibration": calibration},
            f"Mastered! Score {score:.2f}. Gap {calibration['gap']:.2f}."
        )
        session.events.append(event)

        next_cid = curriculum_agent.select_next_concept(learner)
        if next_cid:
            next_c = knowledge_graph.get_concept(next_cid)
            teaching = await teacher_agent.teach(next_c, learner)
            session.current_concept = next_cid
            session.current_state = "teaching"
            session.last_teaching_content = teaching
            session.current_strategy = teaching.get("strategy_used", "socratic")
            if next_cid not in session.concepts_covered:
                session.concepts_covered.append(next_cid)
            if next_cid not in learner.concept_states:
                learner.concept_states[next_cid] = ConceptMastery(
                    concept_id=next_cid, status="introduced", introduced_at=datetime.utcnow()
                )
            await learner_store.update_learner(learner)

            return {
                "action": "mastered_and_advance",
                "evaluation": evaluation,
                "calibration": calibration,
                "concept": self._concept_info(concept_id),
                "next_concept": self._concept_info(next_cid),
                "next_content": teaching,
                "content": teaching,
                "state_update": {"concept_status": "mastered"},
                "career_readiness": [r.model_dump() for r in career_readiness],
                "_llm_calls": 2,  # evaluate + teach
            }

        return {
            "action": "mastered_all_done",
            "evaluation": evaluation,
            "calibration": calibration,
            "concept": self._concept_info(concept_id),
            "content": {"message": "All concepts mastered!"},
            "state_update": {"concept_status": "mastered"},
            "career_readiness": [r.model_dump() for r in career_readiness],
            "_llm_calls": 1,
        }

    async def _handle_retest(self, session, learner, cs, concept_id, score,
                             evaluation, calibration):
        cs.status = "testing"
        session.current_state = "retesting"
        await learner_store.update_learner(learner)

        concept = knowledge_graph.get_concept(concept_id)
        engine = get_rl_engine(learner)
        retest_difficulty = engine.select_difficulty(learner, concept_id)
        new_test = await examiner_agent.generate_transfer_test(concept, learner, difficulty_tier=retest_difficulty)
        session.last_test = new_test

        event = self._event(
            "ASSESSMENT_COMPLETE", learner.learner_id, session.session_id,
            {"concept": concept_id, "score": score, "decision": "retest"},
            f"Partial ({score:.2f}). Retesting in different context."
        )
        session.events.append(event)

        return {
            "action": "retest",
            "evaluation": evaluation,
            "calibration": calibration,
            "concept": self._concept_info(concept_id),
            "content": new_test,
            "state_update": {"concept_status": "testing"},
            "_llm_calls": 2,
        }

    async def _handle_reteach(self, session, learner, cs, concept_id, score,
                              misconception_ids, evaluation, calibration):
        cs.status = "introduced"
        for mid in misconception_ids:
            if mid not in cs.misconceptions_active:
                cs.misconceptions_active.append(mid)
        session.tests_failed += 1
        session.misconceptions_detected.extend(misconception_ids)

        prev_strategy = session.current_strategy or "socratic"
        if prev_strategy not in cs.teaching_strategies_tried:
            cs.teaching_strategies_tried[prev_strategy] = score
        else:
            cs.teaching_strategies_tried[prev_strategy] = min(cs.teaching_strategies_tried[prev_strategy], score)

        # LLM-driven strategy selection via teacher reflection
        new_strategy = await teacher_agent.select_strategy_smart(
            learner, concept_id, misconception_ids, session.session_id
        )
        session.current_strategy = new_strategy
        session.current_state = "reteaching"
        await learner_store.update_learner(learner)

        concept = knowledge_graph.get_concept(concept_id)
        reteach = await teacher_agent.teach(concept, learner, strategy=new_strategy, misconceptions=misconception_ids)
        session.last_teaching_content = reteach

        event = self._event(
            "ASSESSMENT_COMPLETE", learner.learner_id, session.session_id,
            {"concept": concept_id, "score": score, "calibration": calibration,
             "misconceptions": misconception_ids, "decision": "reteach",
             "previous_strategy": prev_strategy, "new_strategy": new_strategy},
            f"Failed ({score:.2f}). Misconceptions: {misconception_ids}. Switching {prev_strategy} -> {new_strategy}."
        )
        session.events.append(event)

        return {
            "action": "reteach",
            "evaluation": evaluation,
            "calibration": calibration,
            "concept": self._concept_info(concept_id),
            "content": reteach,
            "misconceptions_detected": misconception_ids,
            "state_update": {"concept_status": "reteaching",
                             "strategy_switch": {"from": prev_strategy, "to": new_strategy}},
            "_llm_calls": 2,  # evaluate + reteach (+ possible reflection)
        }

    async def _tool_practice(self, *, session: Session, learner: LearnerState,
                             concept_id: str = "", **_kw) -> dict:
        if not concept_id:
            concept_id = session.current_concept or ""
        concept_id = self._resolve_concept_id(concept_id)
        concept = knowledge_graph.get_concept(concept_id)
        if not concept:
            return {"action": "error", "content": {"message": f"Concept {concept_id} not found"}}

        if concept_id not in learner.concept_states:
            learner.concept_states[concept_id] = ConceptMastery(concept_id=concept_id)
        learner.concept_states[concept_id].status = "practicing"
        await learner_store.update_learner(learner)

        practice = await examiner_agent.generate_practice(concept, learner)

        event = self._event(
            "PRACTICE_STARTED", learner.learner_id, session.session_id,
            {"concept": concept_id},
            f"Practice problems for {concept.name}."
        )
        session.events.append(event)

        return {
            "action": "practice",
            "content": {"problems": practice, "message": "Let's practice what we just covered."},
            "_llm_calls": 1,
        }

    async def _tool_next_concept(self, *, session: Session, learner: LearnerState, **_kw) -> dict:
        concept_id = curriculum_agent.select_next_concept(learner)
        if not concept_id:
            return {"action": "complete", "content": {"message": "All concepts mastered!"}, "_llm_calls": 0}

        # automatically teach the next concept instead of requiring another reasoning step
        return await self._tool_teach(session=session, learner=learner, concept_id=concept_id)

    async def _tool_mark_mastered(self, *, session: Session, learner: LearnerState,
                                  concept_id: str = "", score: float = 0.8, **_kw) -> dict:
        if not concept_id:
            concept_id = session.current_concept or ""
        cs = learner.concept_states.get(concept_id)
        if cs:
            cs.status = "mastered"
            cs.mastered_at = datetime.utcnow()
            cs.last_validated = datetime.utcnow()
            cs.mastery_score = score
        session.concepts_mastered.append(concept_id)
        learner.learning_profile.total_concepts_mastered += 1
        await learner_store.update_learner(learner)

        career_readiness = career_mapper_agent.calculate_all_readiness(learner)
        return {
            "action": "mastered",
            "content": {"concept_id": concept_id, "score": score},
            "career_readiness": [r.model_dump() for r in career_readiness],
            "_llm_calls": 0,
        }

    async def _tool_ask_learner(self, *, session: Session, learner: LearnerState,
                                question: str = "", question_type: str = "self_assess", **_kw) -> dict:
        concept = knowledge_graph.get_concept(session.current_concept) if session.current_concept else None
        if not question and question_type == "self_assess":
            name = concept.name if concept else "this concept"
            question = f"Before we test your understanding of {name} in a new context, rate your confidence from 1-10."

        event = self._event(
            "QUESTION_ASKED", learner.learner_id, session.session_id,
            {"question_type": question_type},
            f"Asking learner: {question[:60]}"
        )
        session.events.append(event)

        return {
            "action": "self_assess" if question_type == "self_assess" else "chat_response",
            "content": {"message": question},
            "_llm_calls": 0,
        }

    async def _tool_career_impact(self, *, session: Session, learner: LearnerState,
                                  concept_id: str = "", **_kw) -> dict:
        if not concept_id:
            concept_id = session.current_concept or ""
        impacts = career_mapper_agent.get_career_impact(learner, concept_id)

        message_bus.post(AgentMessage(
            source_agent="career_mapper",
            target_agent="orchestrator",
            message_type="observation",
            content=f"Career impact of {concept_id}: {json.dumps(impacts, default=str)[:200]}",
            metadata=impacts,
            session_id=session.session_id,
        ))

        return {
            "action": "career_info",
            "content": impacts,
            "_llm_calls": 0,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_concept_id(self, raw_id: str) -> str:
        if not raw_id:
            return ""
        concept = knowledge_graph.get_concept(raw_id)
        if concept:
            return raw_id
        # try with domain prefix (check all domains)
        for c in knowledge_graph.get_all_concepts():
            if c.id.endswith(f".{raw_id}"):
                return c.id
        # try fuzzy match across all concepts
        for c in knowledge_graph.get_all_concepts():
            if raw_id.lower() in c.id.lower() or raw_id.lower() in c.name.lower():
                return c.id
        return raw_id

    def _concept_info(self, concept_id: str) -> dict:
        concept = knowledge_graph.get_concept(concept_id)
        if not concept:
            return {"id": concept_id}
        return {
            "id": concept.id,
            "name": concept.name,
            "domain": concept.domain,
            "difficulty": concept.difficulty_tier,
            "description": concept.description,
        }


orchestrator = OrchestratorAgent()
