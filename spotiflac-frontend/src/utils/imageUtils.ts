import { getApiBaseUrl } from "@/config";

/**
 * Get a responsive image URL proxied through the backend.
 * Size is determined by the requested pixel width.
 */
export function getResponsiveImageUrl(url: string, width: number): string {
  if (!url || !url.trim() || url === "null" || url === "undefined") return "";

  let size = "medium";
  if (width < 200) {
    size = "small";
  } else if (width >= 200 && width <= 400) {
    size = "medium";
  } else {
    size = "large";
  }

  return `${getApiBaseUrl()}/api/proxy-image?url=${encodeURIComponent(url)}&size=${size}`;
}

/** Base64 music placeholder SVG */
export const MUSIC_PLACEHOLDER_SVG =
  "data:image/svg+xml;base64," +
  btoa(
    '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120" viewBox="0 0 120 120"><rect width="120" height="120" fill="#2a2a2a"/><circle cx="60" cy="60" r="35" fill="none" stroke="#555" stroke-width="2"/><circle cx="60" cy="60" r="15" fill="none" stroke="#555" stroke-width="1.5"/><circle cx="60" cy="60" r="3" fill="#555"/><path d="M60 25 L75 35 L75 40 L60 30 Z" fill="#666"/><text x="60" y="100" text-anchor="middle" font-family="Arial, sans-serif" font-size="10" fill="#777">No Image</text></svg>',
  );

/** Transparent 1x1 pixel used as initial src for lazy images */
export const TRANSPARENT_PIXEL =
  "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' width='1' height='1'></svg>";

/**
 * Infer pixel width from CSS class names and inline style.
 */
export function inferWidth(className: string, style: string): number {
  const widthMatch = style.match(/width:\s*(\d+)px/);
  if (widthMatch) return parseInt(widthMatch[1], 10);
  if (className.includes("video-thumbnail")) return 320;
  if (className.includes("song-thumbnail")) return 280;
  if (style.includes("60px") || style.includes("width: 60")) return 60;
  if (style.includes("80px") || style.includes("width: 80")) return 80;
  if (style.includes("120px") || style.includes("width: 120")) return 120;
  if (style.includes("400px") || style.includes("width: 400")) return 400;
  return 150;
}

/**
 * Build an `<img>` HTML string with data-src for lazy loading.
 */
export function createLazyImageHTML(
  src: string,
  alt = "",
  className = "",
  style = "",
  fallbackSrc: string | null = null,
): string {
  const fallback = fallbackSrc || MUSIC_PLACEHOLDER_SVG;

  let actualSrc =
    src && src.trim() && src !== "" && src !== "null" && src !== "undefined"
      ? src
      : fallback;

  if (actualSrc.startsWith("http://") && !actualSrc.includes("localhost")) {
    actualSrc = actualSrc.replace("http://", "https://");
  }

  const width = inferWidth(className, style);

  if (actualSrc.startsWith("http") && !actualSrc.startsWith("data:")) {
    actualSrc = getResponsiveImageUrl(actualSrc, width);
  }

  return `<img
    data-src="${actualSrc}"
    data-fallback="${fallback}"
    alt="${alt}"
    class="${className}"
    style="${style}"
    src="${TRANSPARENT_PIXEL}"
    onerror="this.src='${fallback}'"
  >`;
}
