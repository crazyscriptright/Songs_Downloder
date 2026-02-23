import { getApiBaseUrl } from '@/config';

/**
 * Low-level helpers for making API calls to the backend.
 */
export class ApiService {
  /** Make a GET request and return parsed JSON. */
  static async get<T = any>(endpoint: string): Promise<T> {
    const url = `${getApiBaseUrl()}${endpoint}`;
    const response = await fetch(url, {
      headers: { 'Content-Type': 'application/json' },
    });
    return response.json();
  }

  /** Make a POST request with a JSON body and return parsed JSON. */
  static async post<T = any>(endpoint: string, body: unknown): Promise<T> {
    const url = `${getApiBaseUrl()}${endpoint}`;
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    return response.json();
  }

  /**
   * Make a POST request and return the raw Response (useful when the caller
   * needs to inspect status codes before parsing).
   */
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