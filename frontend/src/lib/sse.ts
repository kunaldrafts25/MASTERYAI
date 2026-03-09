// SSE streaming client - uses fetch+ReadableStream for POST-based SSE

import { API_BASE, authHeaders } from "./config";

export interface StreamHandlers {
  onAcknowledged?: () => void;
  onChatCreated?: (sessionId: string, title: string) => void;
  onAgentThinking?: (agent: string, message: string) => void;
  onThinkingComplete?: () => void;
  onTextChunk?: (chunk: string, final: boolean) => void;
  onToolStart?: (toolName: string, agent: string) => void;
  onToolComplete?: (toolName: string, agent: string) => void;
  onPhaseChange?: (phase: string, concept: string) => void;
  onResult?: (data: ActionResult) => void;
  onError?: (message: string) => void;
  onComplete?: () => void;
}

/** Discriminated union for SSE events from the backend */
export type StreamEvent =
  | { type: "acknowledged" }
  | { type: "chat_created"; session_id: string; title: string }
  | { type: "agent_thinking"; agent: string; message: string }
  | { type: "thinking_complete" }
  | { type: "text_chunk"; chunk: string; final: boolean }
  | { type: "tool_start"; tool_name: string; agent: string }
  | { type: "tool_complete"; tool_name: string; agent: string }
  | { type: "phase_change"; phase: string; concept: string }
  | { type: "result"; result: ActionResult }
  | { type: "stream_complete" }
  | { type: "error"; message: string };

/** Shape of the result payload from the orchestrator */
export interface ActionResult {
  action: string;
  session_id?: string;
  concept?: { id: string; name: string; domain?: string };
  next_concept?: { id: string; name: string; domain?: string };
  content?: Record<string, unknown>;
  next_content?: Record<string, unknown>;
  evaluation?: { total_score: number; [key: string]: unknown };
  calibration?: {
    self_assessment: number;
    actual_score: number;
    gap: number;
  };
  misconceptions_detected?: string[];
  [key: string]: unknown;
}

/** Active stream handle returned by streaming functions */
export interface StreamHandle {
  abort: () => void;
}

async function streamRequest(
  path: string,
  body: object,
  handlers: StreamHandlers,
  signal?: AbortSignal
): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify(body),
      signal,
    });
  } catch (err) {
    if (signal?.aborted) return;
    handlers.onError?.(err instanceof Error ? err.message : "Network error");
    return;
  }

  if (!response.ok) {
    let text: string;
    try {
      text = await response.text();
    } catch {
      text = "";
    }
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

      for (const block of lines) {
        if (!block.trim()) continue;

        // Each SSE block can have multiple lines: "id: 1\ndata: {...}"
        // Find the "data:" line within the block
        const subLines = block.split("\n");
        for (const sub of subLines) {
          const trimmed = sub.trim();
          if (!trimmed || trimmed.startsWith(":")) continue; // keepalive or empty

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
    }
  } catch (err) {
    if (signal?.aborted) return;
    handlers.onError?.(err instanceof Error ? err.message : "Stream interrupted");
  } finally {
    try {
      reader.releaseLock();
    } catch {
      // reader may already be released
    }
  }
}

function dispatchEvent(event: StreamEvent, handlers: StreamHandlers) {
  switch (event.type) {
    case "acknowledged":
      handlers.onAcknowledged?.();
      break;
    case "chat_created":
      handlers.onChatCreated?.(event.session_id || "", event.title || "");
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
      handlers.onResult?.(event.result || (event as unknown as ActionResult));
      break;
    case "stream_complete":
      handlers.onComplete?.();
      break;
    case "error":
      handlers.onError?.(event.message || "Unknown error");
      break;
  }
}

export function streamStartSession(
  learnerId: string,
  handlers: StreamHandlers,
  topic?: string
): StreamHandle {
  const controller = new AbortController();
  const body: Record<string, string> = { learner_id: learnerId };
  if (topic) body.topic = topic;
  streamRequest("/session/start/stream", body, handlers, controller.signal);
  return { abort: () => controller.abort() };
}

export function streamRespond(
  sessionId: string,
  data: { response_type: string; content: string; confidence?: number },
  handlers: StreamHandlers
): StreamHandle {
  const controller = new AbortController();
  streamRequest(`/session/${sessionId}/respond/stream`, data, handlers, controller.signal);
  return { abort: () => controller.abort() };
}
