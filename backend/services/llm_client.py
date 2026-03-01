import json
import hashlib
import random
import asyncio
import time
import logging
from collections import OrderedDict
from datetime import datetime
from backend.config import settings

logger = logging.getLogger(__name__)

RETRY_DELAYS = settings.retry_delays
CALL_TIMEOUT = settings.call_timeout
CACHE_MAX = settings.cache_max


class LRUCache:

    def __init__(self, maxsize: int = CACHE_MAX):
        self._data: OrderedDict[str, str] = OrderedDict()
        self._maxsize = maxsize

    def get(self, key: str) -> str | None:
        if key in self._data:
            self._data.move_to_end(key)
            return self._data[key]
        return None

    def put(self, key: str, value: str):
        if key in self._data:
            self._data.move_to_end(key)
        else:
            if len(self._data) >= self._maxsize:
                self._data.popitem(last=False)
        self._data[key] = value

    def __len__(self):
        return len(self._data)


class LLMClient:

    def __init__(self):
        self.use_mock = settings.use_mock_llm
        self.model = settings.llm_model
        self.call_count = 0
        self.total_tokens = 0
        self._cache = LRUCache(CACHE_MAX)
        self._client = None

    def _get_client(self):
        if self._client is None:
            from groq import AsyncGroq
            self._client = AsyncGroq(api_key=settings.groq_api_key)
        return self._client

    async def _redis_get(self, key: str) -> str | None:
        try:
            from backend.services.cache import cache
            if cache._redis:
                return await cache.get(f"llm:{key}")
        except Exception:
            pass
        return None

    async def _redis_set(self, key: str, value: str):
        try:
            from backend.services.cache import cache
            if cache._redis:
                await cache.set(f"llm:{key}", value, ttl=3600)
        except Exception:
            pass

    async def generate(self, prompt: str, system: str = "", response_format: str = "json") -> dict:
        self.call_count += 1
        cache_key = hashlib.md5((system + prompt).encode()).hexdigest()

        redis_val = await self._redis_get(cache_key)
        if redis_val is not None:
            logger.debug("redis cache hit for key=%s", cache_key[:8])
            return json.loads(redis_val)

        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.debug("memory cache hit for key=%s", cache_key[:8])
            return json.loads(cached)

        start = time.monotonic()

        if self.use_mock:
            result = self._mock_generate(system, prompt)
        else:
            result = await self._real_generate(system, prompt)

        elapsed = time.monotonic() - start
        logger.info("llm call #%d took %.2fs", self.call_count, elapsed)

        result_json = json.dumps(result)
        self._cache.put(cache_key, result_json)
        await self._redis_set(cache_key, result_json)
        return result

    async def _real_generate(self, system: str, prompt: str) -> dict:
        client = self._get_client()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        last_err = None
        for attempt, delay in enumerate(RETRY_DELAYS):
            try:
                completion = await asyncio.wait_for(
                    client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=settings.llm_temperature,
                        max_tokens=settings.llm_max_tokens,
                        response_format={"type": "json_object"},
                    ),
                    timeout=CALL_TIMEOUT,
                )
                break
            except (asyncio.TimeoutError, Exception) as e:
                last_err = e
                logger.warning(
                    "attempt %d/%d failed: %s — retrying in %ds",
                    attempt + 1, len(RETRY_DELAYS), str(e), delay,
                )
                if attempt < len(RETRY_DELAYS) - 1:
                    await asyncio.sleep(delay)
        else:
            logger.error("all %d attempts failed", len(RETRY_DELAYS))
            raise last_err

        usage = completion.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        self.total_tokens += prompt_tokens + completion_tokens
        logger.info(
            "tokens used: prompt=%d completion=%d total=%d",
            prompt_tokens, completion_tokens, prompt_tokens + completion_tokens,
        )

        text = completion.choices[0].message.content
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
            return {"raw": text}

    def _mock_generate(self, system: str, prompt: str) -> dict:
        lower = (system + prompt).lower()

        # ReAct orchestrator reasoning
        if "orchestrator" in lower and "available tools" in lower:
            return self._mock_react_decision(system, prompt)
        # teacher reflection
        if "reflective teaching" in lower or "reflect on this outcome" in lower:
            return self._mock_teacher_reflection(prompt)
        # test quality validation
        if "test quality reviewer" in lower:
            return self._mock_test_validation(prompt)
        # concept generation
        if "curriculum designer" in lower and "learning tree" in lower:
            return self._mock_concept_tree(prompt)
        if "curriculum designer" in lower and "expanding" in lower:
            return self._mock_concept_expand(prompt)
        # diagnostic
        if "diagnostic assessment specialist" in lower:
            return self._mock_diagnostic_question(prompt)
        if "diagnostic assessment answer" in lower or "evaluating a diagnostic" in lower:
            return self._mock_diagnostic_evaluation(prompt)
        # career role generation
        if "workforce analyst" in lower:
            return self._mock_career_role(prompt)
        # encouragement
        if "encouraging learning coach" in lower:
            return self._mock_encouragement(prompt)
        # existing handlers
        if "transfer test" in lower and "generate" in lower:
            return self._mock_transfer_test(prompt)
        elif "evaluat" in lower and "rubric" in lower:
            return self._mock_evaluation(prompt)
        elif "teach" in lower:
            return self._mock_teaching(prompt)
        else:
            return self._mock_generic(prompt)

    def _mock_transfer_test(self, prompt: str) -> dict:
        concept = self._extract_concept(prompt)
        contexts = [
            ("rate limiter implementation", "A web service needs to limit API calls per user. Implement a rate limiter factory."),
            ("event handler factory", "A UI framework creates click handlers in a loop for buttons."),
            ("plugin configuration system", "A plugin system uses factory functions to create configured plugins."),
            ("caching decorator factory", "Build a caching system where each cache has different TTL settings."),
            ("database connection pool", "A connection pool needs to track active connections per tenant."),
        ]
        ctx = random.choice(contexts)

        return {
            "problem_statement": f"**Context: {ctx[0].title()}**\n\n{ctx[1]}\n\nUsing your understanding of {concept}, identify the issue in the following code and explain your fix.\n\n```python\ndef create_handlers():\n    handlers = []\n    for i in range(5):\n        handlers.append(lambda: process(i))\n    return handlers\n```\n\nWhat will happen when each handler is called? Fix the bug.",
            "context_description": ctx[0],
            "response_format": "code",
            "correct_approach": f"The learner should recognize that the lambda captures the variable 'i' by reference, not by value. All handlers will use the final value of i. Fix by using a default argument: lambda i=i: process(i)",
            "misconception_traps": [
                {
                    "misconception_id": f"{concept.split('.')[-1]}_late_binding" if "closure" in concept else "surface_pattern",
                    "wrong_answer_pattern": "Tries to fix by adding a global variable or copying i outside the loop without understanding closure capture",
                    "why_wrong": "Does not address the fundamental issue of late binding in closures",
                    "indicator_phrases": ["global", "copy the variable", "store i somewhere"]
                }
            ],
            "rubric": [
                {
                    "criterion": "Correctly identifies the core issue",
                    "max_points": 10,
                    "scoring_guide": {
                        "10": "Clearly explains late binding / variable capture by reference",
                        "7": "Identifies the bug but explanation lacks precision",
                        "4": "Partially correct but confuses concepts",
                        "1": "Fundamental misunderstanding",
                        "0": "No relevant understanding"
                    }
                },
                {
                    "criterion": "Provides working fix",
                    "max_points": 10,
                    "scoring_guide": {
                        "10": "Uses default argument trick or functools.partial correctly",
                        "7": "Working fix but suboptimal approach",
                        "4": "Attempted fix that partially works",
                        "1": "Fix does not address the issue",
                        "0": "No fix provided"
                    }
                }
            ],
            "follow_up_if_correct": "Now modify this to also track how many times each handler has been called, using a closure-based counter.",
            "estimated_time_minutes": 5,
        }

    def _mock_evaluation(self, prompt: str) -> dict:
        has_misconception = random.random() < 0.4
        score = round(random.uniform(0.2, 0.5), 2) if has_misconception else round(random.uniform(0.6, 0.95), 2)

        misconceptions = []
        if has_misconception:
            misconceptions.append({
                "misconception_id": "closure_late_binding",
                "confidence": round(random.uniform(0.7, 0.95), 2),
                "evidence": "Learner attempted to use a global variable instead of recognizing the closure capture issue.",
            })

        return {
            "rubric_scores": [
                {"criterion": "Correctly identifies the core issue", "score": int(score * 10), "evidence": "Learner showed partial understanding of variable scoping."},
                {"criterion": "Provides working fix", "score": int(score * 8), "evidence": "The proposed fix addresses the surface issue."},
            ],
            "total_score": score,
            "misconceptions_detected": misconceptions,
            "understanding_level": "deep" if score >= 0.7 else "partial" if score >= 0.4 else "surface",
            "reasoning": f"The learner demonstrates {'solid' if score >= 0.7 else 'partial' if score >= 0.4 else 'surface-level'} understanding. {'No misconceptions detected.' if not misconceptions else 'Detected misconception in closure variable capture timing.'}",
            "recommended_focus": "Practice with more closure scenarios in different contexts" if score < 0.7 else "Ready for next concept",
        }

    def _mock_teaching(self, prompt: str) -> dict:
        concept = self._extract_concept(prompt)
        strategy = "socratic"
        for s in ["debugging_exercise", "worked_examples", "analogy", "explain_back", "socratic"]:
            if s.replace("_", " ") in prompt.lower() or s in prompt.lower():
                strategy = s
                break

        content_map = {
            "socratic": f"Let me ask you something: when you define a function inside another function, what happens to the variables from the outer function? Think about this carefully.\n\nIf the outer function returns the inner function, does the inner function still have access to those outer variables? Why or why not?\n\nTake a moment to think, then share your reasoning.",
            "worked_examples": f"Let's walk through an example step by step.\n\n**Example 1: Simple Closure**\n```python\ndef make_greeting(name):\n    def greet():\n        return f'Hello, {{name}}!'\n    return greet\n\nhi_alice = make_greeting('Alice')\nprint(hi_alice())  # Output: Hello, Alice!\n```\n\n`make_greeting` has already returned, but `greet` still remembers `name`. That's a closure — a function that remembers its enclosing scope.\n\n**Example 2: Closure with State**\n```python\ndef make_counter():\n    count = 0\n    def increment():\n        nonlocal count\n        count += 1\n        return count\n    return increment\n\nc = make_counter()\nprint(c())  # 1\nprint(c())  # 2\n```\n\nNotice how `count` persists between calls. The closure captures and maintains state.",
            "debugging_exercise": f"Here's some code that has a bug related to closures. Find and fix it:\n\n```python\ndef create_multipliers():\n    multipliers = []\n    for i in range(5):\n        multipliers.append(lambda x: x * i)\n    return multipliers\n\nresult = create_multipliers()\nprint(result[0](10))  # Expected: 0, Actual: ?\nprint(result[1](10))  # Expected: 10, Actual: ?\nprint(result[4](10))  # Expected: 40, Actual: ?\n```\n\nRun this code mentally. What does each call actually return? Why? What's the fix?",
            "analogy": f"Think of a closure like a backpack. When you create a function inside another function, the inner function packs up all the variables it needs from the outer scope into its backpack. Even after the outer function is done and the room is cleaned up, the inner function still has its backpack with all those variables.\n\nThe key insight: the backpack doesn't contain *copies* of the values. It contains *live references* to the original variables. If someone changes those variables before you look in your backpack, you'll see the changed values.",
            "explain_back": f"You've been learning about closures. I'd like you to explain the concept to me as if I'm a fellow student who missed that class.\n\nSpecifically, explain:\n1. What is a closure?\n2. When would you use one?\n3. What's a common pitfall when creating closures in a loop?\n\nDon't worry about being perfect — I want to see how you think about it.",
        }

        return {
            "teaching_content": content_map.get(strategy, content_map["socratic"]),
            "check_question": "Can you write a function `make_adder(n)` that returns a function which adds `n` to any number passed to it?",
            "expected_check_answer": "def make_adder(n):\n    def add(x):\n        return x + n\n    return add",
            "concepts_referenced": ["python.functions", "python.scope"],
            "strategy_used": strategy,
            "estimated_time_minutes": 3,
        }

    def _mock_react_decision(self, system: str, prompt: str) -> dict:
        lower = prompt.lower()

        # Extract the TRIGGER line for precise matching
        trigger_line = ""
        for line in prompt.split("\n"):
            if line.strip().startswith("TRIGGER:"):
                trigger_line = line.lower()
                break

        # session start
        if "session_start" in trigger_line:
            if "decayed" in lower and "decay" in lower:
                concept = self._extract_react_field(prompt, "decayed_concepts")
                return {
                    "tool": "generate_test",
                    "args": {"concept_id": concept, "difficulty": 1},
                    "reasoning": "Returning learner with decayed concepts. Testing retention first.",
                    "respond_to_learner": True,
                }
            concept = self._extract_react_field(prompt, "next_concept")
            return {
                "tool": "teach",
                "args": {"concept_id": concept},
                "reasoning": "New session. Teaching the next recommended concept.",
                "respond_to_learner": True,
            }

        # self assessment received — match trigger line specifically (not full context)
        if "self_assessment" in trigger_line:
            concept = self._extract_react_field(prompt, "current concept")
            return {
                "tool": "generate_test",
                "args": {"concept_id": concept, "difficulty": 2},
                "reasoning": "Self-assessment received. Generating transfer test.",
                "respond_to_learner": True,
            }

        # learner answered — use UI state field for precise matching
        if "learner_answer" in trigger_line:
            # extract the actual UI state from context (format: "- UI state: <state>")
            ui_state = ""
            for line in prompt.split("\n"):
                if "ui state:" in line.lower():
                    ui_state = line.split(":")[-1].strip().lower()
                    break

            if ui_state in ("testing", "retesting"):
                return {
                    "tool": "evaluate_response",
                    "args": {"response": "(learner response)"},
                    "reasoning": "Learner answered a test. Evaluating their response.",
                    "respond_to_learner": True,
                }
            if ui_state in ("teaching", "reteaching"):
                concept = self._extract_react_field(prompt, "current concept")
                return {
                    "tool": "generate_practice",
                    "args": {"concept_id": concept},
                    "reasoning": "Teaching response received. Moving to practice.",
                    "respond_to_learner": True,
                }
            if ui_state == "practicing":
                return {
                    "tool": "ask_learner",
                    "args": {"question": "Rate your confidence from 1-10.", "question_type": "self_assess"},
                    "reasoning": "Practice complete. Collecting self-assessment before test.",
                    "respond_to_learner": True,
                }

        # chat
        if "chat" in trigger_line:
            return {
                "tool": "ask_learner",
                "args": {"question": "I hear you. Let's continue learning.", "question_type": "chat"},
                "reasoning": "Acknowledging chat message.",
                "respond_to_learner": True,
            }

        # fallback
        concept = self._extract_react_field(prompt, "current concept")
        if not concept:
            # pick first available concept from the knowledge graph
            from backend.services.knowledge_graph import knowledge_graph
            all_concepts = knowledge_graph.get_all_concepts()
            concept = all_concepts[0].id if all_concepts else "unknown"
        return {
            "tool": "teach",
            "args": {"concept_id": concept},
            "reasoning": "Continuing with teaching.",
            "respond_to_learner": True,
        }

    def _extract_react_field(self, prompt: str, field: str) -> str:
        lower_field = field.lower()
        # also match with spaces instead of underscores (e.g. "next_concept" → "next concept")
        alt_field = lower_field.replace("_", " ")
        for line in prompt.split("\n"):
            ll = line.lower().strip()
            if lower_field in ll or alt_field in ll:
                # try to extract a concept ID like domain.concept
                parts = line.split(":")
                if len(parts) > 1:
                    val = parts[-1].strip().strip("[]'\"")
                    # extract first domain.concept pattern
                    for word in val.replace(",", " ").split():
                        word = word.strip("[]'\"().!;")
                        if "." in word and len(word) > 3:
                            return word
                    if val and val != "None":
                        return val
        return ""

    def _mock_teacher_reflection(self, prompt: str) -> dict:
        return {
            "reflection": "The previous strategy showed moderate results but the learner struggles with abstract reasoning. Concrete examples work better.",
            "recommended_strategy": "worked_examples",
            "reasoning": "Worked examples provide concrete stepping stones that help bridge from familiar to abstract.",
            "confidence": 0.75,
        }

    def _mock_concept_tree(self, prompt: str) -> dict:
        topic = "generated_topic"
        for line in prompt.split("\n"):
            if "generate a learning tree for:" in line.lower():
                topic = line.split(":")[-1].strip().lower().replace(" ", "_")
                break
        domain = topic.split("_")[0] if "_" in topic else topic
        return {
            "domain": domain,
            "domain_description": f"Generated concepts for {topic}",
            "concepts": [
                {
                    "id": f"{domain}.basics",
                    "name": f"{topic.replace('_', ' ').title()} Basics",
                    "domain": domain,
                    "description": f"Foundational concepts of {topic.replace('_', ' ')}.",
                    "difficulty_tier": 1,
                    "prerequisites": [],
                    "common_misconceptions": [
                        {"id": "surface_understanding", "description": "Confuses terminology with understanding",
                         "indicators": ["Uses jargon without explanation", "Cannot give examples"],
                         "remediation_strategy": "worked_examples", "example_trigger": "Explain this in your own words"}
                    ],
                    "teaching_contexts": ["introductory tutorial", "first principles"],
                    "test_contexts": ["real-world application", "debugging scenario"],
                    "base_hours": 2.0,
                    "tags": [topic, "fundamentals"],
                },
                {
                    "id": f"{domain}.intermediate",
                    "name": f"{topic.replace('_', ' ').title()} Intermediate",
                    "domain": domain,
                    "description": f"Intermediate patterns and techniques in {topic.replace('_', ' ')}.",
                    "difficulty_tier": 2,
                    "prerequisites": [f"{domain}.basics"],
                    "common_misconceptions": [
                        {"id": "pattern_mismatch", "description": "Applies wrong pattern to problem",
                         "indicators": ["Uses brute force when elegant solution exists"],
                         "remediation_strategy": "debugging_exercise", "example_trigger": "Optimize this approach"}
                    ],
                    "teaching_contexts": ["project-based learning", "code review"],
                    "test_contexts": ["system design", "performance optimization"],
                    "base_hours": 3.0,
                    "tags": [topic, "intermediate"],
                },
                {
                    "id": f"{domain}.advanced",
                    "name": f"{topic.replace('_', ' ').title()} Advanced",
                    "domain": domain,
                    "description": f"Advanced concepts and edge cases in {topic.replace('_', ' ')}.",
                    "difficulty_tier": 3,
                    "prerequisites": [f"{domain}.intermediate"],
                    "common_misconceptions": [
                        {"id": "overengineering", "description": "Over-complicates solutions",
                         "indicators": ["Adds unnecessary abstraction"],
                         "remediation_strategy": "explain_back", "example_trigger": "Simplify this design"}
                    ],
                    "teaching_contexts": ["advanced workshop", "production systems"],
                    "test_contexts": ["failure recovery", "scaling challenges"],
                    "base_hours": 4.0,
                    "tags": [topic, "advanced"],
                },
            ],
        }

    def _mock_concept_expand(self, prompt: str) -> dict:
        return {
            "concepts": [
                {
                    "id": "expanded.sub_topic_1",
                    "name": "Sub-topic Deep Dive",
                    "description": "A deeper exploration of the parent concept.",
                    "difficulty_tier": 3,
                    "prerequisites": [],
                    "common_misconceptions": [
                        {"id": "shallow_dive", "description": "Stays at surface level",
                         "indicators": ["Cannot explain why"], "remediation_strategy": "socratic",
                         "example_trigger": "Why does this work?"}
                    ],
                    "teaching_contexts": ["deep dive session"],
                    "test_contexts": ["novel application"],
                    "base_hours": 2.0,
                    "tags": ["expanded"],
                },
            ],
        }

    def _mock_test_validation(self, prompt: str) -> dict:
        return {
            "is_valid": True,
            "issues": [],
            "quality_score": 0.85,
            "suggestion": "Test is well-structured for transfer assessment.",
        }

    def _mock_diagnostic_question(self, prompt: str) -> dict:
        concept_id = self._extract_concept(prompt)
        return {
            "question": f"Explain the core concept behind {concept_id.split('.')[-1] if '.' in concept_id else concept_id} in 2-3 sentences. What is its primary purpose?",
            "key_indicators": ["demonstrates understanding of core purpose", "can explain when to use it"],
            "concept_id": concept_id,
        }

    def _mock_diagnostic_evaluation(self, prompt: str) -> dict:
        score = round(random.uniform(0.3, 0.9), 2)
        level = "solid" if score >= 0.7 else "partial" if score >= 0.4 else "none"
        return {
            "score": score,
            "understanding": level,
            "notes": f"Learner shows {level} understanding of the concept.",
        }

    def _mock_career_role(self, prompt: str) -> dict:
        # Only check the role description line, not the full prompt
        # (which contains "quantitative_analyst" as an example ID)
        first_line = prompt.split("\n")[0].lower()
        if "quant" in first_line:
            return {
                "role": {
                    "id": "quantitative_analyst",
                    "title": "Junior Quantitative Analyst",
                    "description": "Entry-level quant building pricing models, back-testing trading strategies, and performing statistical analysis.",
                    "level": "mid",
                    "required_skills": [
                        {
                            "name": "Python Fluency",
                            "concept_ids": [
                                "python.variables", "python.control_flow", "python.functions",
                                "python.scope", "python.classes", "python.closures",
                                "python.decorators", "python.generators", "python.recursion",
                                "python.list_comp",
                            ],
                            "minimum_mastery": 0.75,
                            "weight": 0.35,
                        },
                        {
                            "name": "Algorithms & Data Structures",
                            "concept_ids": [
                                "ds.arrays_lists", "ds.hash_maps", "ds.trees",
                                "ds.sorting", "ds.searching",
                            ],
                            "minimum_mastery": 0.70,
                            "weight": 0.30,
                        },
                        {
                            "name": "Numerical & Recursive Thinking",
                            "concept_ids": [
                                "python.recursion", "ds.tree_traversal", "ds.graphs",
                            ],
                            "minimum_mastery": 0.70,
                            "weight": 0.20,
                        },
                        {
                            "name": "Data Pipeline Foundations",
                            "concept_ids": [
                                "python.file_io", "python.exceptions", "python.modules",
                            ],
                            "minimum_mastery": 0.60,
                            "weight": 0.15,
                        },
                    ],
                    "nice_to_have_skills": [],
                    "market_demand": "high",
                    "salary_range": {"min": 95000, "max": 150000, "currency": "USD"},
                    "growth_trend": "growing",
                    "related_roles": ["ml_engineer_entry", "data_structures_ta"],
                }
            }
        return {
            "role": {
                "id": "generated_role",
                "title": "Generated Role",
                "description": "A dynamically generated career role.",
                "level": "mid",
                "required_skills": [
                    {
                        "name": "Python Fundamentals",
                        "concept_ids": [
                            "python.variables", "python.control_flow",
                            "python.functions", "python.classes",
                        ],
                        "minimum_mastery": 0.7,
                        "weight": 0.50,
                    },
                    {
                        "name": "Data Structures",
                        "concept_ids": ["ds.arrays_lists", "ds.hash_maps"],
                        "minimum_mastery": 0.6,
                        "weight": 0.50,
                    },
                ],
                "nice_to_have_skills": [],
                "market_demand": "medium",
                "salary_range": {"min": 60000, "max": 90000, "currency": "USD"},
                "growth_trend": "stable",
                "related_roles": ["junior_python_developer"],
            }
        }

    def _mock_encouragement(self, prompt: str) -> dict:
        return {
            "message": "You're building real understanding here. Each challenge you work through makes the next one easier. Keep pushing!",
        }

    def _mock_generic(self, prompt: str) -> dict:
        return {"response": "Processed successfully.", "status": "ok"}

    def _extract_concept(self, prompt: str) -> str:
        for marker in ["CONCEPT BEING TESTED:", "CONCEPT TO TEACH:", "concept:"]:
            if marker in prompt:
                start = prompt.index(marker) + len(marker)
                line = prompt[start:start + 100].strip().split("\n")[0].strip()
                return line
        # fallback: first available concept
        from backend.services.knowledge_graph import knowledge_graph
        all_c = knowledge_graph.get_all_concepts()
        return all_c[0].id if all_c else "unknown"

    def get_stats(self) -> dict:
        return {
            "call_count": self.call_count,
            "total_tokens": self.total_tokens,
            "cache_size": len(self._cache),
            "mock_mode": self.use_mock,
        }


llm_client = LLMClient()
