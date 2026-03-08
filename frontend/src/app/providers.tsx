"use client";
import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { AuthContext, AuthState, loadAuth, saveAuth, clearAuth, useAuth } from "@/lib/auth";
import { setOnUnauthorized } from "@/lib/api";
import { NAV_LINKS, ROUTES, APP_NAME } from "@/lib/constants";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [auth, setAuth] = useState<AuthState>({ token: null, userId: null, learnerId: null, name: null });
  const router = useRouter();

  useEffect(() => {
    setAuth(loadAuth());
  }, []);

  useEffect(() => {
    setOnUnauthorized(() => {
      setAuth({ token: null, userId: null, learnerId: null, name: null });
      router.push(ROUTES.LOGIN);
    });
  }, [router]);

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
  const { auth, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  function handleLogout() {
    logout();
    router.push(ROUTES.LOGIN);
  }

  const loggedIn = !!auth.token;

  return (
    <nav className="border-b border-white/10 px-4 md:px-6 py-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-8">
          <Link href={loggedIn ? ROUTES.SESSION : ROUTES.HOME} className="text-lg font-semibold tracking-tight">
            {APP_NAME}
          </Link>
          {loggedIn && (
            <div className="hidden md:flex gap-6 text-sm text-zinc-400">
              {NAV_LINKS.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`hover:text-white transition-colors ${
                    pathname === link.href ? "text-white" : ""
                  }`}
                >
                  {link.label}
                </Link>
              ))}
            </div>
          )}
        </div>
        <div className="flex items-center gap-4">
          {loggedIn ? (
            <>
              <Link href={ROUTES.SETTINGS} className="text-sm text-zinc-400 hover:text-white transition-colors">
                Settings
              </Link>
              <button onClick={handleLogout} className="text-sm text-zinc-400 hover:text-white transition-colors">
                Sign Out
              </button>
              <button
                onClick={() => setMobileOpen(!mobileOpen)}
                className="md:hidden p-1.5 text-zinc-400 hover:text-white"
                aria-label="Toggle menu"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  {mobileOpen ? (
                    <path d="M6 18L18 6M6 6l12 12" />
                  ) : (
                    <path d="M4 6h16M4 12h16M4 18h16" />
                  )}
                </svg>
              </button>
            </>
          ) : (
            <div className="flex gap-4 text-sm">
              <Link href={ROUTES.LOGIN} className="text-zinc-400 hover:text-white transition-colors">Sign In</Link>
              <Link href={ROUTES.REGISTER} className="text-white bg-zinc-800 px-3 py-1 rounded hover:bg-zinc-700 transition-colors">Sign Up</Link>
            </div>
          )}
        </div>
      </div>

      {loggedIn && mobileOpen && (
        <div className="md:hidden pt-3 pb-1 flex flex-col gap-2 text-sm text-zinc-400 border-t border-white/5 mt-3">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              onClick={() => setMobileOpen(false)}
              className={`py-1.5 hover:text-white transition-colors ${
                pathname === link.href ? "text-white" : ""
              }`}
            >
              {link.label}
            </Link>
          ))}
        </div>
      )}
    </nav>
  );
}
