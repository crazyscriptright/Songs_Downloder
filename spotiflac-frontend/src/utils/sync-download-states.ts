import type { DownloadItem } from "@/types";

/**
 * Helper to update a single download button from a urlStatus map.
 */
function _setButtonState(
  btn: HTMLButtonElement,
  state: DownloadItem | undefined,
  idleLabel: string,
  idleClass?: string,
): void {
  if (!state) {
    btn.className = idleClass || "download-btn";
    btn.innerHTML = idleLabel;
    btn.disabled = false;
    return;
  }

  const pct = Math.round(state.progress);

  switch (state.status) {
    case "queued":
      btn.innerHTML = "Queued";
      btn.className = "download-btn queued";
      btn.disabled = true;
      break;
    case "downloading":
      btn.innerHTML = `Downloading — ${pct}%`;
      btn.className = "download-btn downloading";
      btn.disabled = true;
      break;
    case "complete":
      btn.innerHTML =
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg> Downloaded';
      btn.className = "download-btn complete";
      btn.disabled = false;
      break;
    case "error":
      btn.innerHTML = "Failed";
      btn.className = "download-btn";
      btn.disabled = false;
      break;
    case "cancelled":
      btn.innerHTML = "Cancelled";
      btn.className = "download-btn";
      btn.disabled = false;
      break;
    default:
      btn.innerHTML = idleLabel;
      btn.className = idleClass || "download-btn";
      btn.disabled = false;
  }
}

/**
 * Synchronise all download buttons (song cards, recommendation cards,
 * and the direct-URL download button) with the latest download state
 * keyed by URL.  Called after every poll update and after search results
 * are first rendered.
 */
export function syncSongCardStates(downloads: Record<string, DownloadItem>): void {
  if (!downloads) return;

  // Latest download per URL (keyed by URL for fast lookup)
  const urlStatus = new Map<string, DownloadItem>();
  for (const item of Object.values(downloads)) {
    const prev = urlStatus.get(item.url);
    if (!prev || (item.timestamp ?? 0) > (prev.timestamp ?? 0)) {
      urlStatus.set(item.url, item);
    }
  }

  // 1. Song cards (search results)
  document.querySelectorAll<HTMLElement>(".song-card").forEach((card) => {
    const btn = card.querySelector<HTMLButtonElement>(".download-btn");
    if (!btn) return;
    const url = btn.dataset.songUrl;
    if (!url) return;
    _setButtonState(btn, urlStatus.get(url), "Download");
  });

  // 2. Recommendation-track download buttons
  document.querySelectorAll<HTMLElement>(".recommended-track-card").forEach((card) => {
    const btn = card.querySelector<HTMLButtonElement>(".rec-download");
    if (!btn) return;
    const url = btn.dataset.url;
    if (!url) return;
    _setButtonState(btn, urlStatus.get(url), "Download");
  });

  // 3. Direct-URL download button (advanced UI page)
  const directBtn = document.getElementById("direct-url-download-btn") as HTMLButtonElement | null;
  if (directBtn) {
    const url = directBtn.dataset.url;
    if (url) {
      _setButtonState(directBtn, urlStatus.get(url), "⤓ Download Now");
    }
  }
}
