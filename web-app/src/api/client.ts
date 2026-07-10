const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  status: number
  detail: unknown

  constructor(status: number, detail: unknown) {
    super(typeof detail === 'string' ? detail : JSON.stringify(detail))
    this.status = status
    this.detail = detail
  }
}

export function detailMessage(detail: unknown): string {
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object' && 'message' in detail) {
    return String((detail as { message: unknown }).message)
  }
  return 'Something went wrong.'
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${BASE_URL}${path}`, init)
  } catch {
    throw new ApiError(0, `Could not reach the API at ${BASE_URL} — is the backend running?`)
  }

  if (!response.ok) {
    let detail: unknown = response.statusText
    try {
      const body = await response.json()
      detail = body.detail ?? body
    } catch {
      // response body wasn't JSON; fall back to statusText
    }
    throw new ApiError(response.status, detail)
  }

  return response.json() as Promise<T>
}

export function postJson<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function postForm<T>(path: string, form: FormData): Promise<T> {
  return request<T>(path, { method: 'POST', body: form })
}
