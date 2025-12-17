// API configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 
                     (typeof window !== 'undefined' && window.API_CONFIG?.API_BASE_URL) ||
                     'http://localhost:5000';

export const getApiBaseUrl = () => API_BASE_URL;

// Sanitize title to remove dangerous characters
export const sanitizeTitle = (title) => {
  if (!title) return "untitled";
  
  return title
    .replace(/[<>:"|?*\\\/]/g, '') // Remove filesystem dangerous chars
    .replace(/[\x00-\x1F\x7F]/g, '') // Remove control characters
    .replace(/\.\./g, '.') // Replace .. with single dot
    .trim()
    .substring(0, 200) || "untitled"; // Limit length and provide fallback
};

// Convert YouTube Music URLs to regular YouTube URLs
export const convertYouTubeMusicUrl = (url) => {
  let convertedUrl = url.replace("music.youtube.com", "youtube.com");
  
  let videoId = null;
  const patterns = [
    /(?:v=|\/)([0-9A-Za-z_-]{11}).*/,
    /(?:embed\/)([0-9A-Za-z_-]{11})/,
    /(?:watch\?v=)([0-9A-Za-z_-]{11})/
  ];

  for (const pattern of patterns) {
    const match = convertedUrl.match(pattern);
    if (match) {
      videoId = match[1];
      break;
    }
  }

  return {
    convertedUrl,
    videoId,
    embedUrl: videoId ? `https://www.youtube.com/embed/${videoId}` : null
  };
};

// Extract title from URL
export const extractTitleFromUrl = (url) => {
  try {
    const urlObj = new URL(url);
    
    if (url.includes('youtube.com') || url.includes('youtu.be')) {
      const params = new URLSearchParams(urlObj.search);
      return params.get('v') || url.split('/').pop().split('?')[0] || 'YouTube Video';
    }
    
    if (url.includes('soundcloud.com')) {
      return urlObj.pathname.split('/').filter(Boolean).pop() || 'SoundCloud Track';
    }
    
    if (url.includes('jiosaavn.com')) {
      return urlObj.pathname.split('/').filter(Boolean).pop() || 'JioSaavn Song';
    }
    
    return 'Downloaded File';
  } catch {
    return 'Downloaded File';
  }
};

// Storage utilities
export const storage = {
  getDownloads: () => {
    try {
      return JSON.parse(localStorage.getItem('allDownloads') || '{}');
    } catch {
      return {};
    }
  },
  
  saveDownloads: (downloads) => {
    try {
      localStorage.setItem('allDownloads', JSON.stringify(downloads));
    } catch (error) {
      console.error('Failed to save downloads:', error);
    }
  },
  
  getTheme: () => {
    return localStorage.getItem('theme') || 'dark';
  },
  
  saveTheme: (theme) => {
    localStorage.setItem('theme', theme);
  }
};
