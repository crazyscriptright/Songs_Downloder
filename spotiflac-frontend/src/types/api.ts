/** Standardized backend response envelope ({success, message, data, meta?}). */
export interface ApiEnvelope<T = unknown> {
  success: boolean;
  message: string;
  data: T;
  meta?: Record<string, unknown>;
}

/** Error thrown by ApiService when a request fails (non-OK status or success:false). */
export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}
