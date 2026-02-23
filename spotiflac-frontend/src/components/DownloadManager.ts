import { getApiBaseUrl } from "@/config";
import type { DownloadService } from "@/services/DownloadService";
import type { DownloadItem, QueueItem } from "@/types";

type DownloadFilter = "all" | "downloading" | "queued" | "complete" | "error";

const STATUS_ICONS: Record<string, string> = {
  queued:
    '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg>',
  downloading:
    '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7,10 12,15 17,10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>',
  complete:
    '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>',
  error:
    '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>',
  cancelled:
    '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>',
};

/**
 * Manages the download manager panel: filter, list, badge, toggle visibility.
 */
export class DownloadManager {
  private manager: HTMLElement;
  private downloadList: HTMLElement;
  private filterSelect: HTMLSelectElement;
  private badge: HTMLElement;
  private toggleBtn: HTMLElement;
  private visible = false;
  private currentFilter: DownloadFilter = "all";
  private downloadService!: DownloadService;

  constructor() {
    this.manager = document.getElementById("downloadManager") as HTMLElement;
    this.downloadList = document.getElementById("downloadList") as HTMLElement;
    this.filterSelect = document.getElementById(
      "downloadFilter",
    ) as HTMLSelectElement;
    this.badge = document.getElementById("downloadBadge") as HTMLElement;
    this.toggleBtn = document.getElementById("downloadToggle") as HTMLElement;

    this.filterSelect?.addEventListener("change", () => {
      this.currentFilter = this.filterSelect.value as DownloadFilter;
      this.render();
    });

    this.toggleBtn?.addEventListener("click", () => this.toggle());

    const closeBtn = document.getElementById("closeDownloadManager");
    closeBtn?.addEventListener("click", () => this.toggle());

    const clearBtn = document.getElementById("clearFinished");
    clearBtn?.addEventListener("click", () =>
      this.downloadService.clearFinished(),
    );
  }

  /** Provide a reference to the DownloadService (avoids circular deps). */
  setService(service: DownloadService): void {
    this.downloadService = service;
  }

  /** Toggle visibility of the panel. */
  toggle(): void {
    this.visible = !this.visible;
    if (this.visible) {
      this.manager.classList.add("show");
    } else {
      this.manager.classList.remove("show");
    }
  }

  /** Re-render the download list and badge. */
  render(): void {
    this.updateList();
    this.updateBadge();
  }

  /** Update the badge count. */
  updateBadge(): void {
    if (!this.downloadService) return;
    const count = this.downloadService.activeBadgeCount;
    if (count > 0) {
      this.badge.textContent = String(count);
      this.badge.style.display = "flex";
    } else {
      this.badge.style.display = "none";
    }
  }

  /** Render the download list with current filter applied. */
  private updateList(): void {
    if (!this.downloadService) return;

    const downloads = Object.entries(this.downloadService.allDownloads);

    const queuedItems: [string, DownloadItem][] =
      this.downloadService.downloadQueue.map(
        (item: QueueItem, index: number) => [
          `queue_${index}`,
          {
            id: `queue_${index}`,
            title: item.title,
            url: item.url,
            status: "queued" as const,
            progress: 0,
            timestamp: item.timestamp || Date.now(),
          },
        ],
      );

    const allItems: [string, DownloadItem][] = [...downloads, ...queuedItems];

    const counts = {
      all: allItems.length,
      downloading: allItems.filter(([, d]) => d.status === "downloading")
        .length,
      queued: allItems.filter(([, d]) => d.status === "queued").length,
      complete: allItems.filter(([, d]) => d.status === "complete").length,
      error: allItems.filter(([, d]) => d.status === "error").length,
    };

    if (this.filterSelect) {
      this.filterSelect.innerHTML = `
        <option value="all">All (${counts.all})</option>
        <option value="downloading">Downloading (${counts.downloading})</option>
        <option value="queued">Queued (${counts.queued})</option>
        <option value="complete">Complete (${counts.complete})</option>
        <option value="error">Failed (${counts.error})</option>
      `;
      this.filterSelect.value = this.currentFilter;
    }

    let filtered = allItems;
    if (this.currentFilter !== "all") {
      filtered = allItems.filter(([, d]) => d.status === this.currentFilter);
    }

    if (filtered.length === 0) {
      const msg =
        this.currentFilter === "all"
          ? "No downloads yet"
          : `No ${this.currentFilter} downloads`;
      this.downloadList.innerHTML = `<div style="padding:20px;text-align:center;color:var(--text-secondary);">${msg}</div>`;
      return;
    }

    filtered.sort((a, b) => {
      const tA = new Date(a[1].timestamp || 0).getTime();
      const tB = new Date(b[1].timestamp || 0).getTime();
      return tB - tA;
    });

    this.downloadList.innerHTML = filtered
      .map(([downloadId, dl]) => {
        const pct = dl.progress || 0;
        const icon = STATUS_ICONS[dl.status] || "";

        let actions = "";
        if (dl.status === "queued") {
          const qIdx = downloadId.startsWith("queue_")
            ? downloadId.split("_")[1]
            : "-1";
          actions = `<button class="cancel" data-action="cancelQueue" data-index="${qIdx}">Remove</button>`;
        } else if (dl.status === "complete" && dl.download_url) {
          const fullUrl = dl.download_url.startsWith("http")
            ? dl.download_url
            : `${getApiBaseUrl()}${dl.download_url}`;
          actions = `<button data-action="redownload" data-url="${fullUrl}">Download</button>`;
        }

        let timeInfo: string;
        if (dl.status === "downloading") {
          timeInfo =
            (dl as any).statusText ||
            `${(dl as any).speed || "0 KB/s"} \u2022 ETA: ${(dl as any).eta || "Unknown"}`;
        } else if (dl.status === "queued") {
          const pos = downloadId.startsWith("queue_")
            ? parseInt(downloadId.split("_")[1]) + 1
            : "?";
          timeInfo = `Position ${pos} in queue`;
        } else {
          timeInfo = dl.timestamp
            ? new Date(dl.timestamp).toLocaleString()
            : "";
        }

        return `
          <div class="download-item ${dl.status}">
            <div class="download-title">${dl.title}</div>
            <div class="download-progress">
              <div class="progress-bar">
                <div class="progress-fill ${dl.status}" style="width: ${pct}%"></div>
              </div>
            </div>
            <div class="download-info">
              <span>${icon} ${pct}% \u2022 ${timeInfo}</span>
              <div class="download-actions">${actions}</div>
            </div>
          </div>
        `;
      })
      .join("");

    this.downloadList
      .querySelectorAll<HTMLButtonElement>("[data-action]")
      .forEach((btn) => {
        const action = btn.dataset.action;
        if (action === "cancelQueue") {
          btn.addEventListener("click", () => {
            const idx = parseInt(btn.dataset.index || "-1");
            if (idx >= 0) this.downloadService.cancelQueuedDownload(idx);
          });
        } else if (action === "redownload") {
          btn.addEventListener("click", () =>
            window.open(btn.dataset.url, "_blank"),
          );
        }
      });
  }
}
