import { TOOL_LABELS, TIMING } from "@/lib/constants";

interface ThinkingIndicatorProps {
  activeTool: string;
  thinkingAgent: string;
}

export default function ThinkingIndicator({
  activeTool,
  thinkingAgent,
}: ThinkingIndicatorProps) {
  return (
    <div className="py-4">
      <div className="flex gap-4 max-w-chat mx-auto px-4">
        <div className="w-7 h-7 rounded-full bg-accent flex items-center justify-center flex-shrink-0 mt-0.5">
          <span className="text-white text-xs font-bold">P</span>
        </div>
        <div className="flex items-center gap-3 py-1">
          <div className="flex items-center gap-1.5">
            {TIMING.BOUNCE_DELAYS.map((delay) => (
              <span
                key={delay}
                className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce"
                style={{ animationDelay: delay }}
              />
            ))}
          </div>
          {activeTool ? (
            <span className="text-xs px-2 py-0.5 rounded-full bg-white/5 text-zinc-400 border border-white/10">
              {TOOL_LABELS[activeTool] || activeTool}
            </span>
          ) : thinkingAgent ? (
            <span className="text-xs text-zinc-500">Thinking...</span>
          ) : null}
        </div>
      </div>
    </div>
  );
}
