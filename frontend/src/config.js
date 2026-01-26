// API Configuration
export const getApiBaseUrl = () => {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  if (typeof window !== "undefined" && window.API_BASE_URL) {
    return window.API_BASE_URL;
  }
  return "http://localhost:5000";
};

// Add named export for API_BASE_URL for compatibility
export const API_BASE_URL = getApiBaseUrl();

const config = {
  apiBaseUrl: API_BASE_URL,
};
export default config;
