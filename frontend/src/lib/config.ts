export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

/** Decode JWT payload without a library. Returns null if invalid. */
function decodeTokenPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const payload = atob(parts[1].replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(payload);
  } catch {
    return null;
  }
}

/** Returns true if the stored token is expired or will expire within 60s. */
export function isTokenExpired(): boolean {
  const token = getToken();
  if (!token) return true;
  const payload = decodeTokenPayload(token);
  if (!payload || typeof payload.exp !== "number") return false; // no exp claim — assume valid
  const nowSec = Math.floor(Date.now() / 1000);
  return payload.exp - nowSec < 60; // treat as expired if <60s remaining
}

export function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return headers;
}
