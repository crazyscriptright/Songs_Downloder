import type { DownloadItem } from "@/types";

/**
 * Synchronise song card button + status area with the latest download
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
    const statusEl = card.querySelector<HTMLElement>(".download-status");

    if (!state) {
      // Reset to idle
      btn.className = "download-btn";
      btn.innerHTML = "Download";
      btn.disabled = false;
      if (statusEl) statusEl.style.display = "none";
      return;
    }

    // Status heading for the card
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

    // Populate / show the status area
    if (statusEl) {
      if (state.status === "downloading") {
        statusEl.style.display = "block";
        statusEl.className = "download-status downloading";
        statusEl.innerHTML = `
          <div class="ds-progress-bar">
            <div class="ds-progress-fill" style="width:${pct}%"></div>
          </div>
          <div class="ds-meta">
            <span>${pct}%</span>
            ${state.speed ? `<span>${state.speed}</span>` : ""}
            ${state.eta ? `<span>ETA ${state.eta}</span>` : ""}
          </div>
        `;
      } else if (state.status === "queued") {
        statusEl.style.display = "block";
        statusEl.className = "download-status queued";
        statusEl.innerHTML = `<span class="ds-label">⏸ Queued</span>`;
      } else if (state.status === "complete") {
        statusEl.style.display = "block";
        statusEl.className = "download-status complete";
        statusEl.innerHTML = `<span class="ds-label">✓ Downloaded</span>`;
      } else if (state.status === "error") {
        statusEl.style.display = "block";
        statusEl.className = "download-status error";
        statusEl.innerHTML = `<span class="ds-label">✕ ${state.error || "Failed"}</span>`;
      } else {
        statusEl.style.display = "none";
      }
    }
  });
}
