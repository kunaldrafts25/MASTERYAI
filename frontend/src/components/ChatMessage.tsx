"use client";

import MarkdownContent from "./MarkdownContent";

const PHASE_LABELS: Record<string, { label: string; color: string }> = {
  teach: { label: "Learning", color: "text-emerald-400" },
  practice: { label: "Practice", color: "text-yellow-400" },
  self_assess: { label: "Self-Assessment", color: "text-blue-400" },
  transfer_test: { label: "Testing", color: "text-red-400" },
  mastered_and_advance: { label: "Mastered!", color: "text-emerald-400" },
  mastered_all_done: { label: "Complete!", color: "text-emerald-400" },
  reteach: { label: "Review", color: "text-orange-400" },
  retest: { label: "Retesting", color: "text-orange-400" },
  decay_check: { label: "Retention Check", color: "text-purple-400" },
};

interface ChatMessageProps {
  role: "professor" | "learner" | "system";
  content: string;
  action?: string;
  streaming?: boolean;
}

function PhaseBadge({ action }: { action: string }) {
  const phase = PHASE_LABELS[action];
  if (!phase) return null;
  return (
    <span className={`inline-block text-xs font-medium mb-1 ${phase.color}`}>
      {phase.label}
    </span>
  );
}

export default function ChatMessage({ role, content, action, streaming }: ChatMessageProps) {
  // User (learner) message
  if (role === "learner") {
    return (
      <div className="group py-4">
        <div className="flex gap-4 max-w-chat mx-auto px-4">
          <div className="w-7 h-7 rounded-full bg-[#2f2f2f] flex items-center justify-center flex-shrink-0 mt-0.5 border border-white/10">
            <span className="text-xs font-medium text-[#ececec]">U</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-[15px] text-[#ececec] whitespace-pre-wrap leading-relaxed">
              {content}
            </p>
          </div>
        </div>
      </div>
    );
  }

  // System message (phase changes, mastery notifications)
  if (role === "system") {
    return (
      <div className="py-2">
        <div className="max-w-chat mx-auto flex gap-4 px-4">
          <div className="w-7 flex-shrink-0" />
          <div className="flex-1">
            {action && <PhaseBadge action={action} />}
            <div className="text-sm text-zinc-400">
              <MarkdownContent content={content} />
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Professor (assistant) message
  return (
    <div className="group py-4">
      <div className="flex gap-4 max-w-chat mx-auto px-4">
        <div className="w-7 h-7 rounded-full bg-[#10a37f] flex items-center justify-center flex-shrink-0 mt-0.5">
          <span className="text-white text-xs font-bold">P</span>
        </div>
        <div className="flex-1 min-w-0">
          {action && <PhaseBadge action={action} />}
          <div className="text-[15px] text-[#ececec] leading-relaxed">
            <MarkdownContent content={content} />
            {streaming && <span className="streaming-cursor" />}
          </div>
        </div>
      </div>
    </div>
  );
}
