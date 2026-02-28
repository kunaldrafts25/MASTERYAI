"use client";

import { useState, useEffect, useRef, useCallback, Suspense } from "react";
import { useRouter } from "next/navigation";
import { streamStartSession, streamRespond, StreamHandlers } from "@/lib/sse";
import { getLearnerSessions } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import ChatSidebar, { SessionSummary } from "@/components/ChatSidebar";
import ChatMessage from "@/components/ChatMessage";
import WelcomeScreen from "@/components/WelcomeScreen";

// ── Types ──────────────────────────────────────────────────────────────

interface Message {
  id: string;
  role: "professor" | "learner" | "system";
  content: string;
  action?: string;
}

interface ConceptInfo {
  id: string;
  name: string;
  domain?: string;
}

interface CalibrationData {
  self_assessment: number;
  actual_score: number;
  gap: number;
}

// ── Constants ──────────────────────────────────────────────────────────

const TOOL_LABELS: Record<string, string> = {
  teach: "Preparing lesson...",
  generate_test: "Creating transfer test...",
  evaluate_response: "Evaluating your answer...",
  generate_practice: "Generating practice problems...",
  ask_learner: "Preparing question...",
  select_next_concept: "Selecting next concept...",
  mark_mastered: "Updating mastery...",
  check_career_impact: "Checking career impact...",
  generate_concepts: "Building your learning path...",
};

// ── Helpers ────────────────────────────────────────────────────────────

let msgCounter = 0;
function nextId(): string {
  return `msg-${++msgCounter}`;
}

// ── Main Component ─────────────────────────────────────────────────────

