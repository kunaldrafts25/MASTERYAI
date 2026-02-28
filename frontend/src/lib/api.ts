const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API}${path}`, { headers, ...options });

  if (res.status === 401) {
    if (typeof window !== "undefined") {
      localStorage.removeItem("token");
      localStorage.removeItem("userId");
      localStorage.removeItem("learnerId");
      window.location.href = "/login";
    }
    throw new Error("Session expired");
  }

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }

  return res.json();
}

// Auth

export function registerUser(data: { email: string; password: string; name: string; experience_level?: string }) {
  return request<{ token: string; user_id: string; learner_id: string; name: string }>("/auth/register", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function loginUser(data: { email: string; password: string }) {
  return request<{ token: string; user_id: string; learner_id: string; name: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// Learner

export function getLearnerState(learnerId: string) {
  return request(`/learner/${learnerId}/state`);
}

export function getCalibration(learnerId: string) {
  return request(`/learner/${learnerId}/calibration`);
}

// Session

export function getEvents(sessionId: string) {
  return request(`/session/${sessionId}/events`);
}

// Career

export function getReadiness(learnerId: string, roleId: string) {
  return request(`/career/readiness/${learnerId}/${roleId}`);
}

// Graph

export function getGraph(domains?: string[], learnerId?: string) {
  const params = new URLSearchParams();
  if (domains) {
    domains.forEach((d) => params.append("domain", d));
  }
  if (learnerId) {
    params.set("learner_id", learnerId);
  }
  const qs = params.toString();
  return request(`/graph${qs ? `?${qs}` : ""}`);
}

// Session History

export function getLearnerSessions(learnerId: string) {
  return request<
    {
      session_id: string;
      started_at: string;
      current_concept: string | null;
      concepts_covered: string[];
      concepts_mastered: string[];
      current_state: string;
    }[]
  >(`/learner/${learnerId}/sessions`);
}

