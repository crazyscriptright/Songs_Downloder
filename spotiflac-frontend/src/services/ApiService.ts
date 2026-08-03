import { getApiBaseUrl } from "@/config";
import { ApiEnvelope, ApiError } from "@/types/api";

/**
 * Reusable API client for the backend's standardized
 * `{success, message, data, meta?}` response envelope.
 *
 * - `get` / `post` return the payload (`env.data`) and throw `ApiError` on failure.
 * - `getEnvelope` / `postEnvelope` return the full envelope (callers that need `message`).
 * - `postRaw` / `getRaw` / `fetchBlob` return raw responses/blobs for binary endpoints.
 */
export class ApiService {
  private static async request<T>(
    endpoint: string,
    init?: RequestInit,
  ): Promise<ApiEnvelope<T>> {
    const url = `${getApiBaseUrl()}${endpoint}`;
    const response = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
    const envelope: ApiEnvelope<T> = await response.json();
    if (!response.ok || envelope.success === false) {
      throw new ApiError(envelope.message || `HTTP ${response.status}`, response.status);
    }
    return envelope;
  }

  /** GET and return the payload (`env.data`). Throws ApiError on failure. */
  static async get<T>(endpoint: string): Promise<T> {
    return (await this.request<T>(endpoint)).data;
  }

  /** POST a JSON body and return the payload (`env.data`). Throws ApiError on failure. */
  static async post<T>(endpoint: string, body: unknown): Promise<T> {
    return (await this.request<T>(endpoint, { method: "POST", body: JSON.stringify(body) })).data;
  }

  /** GET and return the full envelope (payload + message + meta). Throws ApiError on failure. */
  static async getEnvelope<T>(endpoint: string): Promise<ApiEnvelope<T>> {
    return this.request<T>(endpoint);
  }

  /** POST a JSON body and return the full envelope. Throws ApiError on failure. */
  static async postEnvelope<T>(endpoint: string, body: unknown): Promise<ApiEnvelope<T>> {
    return this.request<T>(endpoint, { method: "POST", body: JSON.stringify(body) });
  }

  /**
   * Make a POST request and return the raw Response (useful when the caller
   * needs to inspect status codes before parsing).
   */
  static async postRaw(endpoint: string, body: unknown): Promise<Response> {
    const url = `${getApiBaseUrl()}${endpoint}`;
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
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
    if (!response.ok) throw new Error("File download failed");
    return response.blob();
  }
}
