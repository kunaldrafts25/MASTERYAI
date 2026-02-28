"use client";
import { createContext, useContext } from "react";

export interface AuthState {
  token: string | null;
  userId: string | null;
  learnerId: string | null;
  name: string | null;
}

export const AuthContext = createContext<{
  auth: AuthState;
  login: (token: string, userId: string, learnerId: string, name?: string) => void;
  logout: () => void;
}>({
  auth: { token: null, userId: null, learnerId: null, name: null },
  login: () => {},
  logout: () => {},
});

export function useAuth() {
  return useContext(AuthContext);
}

export function loadAuth(): AuthState {
  if (typeof window === "undefined") return { token: null, userId: null, learnerId: null, name: null };
  return {
    token: localStorage.getItem("token"),
    userId: localStorage.getItem("userId"),
    learnerId: localStorage.getItem("learnerId"),
    name: localStorage.getItem("userName"),
  };
}

export function saveAuth(token: string, userId: string, learnerId: string, name?: string) {
  localStorage.setItem("token", token);
  localStorage.setItem("userId", userId);
  localStorage.setItem("learnerId", learnerId);
  if (name) localStorage.setItem("userName", name);
}

export function clearAuth() {
  localStorage.removeItem("token");
  localStorage.removeItem("userId");
  localStorage.removeItem("learnerId");
  localStorage.removeItem("userName");
}
