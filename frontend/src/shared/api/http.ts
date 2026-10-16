const API_PREFIX = "/api";

export interface ApiErrorBody {
  code?: string;
  detail?: string;
  params?: Record<string, unknown>;
  [field: string]: unknown;
}

export class ApiError extends Error {
  readonly status: number;
  readonly body: ApiErrorBody;

  constructor(status: number, body: ApiErrorBody) {
    super(body.detail ?? `HTTP ${status}`);
    this.status = status;
    this.body = body;
  }

  get code(): string | undefined {
    return this.body.code;
  }
}

interface HttpHooks {
  readToken: () => string | null;
  onUnauthorized: () => void;
}

let hooks: HttpHooks = { readToken: () => null, onUnauthorized: () => undefined };

export function configureHttp(next: HttpHooks): void {
  hooks = next;
}

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  json?: unknown;
  formData?: FormData;
  query?: Record<string, string | number | boolean | undefined | null>;
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await fetch(buildUrl(path, options.query), {
    method: options.method ?? "GET",
    headers: buildHeaders(options),
    body: options.formData ?? (options.json === undefined ? undefined : JSON.stringify(options.json)),
  });
  if (response.status === 401 && hooks.readToken()) {
    hooks.onUnauthorized();
  }
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorBody(response));
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export async function downloadFile(path: string, fallbackName: string): Promise<void> {
  const response = await fetch(buildUrl(path), { headers: buildHeaders({}) });
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorBody(response));
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = readFilename(response) ?? fallbackName;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function openFileInNewTab(path: string): Promise<void> {
  const target = window.open("", "_blank");
  const response = await fetch(buildUrl(path), { headers: buildHeaders({}) });
  if (!response.ok) {
    target?.close();
    throw new ApiError(response.status, await readErrorBody(response));
  }
  const url = URL.createObjectURL(await response.blob());
  if (target) {
    target.location.href = url;
  }
}

function buildUrl(path: string, query?: RequestOptions["query"]): string {
  const url = new URL(`${API_PREFIX}${path}`, window.location.origin);
  Object.entries(query ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  });
  return url.pathname + url.search;
}

function buildHeaders(options: RequestOptions): HeadersInit {
  const headers: Record<string, string> = { Accept: "application/json" };
  const token = hooks.readToken();
  if (token) {
    headers.Authorization = `Token ${token}`;
  }
  if (options.json !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  return headers;
}

async function readErrorBody(response: Response): Promise<ApiErrorBody> {
  try {
    return (await response.json()) as ApiErrorBody;
  } catch {
    return {};
  }
}

function readFilename(response: Response): string | null {
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(disposition);
  return match ? decodeURIComponent(match[1]) : null;
}
