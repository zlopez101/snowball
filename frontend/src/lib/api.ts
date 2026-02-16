export class HttpError extends Error {
  status: number
  detail: string

  constructor(status: number, detail: string) {
    super(detail)
    this.status = status
    this.detail = detail
  }
}

function getAuthHeaders() {
  const token = localStorage.getItem("access_token")
  if (!token) return {}
  return { Authorization: `Bearer ${token}` }
}

function buildUrl(path: string) {
  const base = import.meta.env.VITE_API_URL || ""
  return `${base}${path}`
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set("Content-Type", "application/json")
  const authHeaders = getAuthHeaders()
  if (authHeaders.Authorization) {
    headers.set("Authorization", authHeaders.Authorization)
  }

  const response = await fetch(buildUrl(path), {
    ...init,
    headers,
  })

  if (!response.ok) {
    let detail = "Request failed"
    try {
      const errorJson = (await response.json()) as { detail?: string }
      if (typeof errorJson.detail === "string") {
        detail = errorJson.detail
      }
    } catch {
      // no-op
    }
    throw new HttpError(response.status, detail)
  }

  if (response.status === 204) {
    return null as T
  }

  return (await response.json()) as T
}
