export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export type ApiError = { message: string; code?: string; fields?: Record<string, string[]> };

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = typeof window !== "undefined" ? window.localStorage.getItem("handework_access_token") : null;
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body != null && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const timeout = AbortSignal.timeout(15_000);
  const signal = init.signal ? AbortSignal.any([init.signal, timeout]) : timeout;
  try {
    const response = await fetch(`${API_URL}${path}`, { ...init, headers, signal });
    const body = await response.json().catch((error: unknown) => {
      signal.throwIfAborted();
      if (response.ok) throw error;
      return {};
    });
    if (!response.ok) throw Object.assign(new Error(body.message ?? "Request failed"), { details: body });
    return body as T;
  } catch (error) {
    if (signal.aborted && signal.reason === timeout.reason) {
      throw new Error("The request timed out. Please try again.");
    }
    throw error;
  }
}

export function saveSession(accessToken: string, refreshToken?: string) {
  window.localStorage.setItem("handework_access_token", accessToken);
  if (refreshToken) window.localStorage.setItem("handework_refresh_token", refreshToken);
}

export function clearSession() {
  window.localStorage.removeItem("handework_access_token");
  window.localStorage.removeItem("handework_refresh_token");
}
