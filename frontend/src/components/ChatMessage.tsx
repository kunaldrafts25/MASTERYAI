"use client";

import { memo } from "react";
import MarkdownContent from "./MarkdownContent";
import { PHASE_LABELS } from "@/lib/constants";

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

function ChatMessage({ role, content, action, streaming }: ChatMessageProps) {
  if (role === "learner") {
    return (
      <div className="py-1.5 md:py-2">
        <div className="flex justify-end max-w-chat mx-auto px-3 md:px-4">
          <div className="max-w-[80%]">
            <div className="bg-accent/20 border border-accent/30 rounded-2xl rounded-br-md px-4 py-2.5">
              <p className="text-sm md:text-[15px] text-foreground whitespace-pre-wrap leading-relaxed">
                {content}
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (role === "system") {
    return (
      <div className="py-2">
        <div className="max-w-chat mx-auto px-3 md:px-4">
          <div className="flex items-start gap-3">
            <div className="w-7 h-7 rounded-full bg-accent flex items-center justify-center flex-shrink-0 mt-0.5">
              <span className="text-white text-xs font-bold">P</span>
            </div>
            <div className="flex-1">
              {action && <PhaseBadge action={action} />}
              <div className="text-sm text-zinc-400">
                <MarkdownContent content={content} />
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Professor (AI) message — left-aligned bubble
  return (
    <div className="py-1.5 md:py-2">
      <div className="flex justify-start max-w-chat mx-auto px-3 md:px-4">
        <div className="flex items-start gap-2.5 max-w-[85%]">
          <div className="w-7 h-7 rounded-full bg-accent flex items-center justify-center flex-shrink-0 mt-0.5">
            <span className="text-white text-xs font-bold">P</span>
          </div>
          <div>
            {action && <PhaseBadge action={action} />}
            <div className="bg-input-bg border border-white/10 rounded-2xl rounded-tl-md px-4 py-2.5">
              <div className="text-sm md:text-[15px] text-foreground leading-relaxed">
                <MarkdownContent content={content} />
                {streaming && <span className="streaming-cursor" />}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default memo(ChatMessage);
