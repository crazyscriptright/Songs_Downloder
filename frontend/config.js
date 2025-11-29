// API Configuration
// Automatically detects API URL from environment or uses default
const API_BASE_URL =
  window.location.hostname === "localhost"
    ? "http://localhost:5000" // Local development
    : window.ENV?.API_URL || "https://song-download-9889cf8e8f85.herokuapp.com"; // Production

// Helper function to make API calls
async function apiCall(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
  return response;
}

// Export for use in index.html
window.API = {
  baseUrl: API_BASE_URL,
  call: apiCall,
};

console.log("🌐 API Base URL:", API_BASE_URL);
