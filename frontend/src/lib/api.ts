import { API_BASE, authHeaders } from "./config";
import { clearAuth } from "./auth";

let onUnauthorized: (() => void) | null = null;

/** Register a callback for 401 responses (called by AuthProvider) */
export function setOnUnauthorized(cb: () => void) {
  onUnauthorized = cb;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: authHeaders(),
    ...options,
  });

  if (res.status === 401) {
    clearAuth();
    onUnauthorized?.();
    throw new Error("Session expired");
  }

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }

  return res.json();
}

// Auth

export interface AuthResponse {
  token: string;
  user_id: string;
  learner_id: string;
  name: string;
}

export function registerUser(data: {
  email: string;
  password: string;
  name: string;
  experience_level?: string;
}) {
  return request<AuthResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function loginUser(data: { email: string; password: string }) {
  return request<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// Learner

export interface LearnerSession {
  session_id: string;
  started_at: string;
  current_concept: string | null;
  concepts_covered: string[];
  concepts_mastered: string[];
  current_state: string;
}

export function getLearnerState(learnerId: string) {
  return request<{ career_targets: string[]; [key: string]: unknown }>(
    `/learner/${learnerId}/state`
  );
}

export function getCalibration(learnerId: string) {
  return request<{
    overall_calibration: number;
    trend: string;
    per_concept: {
      concept: string;
      confidence: number;
      mastery: number;
      gap: number;
    }[];
  }>(`/learner/${learnerId}/calibration`);
}

// Session

export function getEvents(sessionId: string) {
  return request<unknown[]>(`/session/${sessionId}/events`);
}

// Career

export function getReadiness(learnerId: string, roleId: string) {
  return request<{
    readiness: {
      role_id: string;
      role_title: string;
      overall_score: number;
      skill_breakdown: {
        skill_name: string;
        score: number;
        concepts_mastered: number;
        total_concepts: number;
      }[];
      gaps: {
        skill_name: string;
        current_mastery: number;
        required_mastery: number;
        missing_concepts: string[];
        estimated_hours: number;
      }[];
      estimated_hours_to_ready: number;
      recommended_next: string | null;
    };
    learning_path: unknown[];
    total_hours: number;
  }>(`/career/readiness/${learnerId}/${roleId}`);
}

// Graph

export interface GraphNode {
  id: string;
  name: string;
  domain: string;
  difficulty_tier: number;
  status: string;
  mastery_score: number;
}

export interface GraphEdge {
  source: string | GraphNode;
  target: string | GraphNode;
  type: string;
  strength?: number;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export function getGraph(domains?: string[], learnerId?: string) {
  const params = new URLSearchParams();
  if (domains) {
    domains.forEach((d) => params.append("domain", d));
  }
  if (learnerId) {
    params.set("learner_id", learnerId);
  }
  const qs = params.toString();
  return request<GraphData>(`/graph${qs ? `?${qs}` : ""}`);
}

// Profile

export function updateProfile(learnerId: string, data: { name?: string; experience_level?: string }) {
  return request<{ name: string; experience_level: string }>(`/learner/${learnerId}/profile`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

// Session History

export function getLearnerSessions(learnerId: string) {
  return request<LearnerSession[]>(`/learner/${learnerId}/sessions`);
}
