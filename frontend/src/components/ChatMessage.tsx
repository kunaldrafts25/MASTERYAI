"use client";

import MarkdownContent from "./MarkdownContent";

const PHASE_LABELS: Record<string, { label: string; color: string }> = {
  teach: { label: "Learning", color: "bg-green-500/20 text-green-400 border-green-500/30" },
  practice: { label: "Practice", color: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30" },
  self_assess: { label: "Self-Assessment", color: "bg-blue-500/20 text-blue-400 border-blue-500/30" },
  transfer_test: { label: "Testing", color: "bg-red-500/20 text-red-400 border-red-500/30" },
  mastered_and_advance: { label: "Mastered!", color: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" },
  mastered_all_done: { label: "Complete!", color: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" },
  reteach: { label: "Review", color: "bg-orange-500/20 text-orange-400 border-orange-500/30" },
  retest: { label: "Retesting", color: "bg-orange-500/20 text-orange-400 border-orange-500/30" },
  decay_check: { label: "Retention Check", color: "bg-purple-500/20 text-purple-400 border-purple-500/30" },
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
    <span className={`inline-block text-[10px] px-2 py-0.5 rounded-full border font-medium mb-1.5 ${phase.color}`}>
      {phase.label}
    </span>
  );
}

export default function ChatMessage({ role, content, action, streaming }: ChatMessageProps) {
  if (role === "learner") {
    return (
      <div className="flex justify-end">
        <div className="bg-blue-600 rounded-2xl rounded-br-sm px-4 py-3 max-w-[80%]">
          <span className="text-sm text-white whitespace-pre-wrap">{content}</span>
        </div>
      </div>
    );
  }

  if (role === "system") {
    return (
      <div className="max-w-3xl mx-auto">
        <div className="text-center py-2">
          {action && <PhaseBadge action={action} />}
          <div className="text-xs text-zinc-400">
            <MarkdownContent content={content} />
          </div>
        </div>
      </div>
    );
  }

  // Professor message
  return (
    <div className="flex gap-3 max-w-3xl">
      <div className="w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center flex-shrink-0 mt-1">
        <span className="text-white text-xs font-bold">P</span>
      </div>
      <div className="flex-1 min-w-0">
        {action && <PhaseBadge action={action} />}
        <div className="text-sm text-zinc-200 leading-relaxed">
          <MarkdownContent content={content} />
          {streaming && (
            <span className="inline-block w-1.5 h-4 bg-emerald-400 ml-0.5 animate-pulse" />
          )}
        </div>
      </div>
    </div>
  );
}
