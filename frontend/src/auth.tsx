import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, json, tokenStore } from "./api";
import type { User } from "./types";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (full_name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
}

const Ctx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!tokenStore.get()) { setUser(null); setLoading(false); return; }
    try { setUser(await api<User>("/v1/auth/me")); } catch { setUser(null); } finally { setLoading(false); }
  }, []);

  useEffect(() => {
    refresh();
    const onLogout = () => setUser(null);
    window.addEventListener("kudiready:logout", onLogout);
    return () => window.removeEventListener("kudiready:logout", onLogout);
  }, [refresh]);

  const login = async (email: string, password: string) => {
    const { access_token } = await api<{ access_token: string }>("/v1/auth/login", { method: "POST", body: json({ email, password }) }, false);
    tokenStore.set(access_token);
    await refresh();
  };

  const register = async (full_name: string, email: string, password: string) => {
    const { access_token } = await api<{ access_token: string }>("/v1/auth/register", { method: "POST", body: json({ full_name, email, password }) }, false);
    tokenStore.set(access_token);
    await refresh();
  };

  const logout = () => { tokenStore.set(null); setUser(null); };

  return <Ctx.Provider value={{ user, loading, login, register, logout, refresh }}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth outside AuthProvider");
  return v;
}
