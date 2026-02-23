/**
 * API Configuration
 * Reads VITE_API_URL from .env, falls back to auto-detecting by hostname.
 */

const PRODUCTION_URL = 'https://song-download-9889cf8e8f85.herokuapp.com';
const DEV_URL = 'http://localhost:5000';

/** Value from .env / .env.production (set VITE_API_URL=...) */
const ENV_URL: string | undefined = import.meta.env.VITE_API_URL;

function detectApiBaseUrl(): string {
  if (ENV_URL) return ENV_URL.replace(/\/$/, '');
  const hostname = window.location.hostname;
  return hostname === 'localhost' || hostname === '127.0.0.1'
    ? DEV_URL
    : PRODUCTION_URL;
}

/** Configured API base URL (no trailing slash) */
export const API_BASE_URL: string = detectApiBaseUrl();

/**
 * Returns the active API base URL, checking for a runtime window override first.
 * Strips any trailing slash.
 */
export function getApiBaseUrl(): string {
  const win = window as Window & { API?: { baseUrl?: string } };
  const url = (win.API?.baseUrl ?? API_BASE_URL).replace(/\/$/, '');
  return url || PRODUCTION_URL;
}

/** Maximum number of concurrent downloads */
export const MAX_CONCURRENT_DOWNLOADS = 3;

/** Polling interval (ms) for download status checks */
export const POLL_INTERVAL = 3000;

/** Maximum polling attempts before timeout */
export const MAX_POLL_ATTEMPTS = 60;

/** Debounce delay for search suggestions (ms) */
export const SUGGESTION_DEBOUNCE = 300;