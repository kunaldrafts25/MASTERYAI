"use client";
import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AuthContext, AuthState, loadAuth, saveAuth, clearAuth } from "@/lib/auth";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [auth, setAuth] = useState<AuthState>({ token: null, userId: null, learnerId: null, name: null });

  useEffect(() => {
    setAuth(loadAuth());
  }, []);

  const login = useCallback((token: string, userId: string, learnerId: string, name?: string) => {
    saveAuth(token, userId, learnerId, name);
    setAuth({ token, userId, learnerId, name: name || null });
  }, []);

  const logout = useCallback(() => {
    clearAuth();
    setAuth({ token: null, userId: null, learnerId: null, name: null });
  }, []);

  return (
    <AuthContext.Provider value={{ auth, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function NavBar() {
  const router = useRouter();
  const [auth, setAuth] = useState<AuthState>({ token: null, userId: null, learnerId: null, name: null });

  useEffect(() => {
    setAuth(loadAuth());
    const handler = () => setAuth(loadAuth());
    window.addEventListener("storage", handler);
    return () => window.removeEventListener("storage", handler);
  }, []);

  function handleLogout() {
    clearAuth();
    setAuth({ token: null, userId: null, learnerId: null, name: null });
    router.push("/login");
  }

  const loggedIn = !!auth.token;

  return (
    <nav className="border-b border-white/10 px-6 py-3 flex items-center justify-between">
      <div className="flex items-center gap-8">
        <Link href={loggedIn ? "/session" : "/"} className="text-lg font-semibold tracking-tight">
          MasteryAI
        </Link>
        {loggedIn && (
          <div className="flex gap-6 text-sm text-zinc-400">
            <Link href="/session" className="hover:text-white transition-colors">Session</Link>
            <Link href="/knowledge-map" className="hover:text-white transition-colors">Knowledge Map</Link>
            <Link href="/career" className="hover:text-white transition-colors">Career</Link>
            <Link href="/calibration" className="hover:text-white transition-colors">Calibration</Link>
            <Link href="/agent-log" className="hover:text-white transition-colors">Agent Log</Link>
          </div>
        )}
      </div>
      <div className="flex items-center gap-4">
        {loggedIn ? (
          <button onClick={handleLogout} className="text-sm text-zinc-400 hover:text-white transition-colors">
            Sign Out
          </button>
        ) : (
          <div className="flex gap-4 text-sm">
            <Link href="/login" className="text-zinc-400 hover:text-white transition-colors">Sign In</Link>
            <Link href="/register" className="text-white bg-zinc-800 px-3 py-1 rounded hover:bg-zinc-700 transition-colors">Sign Up</Link>
          </div>
        )}
      </div>
    </nav>
  );
}
