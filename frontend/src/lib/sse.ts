// SSE streaming client - uses fetch+ReadableStream for POST-based SSE

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

export interface StreamHandlers {
  onAcknowledged?: () => void;
  onAgentThinking?: (agent: string, message: string) => void;
  onThinkingComplete?: () => void;
  onTextChunk?: (chunk: string, final: boolean) => void;
  onToolStart?: (toolName: string, agent: string) => void;
  onToolComplete?: (toolName: string, agent: string) => void;
  onPhaseChange?: (phase: string, concept: string) => void;
  onResult?: (data: any) => void;
  onError?: (message: string) => void;
  onComplete?: () => void;
}

async function streamRequest(
  path: string,
  body: object,
  handlers: StreamHandlers
): Promise<void> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const response = await fetch(`${API}${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const text = await response.text();
    handlers.onError?.(text || `HTTP ${response.status}`);
    return;
  }

  if (!response.body) {
    handlers.onError?.("No response body");
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Parse SSE lines: "data: {...}\n\n"
      const lines = buffer.split("\n\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith(":")) continue; // keepalive comment

        const dataPrefix = "data: ";
        if (!trimmed.startsWith(dataPrefix)) continue;

        try {
          const json = JSON.parse(trimmed.slice(dataPrefix.length));
          dispatchEvent(json, handlers);
        } catch {
          // skip malformed JSON
        }
      }
    }
  } finally {
    reader.releaseLock();
  }

  handlers.onComplete?.();
}

function dispatchEvent(event: any, handlers: StreamHandlers) {
  switch (event.type) {
    case "acknowledged":
      handlers.onAcknowledged?.();
      break;
    case "agent_thinking":
      handlers.onAgentThinking?.(event.agent || "", event.message || "");
      break;
    case "thinking_complete":
      handlers.onThinkingComplete?.();
      break;
    case "text_chunk":
      handlers.onTextChunk?.(event.chunk || "", event.final || false);
      break;
    case "tool_start":
      handlers.onToolStart?.(event.tool_name || "", event.agent || "");
      break;
    case "tool_complete":
      handlers.onToolComplete?.(event.tool_name || "", event.agent || "");
      break;
    case "phase_change":
      handlers.onPhaseChange?.(event.phase || "", event.concept || "");
      break;
    case "result":
      handlers.onResult?.(event.result || event);
      break;
    case "stream_complete":
      handlers.onComplete?.();
      break;
    case "error":
      handlers.onError?.(event.message || "Unknown error");
      break;
  }
}

export function streamStartSession(learnerId: string, handlers: StreamHandlers, topic?: string) {
  const body: Record<string, string> = { learner_id: learnerId };
  if (topic) body.topic = topic;
  return streamRequest("/session/start/stream", body, handlers);
}

export function streamRespond(
  sessionId: string,
  data: { response_type: string; content: string; confidence?: number },
  handlers: StreamHandlers
) {
  return streamRequest(`/session/${sessionId}/respond/stream`, data, handlers);
}
