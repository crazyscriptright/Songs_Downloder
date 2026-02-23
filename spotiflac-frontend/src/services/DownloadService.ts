import {
  getApiBaseUrl,
  MAX_CONCURRENT_DOWNLOADS,
  MAX_POLL_ATTEMPTS,
  POLL_INTERVAL,
} from "@/config";
import type {
  AdvancedOptions,
  DownloadItem,
  DownloadRequestBody,
  DownloadResponse,
  DownloadStatusResponse,
  QueueItem,
  SearchType,
} from "@/types";
import { StorageService } from "./StorageService";
import { YouTubeService } from "./YouTubeService";

export type DownloadEventCallback = () => void;
export type ToastFn = (
  type: "success" | "error" | "info",
  title: string,
  message: string,
  duration?: number,
) => void;

/**
 * Manages the download queue, active downloads, status polling, and proxy fallback.
 */
export class DownloadService {
  allDownloads: Record<string, DownloadItem> = {};
  downloadQueue: QueueItem[] = [];
  activeDownloads = 0;

  private ongoingDownloads = new Set<string>();
  private onChange: DownloadEventCallback;
  private showToast: ToastFn;

  constructor(onChange: DownloadEventCallback, showToast: ToastFn) {
    this.onChange = onChange;
    this.showToast = showToast;
  }

  /** Load persisted downloads from localStorage. */
  loadFromStorage(): void {
    const loaded = StorageService.loadDownloads();
    // Ensure all downloads have timestamps
    this.allDownloads = {};
    for (const [id, download] of Object.entries(loaded)) {
      this.allDownloads[id] = {
        ...download,
        timestamp: download.timestamp || Date.now(),
      };
    }
  }

  /** Persist current downloads to localStorage. */
  saveToStorage(): void {
    StorageService.saveDownloads(this.allDownloads);
  }

  /** Count of actively downloading + queued items. */
  get activeBadgeCount(): number {
    const active = Object.values(this.allDownloads).filter(
      (d) => d.status === "downloading",
    ).length;
    return active + this.downloadQueue.length;
  }

  /** Add a download to the queue. If slots are available, start immediately. */
  queueDownload(
    url: string,
    title: string,
    button: HTMLButtonElement,
    useAdvanced = false,
  ): void {
    const item: QueueItem = {
      url,
      title,
      useAdvanced,
      status: "queued",
      timestamp: Date.now(),
      buttonId: button.id || `btn_${Date.now()}`,
    };

    if (!button.id) button.id = item.buttonId;

    this.downloadQueue.push(item);

    button.disabled = true;
    button.className = "download-btn queued";
    button.innerHTML = `<svg width=\"16\" height=\"16\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\"><rect x=\"6\" y=\"4\" width=\"4\" height=\"16\"></rect><rect x=\"14\" y=\"4\" width=\"4\" height=\"16\"></rect></svg> Queued (${this.downloadQueue.length})`;

    this.showToast(
      "info",
      "Added to Queue",
      `${title} will download when a slot is available. Position: ${this.downloadQueue.length}`,
      4000,
    );
    this.onChange();
    this.processQueue();
  }

  /** Try to start queued downloads if slots are available. */
  processQueue(): void {
    while (
      this.activeDownloads < MAX_CONCURRENT_DOWNLOADS &&
      this.downloadQueue.length > 0
    ) {
      const item = this.downloadQueue.shift()!;
      const button = document.getElementById(
        item.buttonId,
      ) as HTMLButtonElement | null;
      if (button) {
        button.className = "download-btn downloading";
        button.innerHTML = '<div class=\"spinner\"></div> Starting...';
      }
      this.activeDownloads++;
      this.startDownload(item.url, item.title, item.useAdvanced, button);
      this.onChange();
    }
  }

  /**
   * Entry point: download a song. Queues if too many concurrent downloads.
   */
  downloadSong(
    url: string,
    title: string,
    button: HTMLButtonElement,
    useAdvanced = false,
  ): void {
    if (this.activeDownloads >= MAX_CONCURRENT_DOWNLOADS) {
      this.queueDownload(url, title, button, useAdvanced);
      return;
    }
    this.activeDownloads++;
    this.startDownload(url, title, useAdvanced, button);
  }

