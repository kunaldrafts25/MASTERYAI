"use client";

import { useState, useCallback } from "react";
import { ActionResult } from "@/lib/sse";
import { ACTIONS, CONFIDENCE } from "@/lib/constants";

// ── Types ──────────────────────────────────────────────────────────────

export interface Message {
  id: string;
  role: "professor" | "learner" | "system";
  content: string;
  action?: string;
}

export interface ConceptInfo {
  id: string;
  name: string;
  domain?: string;
}

export interface CalibrationData {
  self_assessment: number;
  actual_score: number;
  gap: number;
}

// ── Hook ───────────────────────────────────────────────────────────────

export function useSessionState() {
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [confidence, setConfidence] = useState<number>(CONFIDENCE.DEFAULT);
  const [currentAction, setCurrentAction] = useState("");
  const [concept, setConcept] = useState<ConceptInfo | null>(null);
  const [calibration, setCalibration] = useState<CalibrationData | null>(null);
  const [error, setError] = useState("");

  const addMessage = useCallback(
    (role: Message["role"], content: string | unknown, action?: string) => {
      const text =
        typeof content === "string" ? content : JSON.stringify(content, null, 2);
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role, content: text, action },
      ]);
    },
    []
  );

  const resetSession = useCallback(() => {
    setActiveSessionId(null);
    setMessages([]);
    setCurrentAction("");
    setConcept(null);
    setCalibration(null);
    setError("");
    setInput("");
  }, []);

  const handleActionResponse = useCallback(
    (res: ActionResult) => {
      const action = res.action || "";
      setCurrentAction(action);

      if (res.concept) setConcept(res.concept as ConceptInfo);
      if (res.calibration) setCalibration(res.calibration);

      const lang =
        res.concept?.domain ||
        res.next_concept?.domain ||
        "";

      const extractText = (content: Record<string, unknown> | undefined) => {
        if (!content) return "";
        return (
          (content.explanation as string) ||
          (content.teaching_content as string) ||
          (content.message as string) ||
          JSON.stringify(content, null, 2)
        );
      };

      const codeBlock = (content: Record<string, unknown> | undefined) => {
        if (!content?.code_example) return "";
        return `\n\n\`\`\`${lang}\n${content.code_example}\n\`\`\``;
      };

      switch (action) {
        case ACTIONS.TEACH:
        case ACTIONS.DECAY_CHECK: {
          const content = res.content;
          addMessage("professor", extractText(content) + codeBlock(content), action);
          break;
        }
        case ACTIONS.PRACTICE: {
          const problems = res.content?.problems as
            | Record<string, unknown>[]
            | undefined;
          const msg =
            (res.content?.message as string) ||
            "Let's practice what we just covered.";
          if (Array.isArray(problems) && problems.length > 0) {
            const problemText = problems
              .map((p, i: number) => {
                const statement =
                  (p.problem_statement as string) ||
                  (p.problem as string) ||
                  (p.question as string) ||
                  (typeof p === "string" ? p : JSON.stringify(p));
                const hints = Array.isArray(p.hints) && p.hints.length > 0
                  ? `\n\n**Hints:**\n${(p.hints as string[]).map((h) => `- ${h}`).join("\n")}`
                  : p.hint
                  ? `\n\n*Hint: ${p.hint}*`
                  : "";
                return `### Problem ${i + 1}\n\n${statement}${hints}`;
              })
              .join("\n\n---\n\n");
            addMessage("professor", msg + "\n\n" + problemText, action);
          } else {
            addMessage("professor", msg, action);
          }
          break;
        }
        case ACTIONS.SELF_ASSESS: {
          const msg =
            (res.content?.message as string) ||
            "How confident do you feel about this concept?";
          addMessage("system", msg, action);
          break;
        }
        case ACTIONS.TRANSFER_TEST: {
          const test = res.content;
          const prompt =
            (test?.problem_statement as string) ||
            (test?.question as string) ||
            (test?.message as string) ||
            (typeof test === "string" ? test : JSON.stringify(test, null, 2));
          const context = test?.context_description
            ? `\n\n**Context:** ${test.context_description}`
            : "";
          const starter = test?.starter_code
            ? `\n\n\`\`\`${lang}\n${test.starter_code}\n\`\`\``
            : "";
          addMessage("professor", prompt + context + starter, action);
          break;
        }
        case ACTIONS.MASTERED_ADVANCE: {
          const score = res.evaluation?.total_score ?? "N/A";
          addMessage(
            "system",
            `Concept mastered! Score: ${typeof score === "number" ? (score * 100).toFixed(0) : score}%`,
            action
          );
          if (res.calibration) {
            addMessage(
              "system",
              `Calibration \u2014 Confidence: ${(res.calibration.self_assessment * 100).toFixed(0)}% | Actual: ${(res.calibration.actual_score * 100).toFixed(0)}% | Gap: ${(res.calibration.gap * 100).toFixed(0)}%`
            );
          }
          if (res.next_concept) {
            setConcept(res.next_concept as ConceptInfo);
            addMessage(
              "system",
              `Moving on to: **${res.next_concept.name || res.next_concept.id}**`
            );
          }
          if (res.next_content) {
            const nc = res.next_content;
            addMessage(
              "professor",
              extractText(nc) + codeBlock(nc),
              ACTIONS.TEACH
            );
            setCurrentAction(ACTIONS.TEACH);
          }
          break;
        }
        case ACTIONS.MASTERED_DONE: {
          addMessage("system", "You've mastered all available concepts!", action);
          if (res.calibration) {
            addMessage(
              "system",
              `Final calibration \u2014 Confidence: ${(res.calibration.self_assessment * 100).toFixed(0)}% | Actual: ${(res.calibration.actual_score * 100).toFixed(0)}%`
            );
          }
          break;
        }
        case ACTIONS.RETEST: {
          addMessage(
            "system",
            `Partial mastery (${((res.evaluation?.total_score as number || 0) * 100).toFixed(0)}%). Let's try a different approach.`,
            action
          );
          const test = res.content;
          if (test) {
            const prompt =
              (test.problem_statement as string) ||
              (test.question as string) ||
              JSON.stringify(test, null, 2);
            const starter = test.starter_code
              ? `\n\n\`\`\`${lang}\n${test.starter_code}\n\`\`\``
              : "";
            addMessage("professor", prompt + starter, ACTIONS.TRANSFER_TEST);
          }
          setCurrentAction(ACTIONS.TRANSFER_TEST);
          break;
        }
        case ACTIONS.RETEACH: {
          const evalScore = (
            ((res.evaluation?.total_score as number) || 0) * 100
          ).toFixed(0);
          addMessage(
            "system",
            `Score: ${evalScore}%. Let's revisit this concept with a different approach.`,
            action
          );
          if (res.misconceptions_detected?.length) {
            addMessage(
              "system",
              `Areas to improve: ${res.misconceptions_detected.join(", ")}`
            );
          }
          const content = res.content;
          addMessage("professor", extractText(content) + codeBlock(content), ACTIONS.TEACH);
          setCurrentAction(ACTIONS.TEACH);
          break;
        }
        case ACTIONS.COMPLETE: {
          addMessage(
            "system",
            (res.content?.message as string) || "Session complete!",
            action
          );
          break;
        }
        case ACTIONS.CHAT_RESPONSE:
        case "chat_response": {
          const msg =
            (res.content?.message as string) ||
            (res.content?.explanation as string) ||
            (typeof res.content === "string" ? res.content : "");
          if (msg) addMessage("professor", msg, action);
          break;
        }
        default: {
          if (res.content?.message) {
            addMessage("professor", res.content.message as string, action);
          }
        }
      }
    },
    [addMessage]
  );

  return {
    activeSessionId,
    setActiveSessionId,
    messages,
    input,
    setInput,
    confidence,
    setConfidence,
    currentAction,
    concept,
    calibration,
    error,
    setError,
    addMessage,
    resetSession,
    handleActionResponse,
  };
}