function SessionContent() {
  const { auth, logout } = useAuth();
  const router = useRouter();
  const learnerId = auth.learnerId || "";

  // Sidebar state
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);

  // Session state
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);

  // Input state
  const [input, setInput] = useState("");
  const [confidence, setConfidence] = useState(5);
  const [currentAction, setCurrentAction] = useState("");
  const [concept, setConcept] = useState<ConceptInfo | null>(null);
  const [calibration, setCalibration] = useState<CalibrationData | null>(null);

  // Streaming state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [thinkingAgent, setThinkingAgent] = useState("");
  const [activeTool, setActiveTool] = useState("");
  const [streamingText, setStreamingText] = useState("");

  const chatEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // ── Effects ──────────────────────────────────────────────────────────

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText, thinkingAgent]);

  useEffect(() => {
    if (!learnerId) return;
    getLearnerSessions(learnerId)
      .then(setSessions)
      .catch(() => {});
  }, [learnerId]);

  // ── Message helpers ──────────────────────────────────────────────────

  function addMessage(role: Message["role"], content: string | any, action?: string) {
    const text = typeof content === "string" ? content : JSON.stringify(content, null, 2);
    setMessages((prev) => [...prev, { id: nextId(), role, content: text, action }]);
  }

  function refreshSessions() {
    if (learnerId) {
      getLearnerSessions(learnerId)
        .then(setSessions)
        .catch(() => {});
    }
  }

  // ── SSE Handlers ─────────────────────────────────────────────────────

  const createHandlers = useCallback((): StreamHandlers => {
    let textBuffer = "";

    return {
      onAcknowledged: () => {
        setError("");
      },
      onAgentThinking: (agent: string) => {
        setThinkingAgent(agent);
      },
      onThinkingComplete: () => {
        setThinkingAgent("");
      },
      onTextChunk: (chunk: string, final: boolean) => {
        textBuffer += chunk;
        setStreamingText(textBuffer);
        if (final) {
          textBuffer = "";
        }
      },
      onToolStart: (toolName: string, agent: string) => {
        setActiveTool(toolName);
        setThinkingAgent(agent);
      },
      onToolComplete: () => {
        setActiveTool("");
      },
      onResult: (data: any) => {
        setStreamingText("");
        setThinkingAgent("");
        setActiveTool("");
        handleActionResponse(data);
      },
      onError: (message: string) => {
        setError(message);
        setLoading(false);
        setThinkingAgent("");
        setActiveTool("");
        setStreamingText("");
      },
      onComplete: () => {
        setLoading(false);
        setThinkingAgent("");
        setActiveTool("");
      },
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Session management ───────────────────────────────────────────────

  async function startNewSession(topic?: string) {
    setMessages([]);
    setCurrentAction("");
    setConcept(null);
    setCalibration(null);
    setError("");
    setLoading(true);
    setActiveSessionId(null);

    try {
      await streamStartSession(
        learnerId,
        {
          ...createHandlers(),
          onResult: (data: any) => {
            setStreamingText("");
            setThinkingAgent("");
            setActiveTool("");
            if (data.session_id) {
              setActiveSessionId(data.session_id);
              refreshSessions();
            }
            handleActionResponse(data);
          },
        },
        topic
      );
    } catch (err: any) {
      setError(err.message || "Failed to start session");
      setLoading(false);
    }
  }

  function handleNewChat() {
    setActiveSessionId(null);
    setMessages([]);
    setCurrentAction("");
    setConcept(null);
    setCalibration(null);
    setError("");
    setStreamingText("");
    setInput("");
  }

  function handleSelectSession(sessionId: string) {
    // For now, just highlight it in the sidebar
    // Future: load session messages and allow continuation
    setActiveSessionId(sessionId);
  }

  function handleSignOut() {
    logout();
    router.push("/login");
  }

  // ── Action Response Handler ──────────────────────────────────────────

  function handleActionResponse(res: any) {
    const action = res.action || "";
    setCurrentAction(action);

    if (res.concept) setConcept(res.concept);
    if (res.calibration) setCalibration(res.calibration);

    const lang = res.concept?.domain || res.next_concept?.domain || concept?.domain || "";

    switch (action) {
      case "teach":
      case "decay_check": {
        const content = res.content;
        const text =
          content?.explanation ||
          content?.teaching_content ||
          content?.message ||
          (typeof content === "string" ? content : JSON.stringify(content, null, 2));
        const codeAppend = content?.code_example
          ? `\n\n\`\`\`${lang}\n${content.code_example}\n\`\`\``
          : "";
        addMessage("professor", text + codeAppend, action);
        break;
      }
      case "practice": {
        const problems = res.content?.problems;
        const msg = res.content?.message || "Let's practice what we just covered.";
        if (Array.isArray(problems) && problems.length > 0) {
          const problemText = problems
            .map((p: any, i: number) => {
              const statement =
                p.problem_statement || p.problem || p.question || (typeof p === "string" ? p : JSON.stringify(p));
              const hints =
                Array.isArray(p.hints) && p.hints.length > 0
                  ? `\n\n**Hints:**\n${p.hints.map((h: string) => `- ${h}`).join("\n")}`
                  : p.hint
                  ? `\n\n*Hint: ${p.hint}*`
                  : "";
              return `### Problem ${i + 1}\n\n${statement}${hints}`;
            })
            .join("\n\n---\n\n");
          addMessage("professor", msg + "\n\n" + problemText, action);
        } else {
          addMessage("professor", msg, action);
        }
        break;
      }
      case "self_assess": {
        const msg = res.content?.message || "How confident do you feel about this concept?";
        addMessage("system", msg, action);
        break;
      }
      case "transfer_test": {
        const test = res.content;
        const prompt =
          test?.problem_statement ||
          test?.question ||
          test?.message ||
          (typeof test === "string" ? test : JSON.stringify(test, null, 2));
        const context = test?.context_description ? `\n\n**Context:** ${test.context_description}` : "";
        const starter = test?.starter_code ? `\n\n\`\`\`${lang}\n${test.starter_code}\n\`\`\`` : "";
        addMessage("professor", prompt + context + starter, action);
        break;
      }
      case "mastered_and_advance": {
        const evalData = res.evaluation;
        const score = evalData?.total_score ?? "N/A";
        addMessage(
          "system",
          `Concept mastered! Score: ${typeof score === "number" ? (score * 100).toFixed(0) : score}%`,
          action
        );
        if (res.calibration) {
          addMessage(
            "system",
            `Calibration \u2014 Confidence: ${(res.calibration.self_assessment * 100).toFixed(0)}% | Actual: ${(
              res.calibration.actual_score * 100
            ).toFixed(0)}% | Gap: ${(res.calibration.gap * 100).toFixed(0)}%`
          );
        }
        if (res.next_concept) {
          setConcept(res.next_concept);
          addMessage("system", `Moving on to: **${res.next_concept.name || res.next_concept.id}**`);
        }
        if (res.next_content) {
          const text =
            res.next_content.explanation ||
            res.next_content.teaching_content ||
            res.next_content.message ||
            JSON.stringify(res.next_content, null, 2);
          const codeAppend = res.next_content.code_example
            ? `\n\n\`\`\`${lang}\n${res.next_content.code_example}\n\`\`\``
            : "";
          addMessage("professor", text + codeAppend, "teach");
          setCurrentAction("teach");
        }
        break;
      }
      case "mastered_all_done": {
        addMessage("system", "You've mastered all available concepts!", action);
        if (res.calibration) {
          addMessage(
            "system",
            `Final calibration \u2014 Confidence: ${(res.calibration.self_assessment * 100).toFixed(0)}% | Actual: ${(
              res.calibration.actual_score * 100
            ).toFixed(0)}%`
          );
        }
        break;
      }
      case "retest": {
        addMessage(
          "system",
          `Partial mastery (${((res.evaluation?.total_score || 0) * 100).toFixed(0)}%). Let's try a different approach.`,
          action
        );
        const test = res.content;
        if (test) {
          const prompt =
            test.problem_statement || test.question || (typeof test === "string" ? test : JSON.stringify(test, null, 2));
          const starter = test.starter_code ? `\n\n\`\`\`${lang}\n${test.starter_code}\n\`\`\`` : "";
          addMessage("professor", prompt + starter, "transfer_test");
        }
        setCurrentAction("transfer_test");
        break;
      }
      case "reteach": {
        const evalScore = ((res.evaluation?.total_score || 0) * 100).toFixed(0);
        addMessage("system", `Score: ${evalScore}%. Let's revisit this concept with a different approach.`, action);
        if (res.misconceptions_detected?.length) {
          addMessage("system", `Areas to improve: ${res.misconceptions_detected.join(", ")}`);
        }
        const content = res.content;
        const text =
          content?.explanation ||
          content?.teaching_content ||
          content?.message ||
          (typeof content === "string" ? content : JSON.stringify(content, null, 2));
        const codeAppend = content?.code_example
          ? `\n\n\`\`\`${lang}\n${content.code_example}\n\`\`\``
          : "";
        addMessage("professor", text + codeAppend, "teach");
        setCurrentAction("teach");
        break;
      }
      case "complete": {
        addMessage("system", res.content?.message || "Session complete!", action);
        break;
      }
      default: {
        if (res.content?.message) {
          addMessage("system", res.content.message, action);
        }
      }
    }
  }

  // ── Submit Handler ───────────────────────────────────────────────────

  async function handleSubmit() {
    if (loading || !activeSessionId) return;

    if (currentAction === "self_assess") {
      addMessage("learner", `Confidence: ${confidence}/10`);
      setLoading(true);
      try {
        await streamRespond(
          activeSessionId,
          { response_type: "self_assessment", content: "", confidence },
          createHandlers()
        );
      } catch (err: any) {
        setError(err.message);
        setLoading(false);
      }
      return;
    }

    const text = input.trim();
    if (!text) return;

    addMessage("learner", text);
    setInput("");
    setLoading(true);
    try {
      await streamRespond(activeSessionId, { response_type: "answer", content: text }, createHandlers());
    } catch (err: any) {
      setError(err.message);
      setLoading(false);
    }
  }

  // ── Render ───────────────────────────────────────────────────────────

  const isProcessing = loading || !!thinkingAgent;

  if (!learnerId) {
    return (
      <div className="h-screen flex items-center justify-center bg-[#0a0a0a]">
        <div className="text-center">
          <p className="text-zinc-400 mb-4">No learner found.</p>
          <a href="/login" className="text-white underline hover:text-zinc-300">
            Sign in to start learning
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-[#0a0a0a]">
      {/* Sidebar */}
      <ChatSidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onNewChat={handleNewChat}
        onSelectSession={handleSelectSession}
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        userName={auth.name || ""}
        onSignOut={handleSignOut}
      />

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {activeSessionId === null ? (
          /* Welcome screen */
          <WelcomeScreen
            onStartSession={startNewSession}
            loading={loading}
            userName={auth.name || ""}
          />
        ) : (
          /* Active chat */
          <>
            {/* Concept + Phase header */}
            {(concept || activeTool) && (
              <div className="px-5 py-2 border-b border-white/5 flex items-center justify-between bg-zinc-900/30">
                <div className="flex items-center gap-2">
                  {concept && (
                    <span className="text-xs text-zinc-400">
                      Learning: <span className="text-zinc-200 font-medium">{concept.name || concept.id}</span>
                    </span>
                  )}
                </div>
                {activeTool && (
                  <span className="text-[10px] px-2.5 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse">
                    {TOOL_LABELS[activeTool] || activeTool}
                  </span>
                )}
              </div>
            )}

            {/* Messages */}
            <div className="flex-1 overflow-y-auto scrollbar-thin">
              <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
                {messages.map((msg) => (
                  <ChatMessage
                    key={msg.id}
                    role={msg.role}
                    content={msg.content}
                    action={msg.action}
                  />
                ))}

                {/* Streaming preview */}
                {streamingText && (
                  <ChatMessage role="professor" content={streamingText} streaming />
                )}

                {/* Thinking indicator */}
                {isProcessing && !streamingText && (
                  <div className="flex gap-3 max-w-3xl">
                    <div className="w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center flex-shrink-0">
                      <span className="text-white text-xs font-bold">P</span>
                    </div>
                    <div className="flex items-center gap-3 py-3">
                      <div className="flex items-center gap-1.5">
                        <span className="w-2 h-2 bg-zinc-500 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                        <span className="w-2 h-2 bg-zinc-500 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                        <span className="w-2 h-2 bg-zinc-500 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                      </div>
                      {activeTool ? (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
                          {TOOL_LABELS[activeTool] || activeTool}
                        </span>
                      ) : thinkingAgent ? (
                        <span className="text-xs text-zinc-500">Thinking...</span>
                      ) : null}
                    </div>
                  </div>
                )}

                <div ref={chatEndRef} />
              </div>
            </div>

            {/* Calibration bar */}
            {calibration && (
              <div className="max-w-3xl mx-auto w-full px-4 py-1.5 flex gap-6 text-xs">
                <span className="text-zinc-500">
                  Confidence: <span className="text-zinc-300">{(calibration.self_assessment * 100).toFixed(0)}%</span>
                </span>
                <span className="text-zinc-500">
                  Actual: <span className="text-zinc-300">{(calibration.actual_score * 100).toFixed(0)}%</span>
                </span>
                <span className={Math.abs(calibration.gap) > 0.2 ? "text-red-400" : "text-green-400"}>
                  Gap: {(calibration.gap * 100).toFixed(0)}%
                </span>
              </div>
            )}

            {/* Input area */}
            <div className="border-t border-white/10">
              <div className="max-w-3xl mx-auto px-4 py-4">
                {currentAction === "self_assess" ? (
                  <div className="bg-zinc-800/60 border border-zinc-700 rounded-xl p-4 space-y-3">
                    <label className="text-xs text-zinc-400 uppercase tracking-wider">
                      How confident do you feel? (1-10)
                    </label>
                    <div className="flex items-center gap-4">
                      <span className="text-lg font-bold text-white w-8 text-center">{confidence}</span>
                      <input
                        type="range"
                        min={1}
                        max={10}
                        value={confidence}
                        onChange={(e) => setConfidence(Number(e.target.value))}
                        className="flex-1 accent-emerald-500 h-2"
                      />
                    </div>
                    <button
                      onClick={handleSubmit}
                      disabled={isProcessing}
                      className="w-full bg-emerald-600 text-white text-sm font-medium py-2.5 rounded-lg
                                 hover:bg-emerald-500 transition-colors disabled:opacity-50"
                    >
                      Submit Confidence
                    </button>
                  </div>
                ) : (
                  <div className="relative">
                    <textarea
                      ref={inputRef}
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                          e.preventDefault();
                          handleSubmit();
                        }
                      }}
                      placeholder={
                        currentAction === "practice" || currentAction === "transfer_test"
                          ? "Type your answer..."
                          : "Type your response..."
                      }
                      rows={1}
                      disabled={isProcessing}
                      className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-3 pr-12
                                 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-zinc-500
                                 resize-none disabled:opacity-50 max-h-32 overflow-y-auto transition-colors"
                    />
                    <button
                      onClick={handleSubmit}
                      disabled={isProcessing || !input.trim()}
                      className="absolute right-2 bottom-2.5 p-1.5 rounded-lg
                                 bg-white text-black hover:bg-zinc-200 transition-colors
                                 disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M12 19V5M5 12l7-7 7 7" />
                      </svg>
                    </button>
                  </div>
                )}
                {error && <p className="text-red-400 text-xs mt-2">{error}</p>}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default function SessionPage() {
  return (
    <Suspense
      fallback={
        <div className="h-screen flex items-center justify-center bg-[#0a0a0a]">
          <div className="text-zinc-500 animate-pulse">Loading...</div>
        </div>
      }
    >
      <SessionContent />
    </Suspense>
  );
}