  /** Cancel a queued (not-yet-started) download. */
  cancelQueuedDownload(queueIndex: number): void {
    if (queueIndex >= 0 && queueIndex < this.downloadQueue.length) {
      const item = this.downloadQueue[queueIndex];
      const button = document.getElementById(
        item.buttonId,
      ) as HTMLButtonElement | null;
      if (button) {
        button.className = "download-btn";
        button.innerHTML = "Download";
        button.disabled = false;
      }
      this.downloadQueue.splice(queueIndex, 1);
      this.showToast(
        "info",
        "Removed from Queue",
        `${item.title} has been removed.`,
        3000,
      );
      this.onChange();
    }
  }

  /** Cancel an active download on the server. */
  async cancelDownload(downloadId: string): Promise<void> {
    try {
      const response = await fetch(
        `${getApiBaseUrl()}/cancel_download/${downloadId}`,
        { method: "POST" },
      );
      const result = await response.json();
      if (this.allDownloads[downloadId]) {
        this.allDownloads[downloadId].status = "cancelled";
        this.saveToStorage();
        this.onChange();
      }
      if (response.ok) {
        this.showToast(
          "info",
          "Download Cancelled",
          result.message || "Download has been cancelled.",
          3000,
        );
      } else {
        this.showToast(
          "error",
          "Cancel Failed",
          result.error || "Could not cancel download.",
        );
      }
    } catch {
      this.showToast("error", "Cancel Failed", "Failed to cancel download.");
    }
  }

  /** Remove all finished (complete/error/cancelled) downloads. */
  clearFinished(): void {
    for (const id in this.allDownloads) {
      const s = this.allDownloads[id].status;
      if (s === "complete" || s === "error" || s === "cancelled") {
        delete this.allDownloads[id];
      }
    }
    this.saveToStorage();
    this.onChange();
    this.showToast(
      "success",
      "Downloads Cleared",
      "All finished downloads have been removed.",
      3000,
    );
  }

  // ─── Private helpers ───────────────────────────────────────

  private cleanupOngoing(url: string, title: string): void {
    this.ongoingDownloads.delete(`${url}|${title}`);
  }

  private finishDownload(url: string, title: string): void {
    this.cleanupOngoing(url, title);
    this.activeDownloads--;
    this.processQueue();
  }

  /**
   * Build the advanced options object by reading from DOM elements.
   */
  buildAdvancedOptions(
    url: string,
    useAdvanced: boolean,
    searchType: SearchType,
  ): AdvancedOptions {
    let isVideoMode = false;

    if (searchType === "video") {
      isVideoMode = true;
    } else if (searchType === "music") {
      isVideoMode = false;
    } else {
      // 'all' — detect from DOM or URL
      if (document.getElementById("videoQuality")) {
        isVideoMode = true;
      } else if (
        (url.includes("youtube.com/watch") || url.includes("youtu.be/")) &&
        !url.includes("music.youtube.com")
      ) {
        isVideoMode = true;
      }
    }

    const opts: AdvancedOptions = {
      keepVideo: isVideoMode,
      embedSubtitles: useAdvanced
        ? (document.getElementById("embedSubs") as HTMLInputElement)
            ?.checked !== false
        : false,
      addMetadata: useAdvanced
        ? (document.getElementById("addMetadata") as HTMLInputElement)
            ?.checked !== false
        : true,
      customArgs: "",
    };

    if (isVideoMode) {
      opts.videoQuality =
        (document.getElementById("videoQuality") as HTMLSelectElement)?.value ||
        "1080";
      opts.videoFPS =
        (document.getElementById("videoFPS") as HTMLSelectElement)?.value ||
        "30";
      opts.videoFormat =
        (document.getElementById("videoFormat") as HTMLSelectElement)?.value ||
        "mkv";
    } else {
      opts.audioFormat =
        (document.getElementById("audioFormat") as HTMLSelectElement)?.value ||
        "mp3";
      opts.audioQuality =
        (document.getElementById("audioQuality") as HTMLSelectElement)?.value ||
        "0";
      opts.embedThumbnail = useAdvanced
        ? (document.getElementById("embedThumbnail") as HTMLInputElement)
            ?.checked !== false
        : true;
    }

    return opts;
  }

