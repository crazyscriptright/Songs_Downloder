/** Regex pattern matching supported music platform URLs */
const MUSIC_URL_PATTERN =
  /youtube\.com\/watch|youtu\.be\/|music\.youtube\.com|jiosaavn\.com\/|saavn\.com\/|soundcloud\.com\/|spotify\.com\/|gaana\.com\/|wynk\.in\//i;

/** Regex pattern matching any HTTP(S) URL */
const ANY_URL_PATTERN = /https?:\/\/|www\./i;

/** Check if a string is a supported music platform URL */
export function isMusicUrl(query: string): boolean {
  return MUSIC_URL_PATTERN.test(query);
}

/** Check if a string looks like any URL */
export function isAnyUrl(query: string): boolean {
  return ANY_URL_PATTERN.test(query);
}

/** Validate that a string is a well-formed URL */
export function isValidUrl(query: string): boolean {
  try {
    new URL(query);
    return true;
  } catch {
    return false;
  }
}

export interface YouTubeUrlData {
  convertedUrl: string;
  videoId: string | null;
  embedUrl: string | null;
}

/**
 * Convert YouTube Music URLs to regular YouTube URLs and extract video ID.
 */
export function convertYouTubeMusicUrl(url: string): YouTubeUrlData {
  let convertedUrl = url.replace('music.youtube.com', 'youtube.com');

  let videoId: string | null = null;
  const patterns = [
    /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/,
    /youtube\.com\/v\/([a-zA-Z0-9_-]{11})/,
    /youtube\.com\/.*[?&]v=([a-zA-Z0-9_-]{11})/,
  ];

  for (const pattern of patterns) {
    const match = convertedUrl.match(pattern);
    if (match) {
      videoId = match[1];
      break;
    }
  }

  return {
    convertedUrl: videoId ? `https://youtube.com/watch?v=${videoId}` : convertedUrl,
    videoId,
    embedUrl: videoId ? `https://youtube.com/embed/${videoId}` : null,
  };
}