/**
 * Thin wrapper around fetch that injects the optional X-API-Key header.
 *
 * Set VITE_API_KEY in your .env (or frontend/.env) to match the backend's
 * BACKEND_API_KEY. Leave it empty (the default) when auth is disabled.
 */
const API_KEY = import.meta.env.VITE_API_KEY ?? "";

function buildHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const headers: Record<string, string> = { ...extra };
  if (API_KEY) headers["X-API-Key"] = API_KEY;
  return headers;
}

export async function apiFetch(
  input: string,
  init: RequestInit = {}
): Promise<Response> {
  const contentType: Record<string, string> =
    init.body && typeof init.body === "string" ? { "Content-Type": "application/json" } : {};

  return fetch(input, {
    ...init,
    headers: buildHeaders({ ...contentType, ...(init.headers as Record<string, string>) }),
  });
}