  /** Start a download (called internally). */
  private async startDownload(
    url: string,
    title: string,
    useAdvanced: boolean,
    button: HTMLButtonElement | null,
  ): Promise<void> {
    const downloadKey = `${url}|${title}`;
    if (this.ongoingDownloads.has(downloadKey)) return;
    this.ongoingDownloads.add(downloadKey);

    if (button) {
      button.disabled = true;
      button.className = "download-btn downloading";
      button.innerHTML = "⏳ Starting...";
    }

    try {
      const requestBody: DownloadRequestBody = { url, title };

      // Determine the current searchType from the DOM active button
      let searchType: SearchType = "music";
      const activeBtn = document.querySelector(
        ".type-btn.active",
      ) as HTMLElement | null;
      if (activeBtn) {
        searchType = (activeBtn.dataset.type as SearchType) || "music";
      }

      requestBody.advancedOptions = this.buildAdvancedOptions(
        url,
        useAdvanced,
        searchType,
      );

      const response = await fetch(`${getApiBaseUrl()}/download`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });

      const data: DownloadResponse = await response.json();
      if (!response.ok || (data as any).error) {
        throw new Error((data as any).error || "Download request failed");
      }

      const downloadId = data.download_id;

      this.allDownloads[downloadId] = {
        id: downloadId,
        title,
        url,
        status: "downloading",
        progress: 0,
        requestBody,
        timestamp: Date.now(),
      };
      this.saveToStorage();
      this.onChange();

      this.showToast(
        "info",
        "Download Started",
        `${title} has been queued for download.`,
        3000,
      );

      if (button) {
        this.pollStatus(downloadId, button, title, url, 0);
      }
    } catch (error: any) {
      this.cleanupOngoing(url, title);
      if (button) {
        button.className = "download-btn";
        button.innerHTML = "❌ Failed";
        button.disabled = false;
      }
      this.showToast("error", "Download Failed", `${title}: ${error.message}`);
      this.activeDownloads--;
      this.processQueue();
    }
  }

  /** Poll download status until complete / error / timeout. */
  private async pollStatus(
    downloadId: string,
    button: HTMLButtonElement,
    title: string,
    url: string,
    attemptCount: number,
  ): Promise<void> {
    if (attemptCount >= MAX_POLL_ATTEMPTS) {
      button.className = "download-btn";
      button.innerHTML = "⏱️ Timeout";
      button.disabled = false;
      this.showToast("error", "Download Timeout", `${title} took too long.`);
      this.finishDownload(url, title);
      return;
    }

    try {
      const response = await fetch(
        `${getApiBaseUrl()}/download_status/${downloadId}`,
      );
      const data: DownloadStatusResponse = await response.json();

      if (!response.ok && (data as any).error) {
        if ((data as any).error.toLowerCase().includes("not found")) {
          (data as any).status = "not_found";
        } else {
          throw new Error((data as any).error);
        }
      }

      // Update local tracking
      this.allDownloads[downloadId] = {
        id: downloadId,
        title: data.title || title,
        url: data.url || url,
        status: data.status,
        progress: data.progress || 0,
        error: data.error || null,
        download_url: data.download_url || null,
        speed: data.speed,
        eta: data.eta,
        timestamp: this.allDownloads[downloadId]?.timestamp || Date.now(),
      };
      this.saveToStorage();
      this.onChange();

      if (data.status === "complete") {
        button.className = "download-btn complete";
        button.innerHTML =
          '<svg width=\"16\" height=\"16\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\"><polyline points=\"20 6 9 17 4 12\"></polyline></svg> Downloaded';
        if (data.download_url) {
          const link = document.createElement("a");
          link.href = data.download_url.startsWith("http")
            ? data.download_url
            : `${getApiBaseUrl()}${data.download_url}`;
          link.download = data.file || title || "download";
          link.style.display = "none";
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          this.showToast(
            "success",
            "Download Complete",
            `${title} downloaded.`,
            4000,
          );
        }
        this.finishDownload(url, title);
      } else if (data.status === "error") {
        await this.handleDownloadError(downloadId, button, title, url, data);
      } else if (data.status === "cancelled") {
        button.className = "download-btn";
        button.innerHTML = "🚫 Cancelled";
        button.disabled = false;
        this.finishDownload(url, title);
      } else if (data.status === "downloading") {
        const progress = data.progress || 0;
        button.className = "download-btn downloading";
        button.innerHTML = `<div style=\"display:flex;flex-direction:column;align-items:center;gap:4px;\"><div>⏳ ${Math.round(progress)}%</div><div style=\"font-size:0.75em;opacity:0.8;\">${data.speed || "N/A"} • ETA ${data.eta || "N/A"}</div></div>`;
        setTimeout(
          () =>
            this.pollStatus(downloadId, button, title, url, attemptCount + 1),
          POLL_INTERVAL,
        );
      } else {
        // not_found, preparing, etc.
        setTimeout(
          () =>
            this.pollStatus(downloadId, button, title, url, attemptCount + 1),
          POLL_INTERVAL,
        );
      }
    } catch (error: any) {
      if (
        attemptCount < MAX_POLL_ATTEMPTS &&
        (error.name === "TypeError" || error.message?.includes("fetch"))
      ) {
        setTimeout(
          () =>
            this.pollStatus(downloadId, button, title, url, attemptCount + 1),
          POLL_INTERVAL,
        );
        return;
      }
      button.className = "download-btn";
      button.innerHTML = "❌ Error";
      button.disabled = false;
      this.showToast(
        "error",
        "Status Check Failed",
        `${title}: ${error.message}`,
      );
      this.finishDownload(url, title);
    }
  }

  /** Handle download error – try YouTube proxy fallback if applicable. */
  private async handleDownloadError(
    downloadId: string,
    button: HTMLButtonElement,
    title: string,
    url: string,
    data: DownloadStatusResponse,
  ): Promise<void> {
    const isYouTube = url.includes("youtube.com") || url.includes("youtu.be");

    if (isYouTube && !this.allDownloads[downloadId]?.fallbackAttempted) {
      this.allDownloads[downloadId].fallbackAttempted = true;
      this.saveToStorage();

      try {
        const req = this.allDownloads[downloadId]?.requestBody;
        const isVideo = req?.advancedOptions?.keepVideo === true;
        const format = isVideo
          ? req?.advancedOptions?.videoQuality || "360"
          : "mp3";
        const audioQuality = req?.advancedOptions?.audioQuality || "128";

        await YouTubeService.downloadViaProxy(
          url,
          title,
          format,
          audioQuality,
          (percent, text) => {
            button.className = "download-btn downloading";
            button.innerHTML = `${percent}% ${text}`;
            if (this.allDownloads[downloadId]) {
              this.allDownloads[downloadId].progress = percent;
              this.allDownloads[downloadId].statusText = text;
              this.saveToStorage();
              this.onChange();
            }
          },
        );

        // Mark complete
        if (this.allDownloads[downloadId]) {
          this.allDownloads[downloadId].status = "complete";
          this.allDownloads[downloadId].progress = 100;
          this.saveToStorage();
          this.onChange();
        }
        button.className = "download-btn complete";
        button.innerHTML =
          '<svg width=\"16\" height=\"16\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\"><polyline points=\"20 6 9 17 4 12\"></polyline></svg> Downloaded';
        this.showToast(
          "success",
          "Download Complete",
          `${title} downloaded via fallback.`,
          4000,
        );
        this.finishDownload(url, title);
        return;
      } catch (fallbackError: any) {
        button.className = "download-btn";
        button.innerHTML = "❌ Failed";
        button.disabled = false;
        this.showToast(
          "error",
          "Download Failed",
          `${title}: Both methods failed.`,
        );
        this.allDownloads[downloadId].status = "error";
        this.allDownloads[downloadId].error =
          `Both methods failed: ${fallbackError.message}`;
        this.saveToStorage();
        this.onChange();
        this.finishDownload(url, title);
        return;
      }
    }

    // Non-YouTube or fallback already attempted
    button.className = "download-btn";
    button.innerHTML = "❌ Failed";
    button.disabled = false;
    this.showToast(
      "error",
      "Download Failed",
      `${title}: ${data.error || "Unknown error"}`,
    );
    this.finishDownload(url, title);
  }
}
