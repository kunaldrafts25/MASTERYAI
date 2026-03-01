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
      {/* Mobile backdrop overlay */}
      {!isCollapsed && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={onToggleCollapse}
        />
      )}

      {/* Sidebar panel */}
      <aside
        className={`
          fixed md:relative z-50 h-screen bg-[#171717] flex flex-col
          transition-transform duration-300 ease-in-out flex-shrink-0
          w-[260px]
          ${isCollapsed ? "-translate-x-full" : "translate-x-0"}
        `}
      >
        {/* Header: sidebar toggle + new chat */}
        <div className="flex items-center justify-between px-3 pt-3 pb-2">
          <button
            onClick={onToggleCollapse}
            className="p-2 rounded-lg hover:bg-white/10 text-[#ececec] transition-colors"
            aria-label="Close sidebar"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 12h18M3 6h18M3 18h18" />
            </svg>
          </button>
          <button
            onClick={onNewChat}
            className="p-2 rounded-lg hover:bg-white/10 text-[#ececec] transition-colors"
            aria-label="New Chat"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 20h9M16.5 3.5a2.121 2.121 0 113 3L7 19l-4 1 1-4L16.5 3.5z" />
            </svg>
          </button>
        </div>

        {/* Session list */}
        <div className="flex-1 overflow-y-auto px-2 scrollbar-thin">
          {Object.entries(groups).map(([label, items]) => {
            if (items.length === 0) return null;
            return (
              <div key={label} className="mb-1 mt-3">
                <h4 className="text-xs text-zinc-500 font-medium px-3 py-1.5">
                  {label}
                </h4>
                {items.map((s) => (
                  <button
                    key={s.session_id}
                    onClick={() => onSelectSession(s.session_id)}
                    className={`
                      w-full text-left px-3 py-2 rounded-lg text-sm truncate
                      transition-colors
                      ${s.session_id === activeSessionId
                        ? "bg-white/10 text-[#ececec]"
                        : "text-zinc-400 hover:bg-white/5 hover:text-[#ececec]"
                      }
                    `}
                  >
                    {formatConceptName(s.current_concept || s.concepts_covered[0] || null)}
                  </button>
                ))}
              </div>
            );
          })}
          {sessions.length === 0 && (
            <p className="text-xs text-zinc-600 text-center py-8 px-3">
              No sessions yet. Start a new chat!
            </p>
          )}
        </div>

        {/* Bottom navigation links */}
        <div className="border-t border-white/5 px-2 py-2 space-y-0.5">
          <Link href="/knowledge-map"
            className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-zinc-400 hover:bg-white/5 hover:text-[#ececec] transition-colors">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <circle cx="12" cy="12" r="10" /><path d="M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20M2 12h20" />
            </svg>
            Knowledge Map
          </Link>
          <Link href="/career"
            className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-zinc-400 hover:bg-white/5 hover:text-[#ececec] transition-colors">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
            </svg>
            Career
          </Link>
          <Link href="/calibration"
            className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-zinc-400 hover:bg-white/5 hover:text-[#ececec] transition-colors">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M12 20V10M6 20V4M18 20v-4" />
            </svg>
            Calibration
          </Link>
        </div>

        {/* User profile footer */}
        <div className="border-t border-white/5 px-3 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-8 h-8 rounded-full bg-[#2f2f2f] flex items-center justify-center flex-shrink-0 border border-white/10">
                <span className="text-sm font-medium text-[#ececec]">
                  {userName ? userName.charAt(0).toUpperCase() : "U"}
                </span>
              </div>
              <span className="text-sm text-zinc-300 truncate">{userName || "User"}</span>
            </div>
            <button
              onClick={onSignOut}
              className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors flex-shrink-0"
            >
              Sign Out
            </button>
          </div>
        </div>
      </aside>

      {/* Floating hamburger when sidebar is collapsed */}
      {isCollapsed && (
        <button
          onClick={onToggleCollapse}
          className="fixed top-3 left-3 z-40 p-2 rounded-lg hover:bg-white/10 text-[#ececec] transition-colors"
          aria-label="Open sidebar"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 12h18M3 6h18M3 18h18" />
          </svg>
        </button>
      )}
    </>
  );
}
