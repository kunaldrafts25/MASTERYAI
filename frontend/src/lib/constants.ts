// ── Routes ────────────────────────────────────────────────────────────

export const ROUTES = {
  HOME: "/",
  LOGIN: "/login",
  REGISTER: "/register",
  SESSION: "/session",
  KNOWLEDGE_MAP: "/knowledge-map",
  CAREER: "/career",
  CALIBRATION: "/calibration",
  AGENT_LOG: "/agent-log",
  SETTINGS: "/settings",
  HISTORY: "/history",
} as const;

export const NAV_LINKS = [
  { href: ROUTES.SESSION, label: "Session" },
  { href: ROUTES.KNOWLEDGE_MAP, label: "Knowledge Map" },
  { href: ROUTES.CAREER, label: "Career" },
  { href: ROUTES.CALIBRATION, label: "Calibration" },
  { href: ROUTES.AGENT_LOG, label: "Agent Log" },
] as const;

export const SIDEBAR_LINKS = [
  {
    href: ROUTES.KNOWLEDGE_MAP,
    label: "Knowledge Map",
    icon: "M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20M2 12h20",
    viewBox: "0 0 24 24",
    isCircle: true,
  },
  {
    href: ROUTES.CAREER,
    label: "Career",
    icon: "M22 12h-4l-3 9L9 3l-3 9H2",
    viewBox: "0 0 24 24",
    isCircle: false,
  },
  {
    href: ROUTES.HISTORY,
    label: "History",
    icon: "M12 8v4l3 3m6-3a9 9 0 1 1-18 0 9 9 0 0 1 18 0z",
    viewBox: "0 0 24 24",
    isCircle: false,
  },
  {
    href: ROUTES.CALIBRATION,
    label: "Calibration",
    icon: "M12 20V10M6 20V4M18 20v-4",
    viewBox: "0 0 24 24",
    isCircle: false,
  },
] as const;

// ── Actions & Phases (match backend protocol) ────────────────────────

export const ACTIONS = {
  TEACH: "teach",
  PRACTICE: "practice",
  SELF_ASSESS: "self_assess",
  TRANSFER_TEST: "transfer_test",
  MASTERED_ADVANCE: "mastered_and_advance",
  MASTERED_DONE: "mastered_all_done",
  RETEACH: "reteach",
  RETEST: "retest",
  DECAY_CHECK: "decay_check",
  COMPLETE: "complete",
  CHAT_RESPONSE: "chat_response",
} as const;

export const RESPONSE_TYPES = {
  SELF_ASSESSMENT: "self_assessment",
  ANSWER: "answer",
  CHAT: "chat",
} as const;

export const PHASE_LABELS: Record<string, { label: string; color: string }> = {
  [ACTIONS.TEACH]: { label: "Learning", color: "text-emerald-400" },
  [ACTIONS.PRACTICE]: { label: "Practice", color: "text-yellow-400" },
  [ACTIONS.SELF_ASSESS]: { label: "Self-Assessment", color: "text-blue-400" },
  [ACTIONS.TRANSFER_TEST]: { label: "Testing", color: "text-red-400" },
  [ACTIONS.MASTERED_ADVANCE]: { label: "Mastered!", color: "text-emerald-400" },
  [ACTIONS.MASTERED_DONE]: { label: "Complete!", color: "text-emerald-400" },
  [ACTIONS.RETEACH]: { label: "Review", color: "text-orange-400" },
  [ACTIONS.RETEST]: { label: "Retesting", color: "text-orange-400" },
  [ACTIONS.DECAY_CHECK]: { label: "Retention Check", color: "text-purple-400" },
};

// ── Tool labels (backend tool names → user-facing text) ──────────────

