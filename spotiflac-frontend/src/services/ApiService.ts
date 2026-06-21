import { getApiBaseUrl } from '@/config';
import type { ApiResponse } from '@/types';

function isJsonContentType(headers: Headers): boolean {
  const ct = headers.get('content-type') || '';
  return ct.includes('application/json');
}

/**
 * Low-level helpers for making API calls to the backend.
 *
 * `get<T>()` / `post<T>()` unwrap the standard envelope automatically
 * and return `response.data` (typed as `T`).  Use `getRaw` / `postRaw`
 * when you need the raw Response (e.g. for binary streams).
 */
export class ApiService {
  /** Make a GET request and return the unwrapped data payload. */
  static async get<T = any>(endpoint: string): Promise<T> {
    const url = `${getApiBaseUrl()}${endpoint}`;
    const response = await fetch(url, {
      headers: { 'Content-Type': 'application/json' },
    });
    return ApiService.unwrap<T>(response);
  }

  /** Make a POST request with a JSON body and return the unwrapped data payload. */
  static async post<T = any>(endpoint: string, body: unknown): Promise<T> {
    const url = `${getApiBaseUrl()}${endpoint}`;
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    return ApiService.unwrap<T>(response);
  }

  /**
   * Parse a Response through the standard envelope and return `response.data`.
   * Throws with the server's error message when `success` is false.
   */
  static async unwrap<T>(response: Response): Promise<T> {
    if (!isJsonContentType(response.headers)) {
      // Non-JSON response (binary stream, blob, etc.)
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      // Can't unwrap — return raw response (caller should handle)
      return response as unknown as T;
    }

    const body: ApiResponse<T> = await response.json();

    if (!body.success) {
      throw new Error(body.message || `Request failed (${response.status})`);
    }

    return body.data as T;
  }

  /** Make a POST request and return the raw Response. */
  static async postRaw(endpoint: string, body: unknown): Promise<Response> {
    const url = `${getApiBaseUrl()}${endpoint}`;
    return fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  }

  /** Make a raw GET request returning the Response object. */
  static async getRaw(endpoint: string): Promise<Response> {
    const url = `${getApiBaseUrl()}${endpoint}`;
    return fetch(url);
  }

  /** Fetch a file as a Blob via GET. */
  static async fetchBlob(url: string): Promise<Blob> {
    const response = await fetch(url);
    if (!response.ok) throw new Error('File download failed');
    return response.blob();
  }
}
