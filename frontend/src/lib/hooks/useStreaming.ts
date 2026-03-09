"use client";

import { useState, useCallback } from "react";
import { StreamHandlers, ActionResult } from "@/lib/sse";

export function useStreaming(onResult: (data: ActionResult) => void, onError: (msg: string) => void) {
  const [loading, setLoading] = useState(false);
  const [thinkingAgent, setThinkingAgent] = useState("");
  const [activeTool, setActiveTool] = useState("");
  const [streamingText, setStreamingText] = useState("");

  const isProcessing = loading || !!thinkingAgent;

  const resetStreaming = useCallback(() => {
    setLoading(false);
    setThinkingAgent("");
    setActiveTool("");
    setStreamingText("");
  }, []);

  const createHandlers = useCallback(
    (extraOnResult?: (data: ActionResult) => void, extraOnChatCreated?: (sessionId: string, title: string) => void): StreamHandlers => {
      let textBuffer = "";

      return {
        onAcknowledged: () => {
          onError("");
        },
        onChatCreated: (sessionId: string, title: string) => {
          extraOnChatCreated?.(sessionId, title);
        },
        onAgentThinking: (agent: string) => {
          setThinkingAgent(agent);
        },
        onThinkingComplete: () => {
          setThinkingAgent("");
        },
        onTextChunk: (chunk: string, final: boolean) => {
          textBuffer += chunk;
          setStreamingText(textBuffer);
          if (final) {
            // Don't clear immediately — let onResult handle adding the permanent message.
            // Just reset the buffer for potential next chunks.
            textBuffer = "";
          }
        },
        onToolStart: (toolName: string, agent: string) => {
          setActiveTool(toolName);
          setThinkingAgent(agent);
        },
        onToolComplete: () => {
          setActiveTool("");
        },
        onResult: (data: ActionResult) => {
          setStreamingText("");
          setThinkingAgent("");
          setActiveTool("");
          if (extraOnResult) {
            extraOnResult(data);
          } else {
            onResult(data);
          }
        },
        onError: (message: string) => {
          onError(message);
          setLoading(false);
          setThinkingAgent("");
          setActiveTool("");
          setStreamingText("");
        },
        onComplete: () => {
          textBuffer = "";
          setLoading(false);
          setThinkingAgent("");
          setActiveTool("");
          setStreamingText("");
        },
      };
    },
    [onResult, onError]
  );

  return {
    loading,
    setLoading,
    thinkingAgent,
    activeTool,
    streamingText,
    isProcessing,
    resetStreaming,
    createHandlers,
  };
}
