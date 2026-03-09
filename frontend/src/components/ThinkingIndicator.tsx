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
    <div className="py-1.5 md:py-2">
      <div className="flex justify-start max-w-chat mx-auto px-3 md:px-4">
        <div className="flex items-start gap-2.5">
          <div className="w-7 h-7 rounded-full bg-accent flex items-center justify-center flex-shrink-0 mt-0.5">
            <span className="text-white text-xs font-bold">P</span>
          </div>
          <div className="bg-input-bg border border-white/10 rounded-2xl rounded-tl-md px-4 py-3">
            <div className="flex items-center gap-3">
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
      </div>
    </div>
  );
}
