import type { Account, Decision, Event, Group, KnowledgeBase, Message, Prompt, Settings } from "./types";

const TOKEN_KEY = "tn_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}
export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const token = getToken();
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...options,
  });
  if (res.status === 401) {
    clearToken();
    if (!url.includes("/api/auth/login")) window.location.reload();
    throw new Error("انتهت الجلسة، سجّل الدخول مجدداً");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

const post = <T,>(url: string, body?: unknown) =>
  request<T>(url, { method: "POST", body: body ? JSON.stringify(body) : undefined });
const put = <T,>(url: string, body: unknown) =>
  request<T>(url, { method: "PUT", body: JSON.stringify(body) });
const del = (url: string) => request<void>(url, { method: "DELETE" });

export const api = {
  accounts: {
    list: () => request<Account[]>("/api/accounts"),
    create: (body: { label: string; phone: string }) => post<Account>("/api/accounts", body),
    remove: (id: number) => del(`/api/accounts/${id}`),
    sendCode: (id: number) => post<Account>(`/api/accounts/${id}/send-code`),
    verifyCode: (id: number, code: string) => post<Account>(`/api/accounts/${id}/verify-code`, { code }),
    verifyPassword: (id: number, password: string) =>
      post<Account>(`/api/accounts/${id}/verify-password`, { password }),
    connect: (id: number) => post<Account>(`/api/accounts/${id}/connect`),
    disconnect: (id: number) => post<Account>(`/api/accounts/${id}/disconnect`),
  },
  prompts: {
    list: () => request<Prompt[]>("/api/prompts"),
    create: (body: { name: string; system_text: string }) => post<Prompt>("/api/prompts", body),
    update: (id: number, body: Partial<Prompt>) => put<Prompt>(`/api/prompts/${id}`, body),
    remove: (id: number) => del(`/api/prompts/${id}`),
  },
  groups: {
    list: () => request<Group[]>("/api/groups"),
    create: (body: Record<string, unknown>) => post<Group>("/api/groups", body),
    update: (id: number, body: Partial<Group>) => put<Group>(`/api/groups/${id}`, body),
    remove: (id: number) => del(`/api/groups/${id}`),
    resolve: (id: number) => post<Group>(`/api/groups/${id}/resolve`),
  },
  monitor: {
    events: () => request<Event[]>("/api/events"),
    messages: (groupId?: number) =>
      request<Message[]>(`/api/messages${groupId ? `?group_id=${groupId}` : ""}`),
    decisions: () => request<Decision[]>("/api/decisions"),
    test: (body: { group_id: number; text: string; sender_name: string }) =>
      post<{ action: string; reply: string; reason: string }>("/api/test", body),
  },
  settings: {
    get: () => request<Settings>("/api/settings"),
    update: (body: Record<string, unknown>) => put<Settings>("/api/settings", body),
  },
  knowledge: {
    get: () => request<KnowledgeBase>("/api/knowledge"),
    update: (body: unknown) => put<KnowledgeBase>("/api/knowledge", body),
  },
  auth: {
    login: (username: string, password: string) =>
      post<{ access_token: string; username: string }>("/api/auth/login", { username, password }),
    me: () => request<{ username: string }>("/api/auth/me"),
  },
};
