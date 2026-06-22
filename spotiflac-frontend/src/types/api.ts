/** Standard API response envelope from the backend. */
export interface ApiResponse<T = unknown> {
  success: boolean;
  message: string;
  data: T | null;
  meta?: Record<string, unknown>;
}
