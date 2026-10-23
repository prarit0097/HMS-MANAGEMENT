export class ApiError extends Error {
  constructor(message: string, public status: number, public fields: Record<string, string[]> = {}) { super(message); }
}
export async function api<T = unknown>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set('Accept', 'application/json');
  if (options.body) headers.set('Content-Type', 'application/json');
  if (options.method && !['GET', 'HEAD', 'OPTIONS'].includes(options.method.toUpperCase())) {
    const csrf = document.cookie.split('; ').find(value => value.startsWith('csrftoken='))?.slice('csrftoken='.length);
    if (csrf) headers.set('X-CSRFToken', decodeURIComponent(csrf));
  }
  let response: Response;
  try { response = await fetch(`/api/v1/${path}`, {...options, headers, credentials:'same-origin'}); }
  catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new ApiError('Cannot connect to the hospital server. Check your connection, then try again.', 0);
  }
  if (response.status === 204) return undefined as T;
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(body?.message || (response.status === 403 ? 'You do not have permission for this action.' : 'The request could not be completed. Please try again.'), response.status, body?.field_errors || {});
  if (body === null) throw new ApiError('The server returned an unexpected response. Please try again.', response.status);
  return body as T;
}
