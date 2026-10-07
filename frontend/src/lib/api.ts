const DEFAULT_API_URL = "http://localhost:8000/api/v1";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_API_URL).replace(/\/$/, "");

/** A non-2xx response. `code` is the backend's machine-readable error code when present. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
    readonly code?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export type Query = Record<string, string | number | boolean | readonly string[] | undefined>;

function buildUrl(path: string, query?: Query): string {
  const url = new URL(`${API_URL}${path}`);
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value === undefined) continue;
    // Repeatable params (status=A&status=B) are how the backend expects lists.
    for (const item of Array.isArray(value) ? value : [value]) {
      url.searchParams.append(key, String(item));
    }
  }
  return url.toString();
}

interface ErrorBody {
  // The backend's envelope: { error: { code, message, details, request_id } }.
  error?: { code?: string; message?: string };
  // FastAPI's own default shape, kept as a fallback.
  detail?: unknown;
}

async function errorFrom(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as ErrorBody;
    const message =
      body.error?.message ?? (typeof body.detail === "string" ? body.detail : response.statusText);
    return new ApiError(response.status, message, body.error?.code);
  } catch {
    return new ApiError(response.status, response.statusText || "Request failed");
  }
}

export async function apiGet<T>(path: string, query?: Query, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await fetch(buildUrl(path, query), {
      headers: { Accept: "application/json" },
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError(0, "Cannot reach the RouteFlow API. Is the backend running?");
  }
  if (!response.ok) throw await errorFrom(response);
  return (await response.json()) as T;
}
