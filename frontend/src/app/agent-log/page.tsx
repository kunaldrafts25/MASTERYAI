"use client";

import { useSearchParams } from "next/navigation";
import { useState, useEffect, useRef, Suspense } from "react";
import { getEvents } from "@/lib/api";
import { NavBar } from "../providers";
import { AGENT_STYLES, DEFAULT_AGENT_STYLE, TIMING, ROUTES } from "@/lib/constants";

interface AgentEvent {
  event_id: string;
  event_type: string;
  source_agent: string;
  timestamp: string;
  learner_id: string;
  session_id: string;
  payload: Record<string, unknown>;
  reasoning: string;
}

function agentStyle(agent: string) {
  return AGENT_STYLES[agent] || DEFAULT_AGENT_STYLE;
}

function formatTime(ts: string) {
  try {
    const d = new Date(ts);
    return d.toLocaleTimeString();
  } catch {
    return ts;
  }
}

function AgentLogContent() {
  const params = useSearchParams();
  const sessionId = params.get("session_id") || "";

  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!sessionId) {
      setLoading(false);
      return;
    }
    doFetch();
    const interval = setInterval(doFetch, TIMING.AGENT_LOG_POLL_MS);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events.length]);

  async function doFetch() {
    try {
      const data = await getEvents(sessionId);
      setEvents(Array.isArray(data) ? (data as AgentEvent[]) : []);
      setError("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load events");
    }
    setLoading(false);
  }

  function toggleExpand(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  if (!sessionId) {
    return (
      <>
        <NavBar />
        <div className="text-center py-16">
          <div className="w-16 h-16 rounded-full bg-blue-600/20 flex items-center justify-center mx-auto mb-4">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#60a5fa" strokeWidth="1.5">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
              <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" />
            </svg>
          </div>
          <h2 className="text-lg font-medium text-zinc-300 mb-2">No session selected</h2>
          <p className="text-zinc-500 max-w-md mx-auto mb-6">
            Start a learning session first, then navigate here to see real-time agent decisions and reasoning.
          </p>
          <a
            href={ROUTES.SESSION}
            className="inline-block px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-500 transition-colors text-sm font-medium"
          >
            Start a session
          </a>
        </div>
      </>
    );
  }

  return (
    <>
    <NavBar />
    <div className="max-w-3xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Agent Decision Log</h1>
        <span className="text-xs text-zinc-500">Session: {sessionId.slice(0, 8)}...</span>
      </div>

      {error && <p className="text-red-400 text-sm mb-4">{error}</p>}

      {loading && events.length === 0 && (
        <p className="text-zinc-500 text-sm">Loading events...</p>
      )}

      {!loading && events.length === 0 && (
        <p className="text-zinc-500 text-sm">No events recorded yet.</p>
      )}

      <div className="space-y-3">
        {events.map((ev) => {
          const isExpanded = expanded.has(ev.event_id);
          const hasPayload = Object.keys(ev.payload || {}).length > 0;

          return (
            <div
              key={ev.event_id}
              className="border border-white/10 rounded-lg p-4 bg-zinc-900/30"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2 flex-wrap">
                  <span
                    className={`text-xs px-2 py-0.5 rounded border ${agentStyle(ev.source_agent)}`}
                  >
                    {ev.source_agent}
                  </span>
                  <span className="text-xs text-zinc-500 font-mono">
                    {ev.event_type}
                  </span>
                </div>
                <span className="text-xs text-zinc-600 whitespace-nowrap">
                  {formatTime(ev.timestamp)}
                </span>
              </div>

              {ev.reasoning && (
                <p className="text-sm text-zinc-300 mt-2">{ev.reasoning}</p>
              )}

              {hasPayload && (
                <div className="mt-2">
                  <button
                    onClick={() => toggleExpand(ev.event_id)}
                    className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
                  >
                    {isExpanded ? "Hide details" : "Show details"}
                  </button>
                  {isExpanded && (
                    <pre className="mt-2 text-xs text-zinc-400 bg-zinc-900/60 rounded p-3 overflow-x-auto font-mono">
                      {JSON.stringify(ev.payload, null, 2)}
                    </pre>
                  )}
                </div>
              )}
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>
    </div>
    </>
  );
}

export default function AgentLogPage() {
  return (
    <Suspense
      fallback={
        <div className="p-10 text-center text-zinc-500">Loading...</div>
      }
    >
      <AgentLogContent />
    </Suspense>
  );
}
