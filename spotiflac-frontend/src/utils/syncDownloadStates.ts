import type { DownloadItem } from "@/types";

/**
 * Synchronise song card button with the latest download
 * state for each URL.  Called after every poll update and after results
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

  document.querySelectorAll<HTMLElement>(".song-card").forEach((card) => {
    const btn = card.querySelector<HTMLButtonElement>(".download-btn");
    if (!btn) return;
    const url = btn.dataset.songUrl;
    if (!url) return;

    const state = urlStatus.get(url);

    if (!state) {
      // Reset to idle
      btn.className = "download-btn";
      btn.innerHTML = "Download";
      btn.disabled = false;
      return;
    }

    let label: string;
    let btnClass: string;
    const pct = Math.round(state.progress);

    switch (state.status) {
      case "queued":
        label = "Queued";
        btnClass = "download-btn queued";
        btn.disabled = true;
        break;
      case "downloading":
        label = `Downloading — ${pct}%`;
        btnClass = "download-btn downloading";
        btn.disabled = true;
        break;
      case "complete":
        label = "Downloaded";
        btnClass = "download-btn complete";
        btn.disabled = false;
        break;
      case "error":
        label = "Failed";
        btnClass = "download-btn";
        btn.disabled = false;
        break;
      case "cancelled":
        label = "Cancelled";
        btnClass = "download-btn";
        btn.disabled = false;
        break;
      default:
        label = state.status;
        btnClass = "download-btn";
        btn.disabled = false;
    }

    btn.className = btnClass;
    btn.innerHTML = label;
  });
}
