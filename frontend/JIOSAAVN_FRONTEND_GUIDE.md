# JioSaavn Suggestions - Frontend Integration Guide

## Quick Start

The JioSaavn suggestions endpoint now has automatic Selenium fallback when the API is blocked or returns empty results.

## API Endpoint

### GET `/jiosaavn_suggestions/<pid>`

Fetch song recommendations based on a JioSaavn song PID.

**URL Parameters:**
- `pid` (required) - JioSaavn song PID (e.g., 'IgwLcB06')
- `language` (optional) - Language preference (default: 'english')
- `selenium` (optional) - Force Selenium mode ('true' or 'false')

**Example Requests:**
```javascript
// 1. Normal mode (tries API first, falls back to Selenium if needed)
fetch('/jiosaavn_suggestions/IgwLcB06?language=english')

// 2. Force Selenium mode (bypasses API, uses real browser)
fetch('/jiosaavn_suggestions/IgwLcB06?selenium=true&language=hindi')

// 3. Different language
fetch('/jiosaavn_suggestions/IgwLcB06?language=tamil')
```

## Response Format

### Success Response
```json
{
  "success": true,
  "pid": "IgwLcB06",
  "language": "english",
  "count": 10,
  "method": "api",  // or "selenium"
  "suggestions": [
    {
      "id": "abc123",
      "title": "Song Title",
      "artist": "Artist Name",
      "subtitle": "Artist Name - Album Name",
      "thumbnail": "https://...",
      "url": "https://www.jiosaavn.com/song/...",
      "duration": "240",
      "language": "english",
      "type": "song",
      "year": "2024",
      "play_count": 123456
    }
    // ... more suggestions
  ]
}
```

### Error Response
```json
{
  "error": "Error message",
  "success": false
}
```

## Frontend Implementation Examples

### 1. Basic Fetch with Loading State
```javascript
async function loadJioSaavnSuggestions(pid, language = 'english') {
  try {
    // Show loading indicator
    showLoadingSpinner();
    
    const response = await fetch(
      `/jiosaavn_suggestions/${pid}?language=${language}`
    );
    
    if (!response.ok) {
      throw new Error('Failed to fetch suggestions');
    }
    
    const data = await response.json();
    
    // Check which method was used
    console.log(`Loaded ${data.count} suggestions via ${data.method}`);
    
    // Display suggestions
    displaySuggestions(data.suggestions);
    
    // Show badge if Selenium was used (slower but reliable)
    if (data.method === 'selenium') {
      showSeleniumBadge('Using real browser for reliability');
    }
    
  } catch (error) {
    console.error('Error loading suggestions:', error);
    showError('Failed to load suggestions');
  } finally {
    hideLoadingSpinner();
  }
}
```

### 2. With Retry Logic (Force Selenium on Failure)
```javascript
async function loadSuggestionsWithRetry(pid, language = 'english') {
  try {
    // First attempt: Normal mode (API first)
    let response = await fetch(
      `/jiosaavn_suggestions/${pid}?language=${language}`
    );
    
    let data = await response.json();
    
    // If API failed or returned no results, force Selenium
    if (!data.success || data.count === 0) {
      console.log('API failed, retrying with Selenium...');
      
      response = await fetch(
        `/jiosaavn_suggestions/${pid}?selenium=true&language=${language}`
      );
      
      data = await response.json();
    }
    
    return data;
    
  } catch (error) {
    console.error('All methods failed:', error);
    throw error;
  }
}
```

### 3. Display Suggestions in UI
```javascript
function displaySuggestions(suggestions) {
  const container = document.getElementById('suggestions-container');
  container.innerHTML = '';
  
  suggestions.forEach((song, index) => {
    const card = document.createElement('div');
    card.className = 'suggestion-card';
    card.innerHTML = `
      <img src="${song.thumbnail}" alt="${song.title}" />
      <div class="song-info">
        <h4>${song.title}</h4>
        <p>${song.artist}</p>
        ${song.year ? `<span class="year">${song.year}</span>` : ''}
      </div>
      <button onclick="downloadSong('${song.url}', '${song.title}')">
        Download
      </button>
    `;
    container.appendChild(card);
  });
}
```

### 4. Loading Indicator
```javascript
function showLoadingSpinner() {
  const loader = document.createElement('div');
  loader.id = 'suggestions-loader';
  loader.innerHTML = `
    <div class="spinner"></div>
    <p>Loading suggestions...</p>
    <small>This may take a moment if using real browser</small>
  `;
  document.getElementById('suggestions-container').appendChild(loader);
}

function hideLoadingSpinner() {
  const loader = document.getElementById('suggestions-loader');
  if (loader) loader.remove();
}
```

### 5. Method Badge (Show when Selenium is used)
```javascript
function showSeleniumBadge(message) {
  const badge = document.createElement('div');
  badge.className = 'method-badge selenium-badge';
  badge.innerHTML = `
    <svg>...</svg> 
    <span>${message}</span>
  `;
  document.querySelector('.suggestions-header').appendChild(badge);
}
```

## CSS Styling Examples

