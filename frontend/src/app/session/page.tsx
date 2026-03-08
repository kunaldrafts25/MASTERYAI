"use client";

import { useEffect, useRef, Suspense } from "react";
import { useRouter } from "next/navigation";
import { streamStartSession, streamRespond } from "@/lib/sse";
import { getLearnerSessions } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useSessionState } from "@/lib/hooks/useSessionState";
import { useStreaming } from "@/lib/hooks/useStreaming";
import ChatSidebar, { SessionSummary } from "@/components/ChatSidebar";
import ChatMessage from "@/components/ChatMessage";
import ChatInput from "@/components/ChatInput";
import WelcomeScreen from "@/components/WelcomeScreen";
import ThinkingIndicator from "@/components/ThinkingIndicator";
import CalibrationBar from "@/components/CalibrationBar";
import { useState } from "react";
import { ACTIONS, RESPONSE_TYPES, CONFIDENCE, PLACEHOLDERS, ROUTES } from "@/lib/constants";

function SessionContent() {
  const { auth, logout } = useAuth();
  const router = useRouter();
  const learnerId = auth.learnerId || "";

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);

  const session = useSessionState();
  const streaming = useStreaming(session.handleActionResponse, session.setError);

  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [session.messages, streaming.streamingText, streaming.thinkingAgent]);

  useEffect(() => {
    if (!learnerId) return;
    getLearnerSessions(learnerId)
      .then(setSessions)
      .catch(() => {});
  }, [learnerId]);

  function refreshSessions() {
    if (learnerId) {
      getLearnerSessions(learnerId).then(setSessions).catch(() => {});
    }
  }

  async function startNewSession(topic?: string) {
    session.resetSession();
    streaming.setLoading(true);

    try {
      await streamStartSession(
        learnerId,
        streaming.createHandlers((data) => {
          if (data.session_id) {
            session.setActiveSessionId(data.session_id);
            refreshSessions();
          }
          session.handleActionResponse(data);
        }),
        topic
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to start session";
      session.setError(msg);
      streaming.setLoading(false);
    }
  }

  function handleNewChat() {
    session.resetSession();
    streaming.resetStreaming();
  }

  function handleSignOut() {
    logout();
    router.push(ROUTES.LOGIN);
  }

  async function handleSubmit() {
    if (streaming.loading || !session.activeSessionId) return;

    if (session.currentAction === ACTIONS.SELF_ASSESS) {
      session.addMessage("learner", `Confidence: ${session.confidence}/${CONFIDENCE.MAX}`);
      streaming.setLoading(true);
      try {
        await streamRespond(
          session.activeSessionId,
          { response_type: RESPONSE_TYPES.SELF_ASSESSMENT, content: "", confidence: session.confidence },
          streaming.createHandlers()
        );
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Submit failed";
        session.setError(msg);
        streaming.setLoading(false);
      }
      return;
    }

    const text = session.input.trim();
    if (!text) return;

    // Determine if this is a learning answer or casual chat
    const learningPhases: string[] = [
      ACTIONS.TEACH, ACTIONS.PRACTICE, ACTIONS.TRANSFER_TEST,
      ACTIONS.RETEACH, ACTIONS.RETEST, ACTIONS.DECAY_CHECK,
    ];
    const responseType = learningPhases.includes(session.currentAction)
      ? RESPONSE_TYPES.ANSWER
      : RESPONSE_TYPES.CHAT;

    session.addMessage("learner", text);
    session.setInput("");
    streaming.setLoading(true);
    try {
      await streamRespond(
        session.activeSessionId,
        { response_type: responseType, content: text },
        streaming.createHandlers()
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Submit failed";
      session.setError(msg);
      streaming.setLoading(false);
    }
  }

  const isSelfAssess = session.currentAction === ACTIONS.SELF_ASSESS;

  if (!learnerId) {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <p className="text-zinc-400 mb-4">No learner found.</p>
          <a href={ROUTES.LOGIN} className="text-white underline hover:text-zinc-300">
            Sign in to start learning
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-background">
      <ChatSidebar
        sessions={sessions}
        activeSessionId={session.activeSessionId}
        onNewChat={handleNewChat}
        onSelectSession={session.setActiveSessionId}
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        userName={auth.name || ""}
        onSignOut={handleSignOut}
      />

      <div className="flex-1 flex flex-col min-w-0">
        {session.activeSessionId === null ? (
          <WelcomeScreen
            onStartSession={startNewSession}
            loading={streaming.loading}
            userName={auth.name || ""}
          />
        ) : (
          <>
            <div className="flex-1 overflow-y-auto scrollbar-thin">
              <div className="py-4">
                {session.messages.map((msg) => (
                  <ChatMessage
                    key={msg.id}
                    role={msg.role}
                    content={msg.content}
                    action={msg.action}
                  />
                ))}

                {streaming.streamingText && (
                  <ChatMessage
                    role="professor"
                    content={streaming.streamingText}
                    streaming
                  />
                )}

                {streaming.isProcessing && !streaming.streamingText && (
                  <ThinkingIndicator
                    activeTool={streaming.activeTool}
                    thinkingAgent={streaming.thinkingAgent}
                  />
                )}

                <div ref={chatEndRef} />
              </div>
            </div>

            {session.calibration && (
              <CalibrationBar calibration={session.calibration} />
            )}

            {session.error && (
              <div className="max-w-chat mx-auto w-full px-4">
                <p className="text-red-400 text-xs py-1">{session.error}</p>
              </div>
            )}

            <ChatInput
              value={session.input}
              onChange={session.setInput}
              onSubmit={handleSubmit}
              disabled={streaming.isProcessing}
              placeholder={
                session.currentAction === ACTIONS.PRACTICE ||
                session.currentAction === ACTIONS.TRANSFER_TEST
                  ? PLACEHOLDERS.ANSWER_INPUT
                  : PLACEHOLDERS.DEFAULT_INPUT
              }
              isSelfAssess={isSelfAssess}
              confidence={session.confidence}
              onConfidenceChange={session.setConfidence}
            />
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
        <div className="h-screen flex items-center justify-center bg-background">
          <div className="text-zinc-500 animate-pulse">Loading...</div>
        </div>
      }
    >
      <SessionContent />
    </Suspense>
  );
}
