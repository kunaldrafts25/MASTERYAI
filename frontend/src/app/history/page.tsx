"use client";
import { useEffect, useState, Suspense } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { getLearnerSessions } from "@/lib/api";
import { NavBar } from "../providers";
import { ROUTES, SESSION_GROUPS } from "@/lib/constants";

interface SessionItem {
  session_id: string;
  started_at: string;
  current_concept: string | null;
  concepts_covered: string[];
  concepts_mastered: string[];
  current_state: string;
}

function groupByDate(sessions: SessionItem[]): Record<string, SessionItem[]> {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  const weekAgo = new Date(today);
  weekAgo.setDate(today.getDate() - 7);

  const groups: Record<string, SessionItem[]> = {};
  for (const label of SESSION_GROUPS) {
    groups[label] = [];
  }

  for (const s of sessions) {
    const d = new Date(s.started_at);
    if (d >= today) groups[SESSION_GROUPS[0]].push(s);
    else if (d >= yesterday) groups[SESSION_GROUPS[1]].push(s);
    else if (d >= weekAgo) groups[SESSION_GROUPS[2]].push(s);
    else groups[SESSION_GROUPS[3]].push(s);
  }
  return groups;
}

function formatConceptName(concept: string | null): string {
  if (!concept) return "New Session";
  return concept
    .replace(/^[a-z_]+\./, "")
    .replace(/[._-]/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function stateColor(state: string): string {
  if (state.includes("mastered")) return "text-emerald-400";
  if (state.includes("test") || state.includes("practice")) return "text-yellow-400";
  if (state.includes("teach")) return "text-blue-400";
  return "text-zinc-400";
}

function HistoryContent() {
  const { auth } = useAuth();
  const router = useRouter();
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!auth.learnerId) return;
    getLearnerSessions(auth.learnerId)
      .then((data) => setSessions(data))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [auth.learnerId]);

  if (!auth.token) {
    router.push(ROUTES.LOGIN);
    return null;
  }

  const groups = groupByDate(sessions);
  const totalMastered = new Set(sessions.flatMap((s) => s.concepts_mastered)).size;

  return (
    <>
      <NavBar />
      <div className="p-6 max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold text-white mb-1">Session History</h1>
        <p className="text-zinc-400 mb-6">
          {sessions.length} session{sessions.length !== 1 ? "s" : ""} &middot; {totalMastered} concept{totalMastered !== 1 ? "s" : ""} mastered
        </p>

        {loading && <p className="text-zinc-400">Loading...</p>}
        {error && <p className="text-red-400">{error}</p>}

        {!loading && sessions.length === 0 && (
          <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-8 text-center">
            <p className="text-zinc-400 mb-4">No sessions yet</p>
            <button
              onClick={() => router.push(ROUTES.SESSION)}
              className="px-4 py-2 bg-white text-black rounded-lg text-sm font-medium hover:bg-zinc-200 transition-colors"
            >
              Start Learning
            </button>
          </div>
        )}

        {!loading && Object.entries(groups).map(([label, items]) => {
          if (items.length === 0) return null;
          return (
            <div key={label} className="mb-6">
              <h2 className="text-sm font-medium text-zinc-500 mb-2">{label}</h2>
              <div className="space-y-2">
                {items.map((s) => (
                  <button
                    key={s.session_id}
                    onClick={() => router.push(`${ROUTES.SESSION}?session_id=${s.session_id}`)}
                    className="w-full text-left bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-3 hover:border-zinc-700 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-white font-medium">
                        {formatConceptName(s.current_concept || s.concepts_covered[0] || null)}
                      </span>
                      <span className="text-xs text-zinc-500">{formatDate(s.started_at)}</span>
                    </div>
                    <div className="flex items-center gap-4 text-xs">
                      <span className={stateColor(s.current_state)}>
                        {s.current_state.replace(/_/g, " ")}
                      </span>
                      <span className="text-zinc-500">
                        {s.concepts_covered.length} concept{s.concepts_covered.length !== 1 ? "s" : ""} covered
                      </span>
                      {s.concepts_mastered.length > 0 && (
                        <span className="text-emerald-400">
                          {s.concepts_mastered.length} mastered
                        </span>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}

export default function HistoryPage() {
  return (
    <Suspense fallback={<p className="text-zinc-400 p-8">Loading...</p>}>
      <HistoryContent />
    </Suspense>
  );
}
