export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export type ApiError = { message: string; code?: string; fields?: Record<string, string[]> };

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = accessToken();
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body != null && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const timeout = AbortSignal.timeout(15_000);
  const signal = init.signal ? AbortSignal.any([init.signal, timeout]) : timeout;
  try {
    const send = () => fetch(`${API_URL}${path}`, { ...init, headers, signal });
    let response = await send();
    if (response.status === 401 && token && !path.startsWith("/v1/auth/login") && !path.startsWith("/v1/auth/register")) {
      const renewed = await renewSession();
      if (renewed) {
        headers.set("Authorization", `Bearer ${renewed}`);
        response = await send();
      }
    }
    const body = await response.json().catch((error: unknown) => {
      signal.throwIfAborted();
      if (response.ok) throw error;
      return {};
    });
    if (!response.ok) throw Object.assign(new Error(body.message ?? "Request failed"), { details: body, status: response.status });
    return body as T;
  } catch (error) {
    if (signal.aborted && signal.reason === timeout.reason) {
      throw new Error("The request timed out. Please try again.");
    }
    throw error;
  }
}

const accessKey = "handework_access_token";
const refreshKey = "handework_refresh_token";
const activityKey = "handework_last_active";
const idleLimit = 24 * 60 * 60 * 1000;

export function accessToken() {
  if (typeof window === "undefined") return null;
  const lastActive = Number(localStorage.getItem(activityKey));
  if (lastActive && Date.now() - lastActive >= idleLimit) return null;
  return localStorage.getItem(accessKey);
}

export function dashboardPath(role: string) {
  if (role === "artisan") return "/artisan/dashboard";
  if (role === "admin") return "/admin";
  return "/dashboard";
}

export function saveSession(access: string, refresh?: string) {
  localStorage.setItem(accessKey, access);
  if (refresh) localStorage.setItem(refreshKey, refresh);
  else localStorage.removeItem(refreshKey);
  localStorage.setItem(activityKey, String(Date.now()));
  window.dispatchEvent(new Event("handework-session"));
}

export function clearSession() {
  for (const key of [accessKey, refreshKey, activityKey]) localStorage.removeItem(key);
  window.dispatchEvent(new Event("handework-session"));
}

export async function signOut() {
  const token = localStorage.getItem(refreshKey) || accessToken();
  clearSession();
  if (token) await fetch(API_URL + "/v1/auth/logout", {
    method: "POST", headers: { Authorization: `Bearer ${token}` }, keepalive: true,
    signal: AbortSignal.timeout(5000),
  }).catch(() => undefined);
}

let pending: Promise<string | null> | undefined;
async function renew() {
  const refresh = localStorage.getItem(refreshKey);
  if (!refresh || !accessToken()) return null;
  const response = await fetch(API_URL + "/v1/auth/refresh", {
    method: "POST", headers: { Authorization: `Bearer ${refresh}`, "Content-Type": "application/json" }, body: JSON.stringify({client: "web"}), signal: AbortSignal.timeout(15000),
  });
  if (localStorage.getItem(refreshKey) !== refresh) return accessToken();
  if (response.status === 401 || response.status === 422) { clearSession(); return null; }
  if (!response.ok) throw new Error("Could not reconnect to your account. Please try again.");
  const body = await response.json();
  if (localStorage.getItem(refreshKey) !== refresh) return accessToken();
  localStorage.setItem(accessKey, body.access_token);
  if (body.refresh_token) localStorage.setItem(refreshKey, body.refresh_token);
  return body.access_token as string;
}

export function renewSession() {
  return pending ??= renew().finally(() => { pending = undefined; });
}

export function recordActivity() {
  if (!accessToken()) {
    if (localStorage.getItem(accessKey)) clearSession();
    return;
  }
  localStorage.setItem(activityKey, String(Date.now()));
}
