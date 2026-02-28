/**
 * PreviewService
 * ==============
 * Singleton that manages a single active low-quality audio preview.
 *
 * How it works:
 *   1. Calls GET /preview?url=<encoded> on the backend.
 *   2. The backend resolves a stream URL (SoundCloud native / JioSaavn native
 *      / yt-dlp fallback) and proxies the audio bytes back.
 *   3. An <audio> element is injected inline, directly below the song card's
 *      action buttons, so only one preview is active at a time.
 *
 * Usage (from SongCard.ts):
 *   import { PreviewService } from "@/services/PreviewService";
 *   PreviewService.play(song.url, song.title, cardElement, previewButton);
 */

import { getApiBaseUrl } from "@/config";
import { ToastNotification } from "@/components/ToastNotification";

const toast = new ToastNotification();

interface ActivePreview {
  url: string;
  /** Set for SoundCloud / JioSaavn audio previews. */
  audioEl: HTMLAudioElement | null;
  /** Set for YouTube Music iframe previews. */
  iframeEl: HTMLIFrameElement | null;
  wrapperEl: HTMLElement;
  btnEl: HTMLButtonElement;
}

// SVG icons reused for button states
const ICON_PLAY =
  '<svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16"><path d="M8 5v14l11-7z"/></svg>';
const ICON_PAUSE =
  '<svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>';
const ICON_LOADING =
  '<svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16" class="preview-spin"><path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8z" opacity=".3"/><path d="M12 2v4a8 8 0 0 1 8 8h4A12 12 0 0 0 12 2z"/></svg>';
const ICON_STOP =
  '<svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16"><path d="M6 6h12v12H6z"/></svg>';

/** Extract an 11-char YouTube video ID from any YouTube / YT Music URL. */
function _extractYouTubeVideoId(url: string): string | null {
  const patterns = [
    /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/,
    /youtube\.com\/.*[?&]v=([a-zA-Z0-9_-]{11})/,
  ];
  const normalized = url.replace("music.youtube.com", "youtube.com");
  for (const re of patterns) {
    const m = normalized.match(re);
    if (m) return m[1];
  }
  return null;
}

let _active: ActivePreview | null = null;

function _stopActive(): void {
  if (!_active) return;
  if (_active.audioEl) {
    _active.audioEl.pause();
    _active.audioEl.src = "";
  }
  _active.wrapperEl.remove();
  _setButtonIdle(_active.btnEl);
  _active = null;
}

function _setButtonIdle(btn: HTMLButtonElement): void {
  btn.innerHTML = ICON_PLAY;
  btn.title = "Preview";
  btn.disabled = false;
  btn.classList.remove("preview-loading", "preview-playing");
}

function _setButtonLoading(btn: HTMLButtonElement): void {
  btn.innerHTML = ICON_LOADING;
  btn.title = "Loading preview…";
  btn.disabled = true;
  btn.classList.add("preview-loading");
  btn.classList.remove("preview-playing");
}

function _setButtonPlaying(btn: HTMLButtonElement): void {
  btn.innerHTML = ICON_PAUSE;
  btn.title = "Pause preview";
  btn.disabled = false;
  btn.classList.remove("preview-loading");
  btn.classList.add("preview-playing");
}

/**
 * Play (or toggle) a low-quality preview for a song.
 *
 * @param songUrl    The song page URL (SoundCloud/JioSaavn permalink).
 * @param songTitle  Song title for accessibility/error messages.
 * @param cardEl     The .song-card element – audio player injected inside it.
 * @param btnEl      The preview button element (show spinner / play / pause).
 */
export function play(
  songUrl: string,
  songTitle: string,
  cardEl: HTMLElement,
  btnEl: HTMLButtonElement,
): void {
  // Toggle: same song already loaded → play / pause without re-fetching
  if (_active && _active.url === songUrl) {
    if (_active.audioEl) {
      if (_active.audioEl.paused) {
        _active.audioEl.play().catch(() => {});
        _setButtonPlaying(btnEl);
      } else {
        _active.audioEl.pause();
        _setButtonIdle(btnEl);
      }
    } else {
      // YouTube iframe — clicking again stops it
      _stopActive();
    }
    return;
  }

  // Stop any currently playing preview
  _stopActive();

  // ── YouTube Music: compact autoplay iframe ────────────────────────────────
  const videoId = _extractYouTubeVideoId(songUrl);
  if (videoId) {
    const iframeEl = document.createElement("iframe");
    iframeEl.src = `https://www.youtube-nocookie.com/embed/${videoId}?autoplay=1&modestbranding=1&rel=0&showinfo=0`;
    iframeEl.allow = "autoplay; encrypted-media";
    iframeEl.setAttribute("allowfullscreen", "");
    iframeEl.style.cssText =
      "width:100%;height:80px;border:none;border-radius:8px;display:block;";
    iframeEl.title = `Preview: ${songTitle}`;

    const wrapperEl = document.createElement("div");
    wrapperEl.className = "inline-preview-wrapper";
    wrapperEl.appendChild(iframeEl);

    const actionsEl = cardEl.querySelector(".song-actions");
    if (actionsEl) {
      actionsEl.insertAdjacentElement("afterend", wrapperEl);
    } else {
      cardEl.appendChild(wrapperEl);
    }

    _active = { url: songUrl, audioEl: null, iframeEl, wrapperEl, btnEl };
    // For iframes we go straight to "playing" state (stop on next click)
    btnEl.innerHTML = ICON_STOP;
    btnEl.title = "Stop preview";
    btnEl.disabled = false;
    btnEl.classList.remove("preview-loading");
    btnEl.classList.add("preview-playing");
    return;
  }

  // ── SoundCloud / JioSaavn: audio proxy stream ─────────────────────────────
  // Show loading state
  _setButtonLoading(btnEl);

  const apiBase = getApiBaseUrl();
  const previewEndpoint = `${apiBase}/preview?url=${encodeURIComponent(songUrl)}`;

  // Create the audio element pointing directly at our proxied endpoint.
  // We don't need a separate fetch – just set src and let the browser stream.
  const audioEl = document.createElement("audio");
  audioEl.controls = true;
  audioEl.preload = "auto";
  audioEl.src = previewEndpoint;
  audioEl.className = "inline-preview-audio";
  audioEl.setAttribute("aria-label", `Preview: ${songTitle}`);

  // Wrapper so we can cleanly remove it later
  const wrapperEl = document.createElement("div");
  wrapperEl.className = "inline-preview-wrapper";
  wrapperEl.appendChild(audioEl);

  // Inject below .song-actions inside the card
  const actionsEl = cardEl.querySelector(".song-actions");
  if (actionsEl) {
    actionsEl.insertAdjacentElement("afterend", wrapperEl);
  } else {
    cardEl.appendChild(wrapperEl);
  }

  _active = { url: songUrl, audioEl, iframeEl: null, wrapperEl, btnEl };

  // canplay fires when enough data is buffered to start
  audioEl.addEventListener(
    "canplay",
    () => {
      audioEl.play().catch(() => {});
      _setButtonPlaying(btnEl);
    },
    { once: true },
  );

  // Restore button when playback ends naturally
  audioEl.addEventListener("ended", () => {
    _setButtonIdle(btnEl);
  });

  // Handle load errors
  audioEl.addEventListener("error", () => {
    _stopActive();
    toast.show(
      "error",
      "Preview unavailable",
      `Could not stream a preview for "${songTitle}".`,
      4000,
    );
  });
}

/** Stop any active preview and remove the inline player. */
export function stop(): void {
  _stopActive();
}

export const PreviewService = { play, stop };