```css
/* Suggestion Cards */
.suggestion-card {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 15px;
  border-radius: 8px;
  background: #f8f9fa;
  margin-bottom: 10px;
  transition: all 0.3s ease;
}

.suggestion-card:hover {
  background: #e9ecef;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.suggestion-card img {
  width: 60px;
  height: 60px;
  border-radius: 4px;
  object-fit: cover;
}

.song-info {
  flex: 1;
}

.song-info h4 {
  margin: 0 0 5px 0;
  font-size: 1em;
  color: #333;
}

.song-info p {
  margin: 0;
  font-size: 0.9em;
  color: #666;
}

/* Loading Spinner */
.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #3498db;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 20px auto;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Method Badge */
.method-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 12px;
  border-radius: 20px;
  font-size: 0.85em;
  font-weight: 500;
  margin-left: 10px;
}

.selenium-badge {
  background: #ffc107;
  color: #333;
}

.api-badge {
  background: #28a745;
  color: white;
}
```

## User Experience Best Practices

### 1. Show Method Indicator
Let users know when Selenium is being used (it's slower but more reliable):
```javascript
if (data.method === 'selenium') {
  showNotification('Using enhanced mode for better reliability', 'info');
}
```

### 2. Add Timeout for Selenium
Selenium can take 5-10 seconds. Show appropriate loading messages:
```javascript
setTimeout(() => {
  if (isStillLoading) {
    updateLoadingMessage('Still loading... Using real browser for reliability');
  }
}, 3000);
```

### 3. Handle Empty Results
```javascript
if (data.count === 0) {
  showMessage('No suggestions available for this song', 'warning');
}
```

### 4. Cache Results
Avoid repeated calls for the same PID:
```javascript
const suggestionsCache = new Map();

async function getCachedSuggestions(pid, language) {
  const key = `${pid}_${language}`;
  
  if (suggestionsCache.has(key)) {
    return suggestionsCache.get(key);
  }
  
  const data = await loadJioSaavnSuggestions(pid, language);
  suggestionsCache.set(key, data);
  
  return data;
}
```

## Language Support

Supported languages:
- `english`
- `hindi`
- `telugu`
- `tamil`
- `punjabi`
- `bengali`
- `marathi`
- `gujarati`
- `kannada`
- `malayalam`

**Example: Language Selector**
```javascript
const languages = [
  'english', 'hindi', 'telugu', 'tamil', 
  'punjabi', 'bengali', 'marathi'
];

function createLanguageSelector(pid) {
  return `
    <select onchange="loadJioSaavnSuggestions('${pid}', this.value)">
      ${languages.map(lang => 
        `<option value="${lang}">${lang}</option>`
      ).join('')}
    </select>
  `;
}
```

## Troubleshooting

### Problem: Suggestions not loading
**Solution:**
```javascript
// Try forcing Selenium mode
const data = await fetch(
  `/jiosaavn_suggestions/${pid}?selenium=true`
).then(r => r.json());
```

### Problem: Slow loading
**Solution:**
```javascript
// Add timeout and show appropriate message
const controller = new AbortController();
const timeoutId = setTimeout(() => controller.abort(), 15000);

try {
  const response = await fetch(url, { signal: controller.signal });
  // ... handle response
} catch (error) {
  if (error.name === 'AbortError') {
    showError('Request timed out. Please try again.');
  }
} finally {
  clearTimeout(timeoutId);
}
```

### Problem: Invalid PID error
**Solution:**
```javascript
function extractPIDFromURL(url) {
  // Extract PID from JioSaavn URL
  const match = url.match(/\/song\/[^\/]+\/([^\/\?]+)/);
  return match ? match[1] : null;
}

const pid = extractPIDFromURL(jiosaavnUrl);
if (!pid) {
  showError('Invalid JioSaavn URL');
  return;
}
```

## Complete Example

Here's a complete working example:

```html
<!DOCTYPE html>
<html>
<head>
  <title>JioSaavn Suggestions</title>
  <style>
    /* Add CSS from above */
  </style>
</head>
<body>
  <div class="container">
    <h2>Similar Songs</h2>
    <div id="suggestions-container"></div>
  </div>

  <script>
    async function loadAndDisplaySuggestions(pid, language = 'english') {
      const container = document.getElementById('suggestions-container');
      
      // Show loading
      container.innerHTML = '<div class="spinner"></div>';
      
      try {
        const response = await fetch(
          `/jiosaavn_suggestions/${pid}?language=${language}`
        );
        
        if (!response.ok) throw new Error('Failed to fetch');
        
        const data = await response.json();
        
        if (data.count === 0) {
          container.innerHTML = '<p>No suggestions available</p>';
          return;
        }
        
        // Display suggestions
        container.innerHTML = data.suggestions.map(song => `
          <div class="suggestion-card">
            <img src="${song.thumbnail}" alt="${song.title}">
            <div class="song-info">
              <h4>${song.title}</h4>
              <p>${song.artist}</p>
            </div>
            <button onclick="download('${song.url}')">Download</button>
          </div>
        `).join('');
        
        // Show method badge
        if (data.method === 'selenium') {
          console.log('Used Selenium for reliability');
        }
        
      } catch (error) {
        container.innerHTML = `<p class="error">Error: ${error.message}</p>`;
      }
    }
    
    // Load on page load
    loadAndDisplaySuggestions('IgwLcB06', 'english');
  </script>
</body>
</html>
```

---

**Last Updated:** December 13, 2025  
**Compatibility:** Works with both `api.py` and `web_main.py`
