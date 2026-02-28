"use client";

import Link from "next/link";

export interface SessionSummary {
  session_id: string;
  started_at: string;
  current_concept: string | null;
  concepts_covered: string[];
  concepts_mastered: string[];
  current_state: string;
}

interface ChatSidebarProps {
  sessions: SessionSummary[];
  activeSessionId: string | null;
  onNewChat: () => void;
  onSelectSession: (sessionId: string) => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  userName: string;
  onSignOut: () => void;
}

function groupByDate(sessions: SessionSummary[]): Record<string, SessionSummary[]> {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  const weekAgo = new Date(today);
  weekAgo.setDate(today.getDate() - 7);

  const groups: Record<string, SessionSummary[]> = {
    Today: [],
    Yesterday: [],
    "Previous 7 Days": [],
    Older: [],
  };

  for (const s of sessions) {
    const d = new Date(s.started_at);
    if (d >= today) groups["Today"].push(s);
    else if (d >= yesterday) groups["Yesterday"].push(s);
    else if (d >= weekAgo) groups["Previous 7 Days"].push(s);
    else groups["Older"].push(s);
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

export default function ChatSidebar({
  sessions,
  activeSessionId,
  onNewChat,
  onSelectSession,
  isCollapsed,
  onToggleCollapse,
  userName,
  onSignOut,
}: ChatSidebarProps) {
  const groups = groupByDate(sessions);

  return (
    <>
      {/* Hamburger toggle — always visible */}
      <button
        onClick={onToggleCollapse}
        className="fixed top-3 left-3 z-50 p-2 rounded-lg hover:bg-zinc-800 text-zinc-400 transition-colors"
        aria-label="Toggle sidebar"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M3 12h18M3 6h18M3 18h18" />
        </svg>
      </button>

      {/* Sidebar panel */}
      <aside
        className={`h-screen bg-[#171717] flex flex-col transition-all duration-300 ease-in-out overflow-hidden flex-shrink-0 ${
          isCollapsed ? "w-0" : "w-[260px]"
        }`}
      >
        <div className="flex flex-col h-full min-w-[260px]">
          {/* Top: New Chat */}
          <div className="px-3 pt-14 pb-3">
            <button
              onClick={onNewChat}
              className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg border border-zinc-700 text-sm text-zinc-300 hover:bg-zinc-800 hover:text-white transition-colors"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 5v14M5 12h14" />
              </svg>
              New Chat
            </button>
          </div>

          {/* Middle: Session list */}
          <div className="flex-1 overflow-y-auto px-2 scrollbar-thin">
            {Object.entries(groups).map(([label, items]) => {
              if (items.length === 0) return null;
              return (
                <div key={label} className="mb-3">
                  <h4 className="text-[10px] text-zinc-500 uppercase tracking-wider font-medium px-3 py-1.5">
                    {label}
                  </h4>
                  {items.map((s) => (
                    <button
                      key={s.session_id}
                      onClick={() => onSelectSession(s.session_id)}
                      className={`w-full text-left px-3 py-2 rounded-lg text-sm truncate transition-colors ${
                        s.session_id === activeSessionId
                          ? "bg-zinc-800 text-white"
                          : "text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200"
                      }`}
                    >
                      {formatConceptName(s.current_concept || s.concepts_covered[0] || null)}
                    </button>
                  ))}
                </div>
              );
            })}
            {sessions.length === 0 && (
              <p className="text-xs text-zinc-600 text-center py-8 px-3">
                No sessions yet. Start a new chat to begin learning!
              </p>
            )}
          </div>

          {/* Bottom: Nav links + User */}
          <div className="border-t border-zinc-800 px-3 py-3 space-y-1">
            <Link
              href="/knowledge-map"
              className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-zinc-400 hover:bg-zinc-800 hover:text-white transition-colors"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" /><path d="M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20M2 12h20" />
              </svg>
              Knowledge Map
            </Link>
            <Link
              href="/career"
              className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-zinc-400 hover:bg-zinc-800 hover:text-white transition-colors"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
              </svg>
              Career
            </Link>
            <Link
              href="/calibration"
              className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-zinc-400 hover:bg-zinc-800 hover:text-white transition-colors"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 20V10M6 20V4M18 20v-4" />
              </svg>
              Calibration
            </Link>
            <Link
              href="/agent-log"
              className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-zinc-400 hover:bg-zinc-800 hover:text-white transition-colors"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" />
              </svg>
              Agent Log
            </Link>
          </div>

          <div className="border-t border-zinc-800 px-3 py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="w-7 h-7 rounded-full bg-zinc-700 flex items-center justify-center flex-shrink-0">
                  <span className="text-xs font-medium text-zinc-300">
                    {userName ? userName.charAt(0).toUpperCase() : "U"}
                  </span>
                </div>
                <span className="text-sm text-zinc-400 truncate">{userName || "User"}</span>
              </div>
              <button
                onClick={onSignOut}
                className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors flex-shrink-0"
              >
                Sign Out
              </button>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