export const TOOL_LABELS: Record<string, string> = {
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

// ── Agent styling (agent names → Tailwind classes) ───────────────────

export const AGENT_STYLES: Record<string, string> = {
  orchestrator: "text-blue-400 bg-blue-500/10 border-blue-500/20",
  examiner: "text-red-400 bg-red-500/10 border-red-500/20",
  teacher: "text-green-400 bg-green-500/10 border-green-500/20",
  curriculum: "text-purple-400 bg-purple-500/10 border-purple-500/20",
  career_mapper: "text-orange-400 bg-orange-500/10 border-orange-500/20",
};

export const DEFAULT_AGENT_STYLE = "text-zinc-400 bg-zinc-500/10 border-zinc-500/20";

// ── Knowledge graph visualization ────────────────────────────────────

export const GRAPH_STATUS_COLORS: Record<string, string> = {
  mastered: "#22c55e",
  practicing: "#eab308",
  testing: "#eab308",
  introduced: "#60a5fa",
  decayed: "#f97316",
  unknown: "#6b7280",
};

export const GRAPH_EDGE_COLORS = {
  transfer: "#8b5cf6",
  default: "#94a3b8",
} as const;

export const GRAPH_CONFIG = {
  HEIGHT: 600,
  LINK_DISTANCE: 100,
  CHARGE_STRENGTH: -200,
  COLLISION_PADDING: 4,
  NODE_BASE_RADIUS: 8,
  NODE_TIER_SCALE: 4,
  HALO_PADDING: 6,
  LABEL_OFFSET: 14,
  LABEL_FONT_SIZE: 11,
  LABEL_COLOR: "#cbd5e1",
  STROKE_WIDTH: 2,
  STROKE_COLOR: "#fff",
  EDGE_STROKE_WIDTH: 1.5,
  EDGE_DASH_PATTERN: "6 3",
  EDGE_DEFAULT_OPACITY: 0.6,
  ZOOM_MIN: 0.2,
  ZOOM_MAX: 5,
} as const;

// ── Calibration thresholds ───────────────────────────────────────────

export const CALIBRATION = {
  GAP_GOOD: 0.15,
  GAP_WARN: 0.25,
  GAP_ALERT: 0.2,
  COLOR_GOOD: "#22c55e",
  COLOR_WARN: "#eab308",
  COLOR_DANGER: "#ef4444",
  CHART_FILL: "#8884d8",
} as const;

// ── Career thresholds ────────────────────────────────────────────────

export const CAREER_THRESHOLDS = {
  HIGH: 0.7,
  MEDIUM: 0.3,
} as const;

export function scoreBarColor(score: number): string {
  if (score > CAREER_THRESHOLDS.HIGH) return "bg-green-500";
  if (score > CAREER_THRESHOLDS.MEDIUM) return "bg-yellow-500";
  return "bg-red-500";
}

// ── Confidence scale ─────────────────────────────────────────────────

export const CONFIDENCE = {
  MIN: 1,
  MAX: 10,
  DEFAULT: 5,
} as const;

// ── UI timing (ms) ──────────────────────────────────────────────────

export const TIMING = {
  COPY_FEEDBACK_MS: 2000,
  AGENT_LOG_POLL_MS: 3000,
  TEXTAREA_MAX_HEIGHT: 200,
  BOUNCE_DELAYS: ["0ms", "150ms", "300ms"],
} as const;

// ── Session date grouping labels ─────────────────────────────────────

export const SESSION_GROUPS = ["Today", "Yesterday", "Previous 7 Days", "Older"] as const;

// ── Placeholder text ─────────────────────────────────────────────────

export const PLACEHOLDERS = {
  DEFAULT_INPUT: "Message MasteryAI...",
  ANSWER_INPUT: "Type your answer...",
} as const;

// ── Landing page features ────────────────────────────────────────────

export const LANDING_FEATURES = [
  {
    title: "Transfer Testing",
    description:
      "Prove understanding by applying concepts in novel contexts, not just repeating examples.",
  },
  {
    title: "Multi-Agent AI",
    description:
      "5 specialized agents collaborate to teach, assess, and adapt your learning path.",
  },
  {
    title: "Career Intelligence",
    description:
      "Real-time career readiness scores tied to your actual mastery, not certificates.",
  },
] as const;

// ── Welcome screen suggestions ──────────────────────────────────────

export const LEARNING_SUGGESTIONS = [
  { label: "Learn Python", desc: "Start from the basics" },
  { label: "Understand recursion", desc: "With visual examples" },
  { label: "Data structures 101", desc: "Arrays, stacks, trees" },
  { label: "Learn JavaScript", desc: "Modern ES6+ syntax" },
] as const;

// ── App branding ─────────────────────────────────────────────────────

export const APP_NAME = "MasteryAI";
export const APP_TAGLINE = "AI-Powered Learning & Career Intelligence Platform";
export const APP_DISCLAIMER = "MasteryAI can make mistakes. Verify important information.";
