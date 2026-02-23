import { getApiBaseUrl } from "@/config";

export type BulkDownloadStatus =
  | "queued"
  | "downloading"
  | "complete"
  | "error";

export interface BulkDownloadItem {
  url: string;
  title: string;
  status: BulkDownloadStatus;
  progress: number;
  error: string | null;
  downloadId: string | null;
  download_url: string | null;
  download_id?: string;
  speed?: string;
  isPlaylist?: boolean;
  format?: string;
  quality?: string | null;
  timestamp?: number;
}

export interface BulkAdvancedOptions {
  keepVideo: boolean;
  addMetadata: boolean;
  videoQuality?: string;
  videoFPS?: string;
  videoFormat?: string;
  audioFormat?: string;
  audioQuality?: string;
  embedThumbnail?: boolean;
  embedSubtitles?: boolean;
}

export interface PlaylistVideo {
  url: string;
  title: string;
}

export class BulkDownloadService {
  downloads: BulkDownloadItem[] = [];

  private heartbeatInterval: ReturnType<typeof setInterval> | null = null;
  private autoDownloadedIds = new Set<string>();
  private ongoingBulk = false;
  private ongoingPlaylist = false;

  private onChange: () => void;
  private showToast: (
    type: "success" | "error" | "info",
    title: string,
    msg: string,
    duration?: number,
  ) => void;

  constructor(
    onChange: () => void,
    showToast: (
      type: "success" | "error" | "info",
      title: string,
      msg: string,
      duration?: number,
    ) => void,
  ) {
    this.onChange = onChange;
    this.showToast = showToast;
  }

  loadFromStorage(): void {
    try {
      const stored = localStorage.getItem("allDownloads");
      if (!stored) return;
      const all = JSON.parse(stored) as Record<string, any>;

      this.downloads = Object.values(all)
        .filter((d: any) => {
          if (d.isPlaylist) return true;

          if (d.id && d.id.includes("bulk_")) return true;
          if (d.id && d.id.includes("playlist_")) return true;
          return false;
        })
        .map((d: any) => ({
          url: d.url,
          title: d.title,
          status: (["queued", "downloading", "complete", "error"].includes(
            d.status,
          )
            ? d.status
            : "error") as BulkDownloadStatus,
          progress: d.progress ?? 0,
          error: d.error ?? null,
          downloadId: d.id ?? null,
          download_url: d.download_url ?? null,
          isPlaylist: d.isPlaylist ?? false,
          timestamp: d.timestamp ?? Date.now(),
        }));

      this.downloads.forEach((d) => {
        if (d.status === "complete") {
          this.autoDownloadedIds.add(d.downloadId ?? d.download_id ?? d.url);
        }
      });
    } catch (e) {
      console.error("Error loading downloads from storage:", e);
    }
  }

  saveToStorage(): void {
    try {
      const existing = localStorage.getItem("allDownloads");
      const all: Record<string, any> = existing ? JSON.parse(existing) : {};

      this.downloads.forEach((d) => {
        const id = d.downloadId || d.url;
        if (id) {
          all[id] = {
            id,
            title: d.title,
            url: d.url,
            status: d.status,
            progress: d.progress,
            error: d.error,
            download_url: d.download_url,
            timestamp: all[id]?.timestamp || d.timestamp || Date.now(),
          };
        }
      });

      localStorage.setItem("allDownloads", JSON.stringify(all));

      window.dispatchEvent(new CustomEvent("downloadsChanged"));
    } catch (e) {
      console.error("Error saving downloads to storage:", e);
    }
  }

  static extractTitleFromUrl(url: string): string {
    try {
      if (url.includes("youtube.com") || url.includes("youtu.be")) {
        const m = url.match(/[?&]v=([^&]+)/);
        if (m) return `YouTube: ${m[1]}`;
      }
      if (url.includes("soundcloud.com")) {
        const parts = url.split("/");
        return (parts[parts.length - 1] || parts[parts.length - 2])
          .replace(/-/g, " ")
          .substring(0, 50);
      }
      if (url.includes("jiosaavn.com") || url.includes("saavn.com")) {
        const parts = url.split("/");
        return (parts[parts.length - 1] || parts[parts.length - 2])
          .replace(/-/g, " ")
          .substring(0, 50);
      }
      const u = new URL(url);
      return `${u.hostname}${u.pathname.substring(0, 30)}`;
    } catch {
      return url.substring(0, 50) + "...";
    }
  }

  resolveDownloadUrl(downloadUrl: string): string {
    return downloadUrl.startsWith("http")
      ? downloadUrl
      : `${getApiBaseUrl()}${downloadUrl}`;
  }

  get stats() {
    const completed = this.downloads.filter(
      (d) => d.status === "complete",
    ).length;
    const failed = this.downloads.filter((d) => d.status === "error").length;
    const total = this.downloads.length;
    return { total, completed, failed };
  }

  get playlistStats() {
    const pl = this.downloads.filter((d) => d.isPlaylist);
    return {
      total: pl.length,
      completed: pl.filter((d) => d.status === "complete").length,
      failed: pl.filter((d) => d.status === "error").length,
    };
  }

  async startBulkDownload(
    urls: string[],
    options: BulkAdvancedOptions,
  ): Promise<void> {
    if (this.ongoingBulk) {
      this.showToast(
        "error",
        "Bulk Download In Progress",
        "Please wait for the current bulk download to complete.",
      );
      return;
    }

    const validUrls: string[] = [];
    const invalidUrls: string[] = [];
    urls.forEach((url, i) => {
      try {
        const u = new URL(url);
        if (u.protocol === "http:" || u.protocol === "https:") {
          validUrls.push(url);
        } else {
          invalidUrls.push(`Line ${i + 1}: ${url.substring(0, 50)}...`);
        }
      } catch {
        invalidUrls.push(`Line ${i + 1}: ${url.substring(0, 50)}...`);
      }
    });

    if (invalidUrls.length > 0) {
      const msg =
        invalidUrls.length === 1
          ? `Invalid URL found: ${invalidUrls[0]}`
          : `${invalidUrls.length} invalid URL(s) found. First: ${invalidUrls[0]}`;
      this.showToast("error", "Invalid URL(s) Detected", msg, 8000);
      if (validUrls.length === 0) return;
      this.showToast(
        "info",
        "Continuing with Valid URLs",
        `Processing ${validUrls.length} valid URL(s)...`,
        3000,
      );
    }

    if (validUrls.length === 0) {
      this.showToast(
        "error",
        "No URLs Provided",
        "Please enter at least one URL to download.",
      );
      return;
    }

    this.showToast(
      "info",
      "Bulk Download Started",
      `Processing ${validUrls.length} URL(s)...`,
    );
    this.ongoingBulk = true;

    const bulkTimestamp = Date.now();
    this.downloads = validUrls.map((url, i) => ({
      url,
      title: BulkDownloadService.extractTitleFromUrl(url),
      status: "queued" as const,
      progress: 0,
      error: null,
      downloadId: `bulk_${bulkTimestamp}_${i}`,
      download_url: null,
      timestamp: bulkTimestamp,
    }));
    this.onChange();

    try {
      const resp = await fetch(`${getApiBaseUrl()}/bulk_download`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ urls: validUrls, advancedOptions: options }),
      });
      const data = await resp.json();

      if (data.bulk_id) {
        this.showToast(
          "success",
          "Download Submitted",
          `Successfully submitted ${validUrls.length} URL(s) for download.`,
          4000,
        );
        this.pollBulkProgress(data.bulk_id);
      } else {
        this.showToast(
          "error",
          "Bulk Download Failed",
          "Failed to start bulk download",
        );
        this.ongoingBulk = false;
      }
    } catch (err: any) {
      console.error("Bulk download error:", err);
      this.showToast(
        "error",
        "Bulk Download Error",
        err.message || "An unexpected error occurred",
      );
      this.ongoingBulk = false;
    }
  }

  private pollBulkProgress(bulkId: string): void {
    if (this.heartbeatInterval) clearInterval(this.heartbeatInterval);

    this.heartbeatInterval = setInterval(async () => {
      try {
        await fetch(`${getApiBaseUrl()}/bulk_heartbeat/${bulkId}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        });
      } catch (e) {
        console.error("Heartbeat error:", e);
      }
    }, 10_000);

    const poll = setInterval(async () => {
      try {
        const resp = await fetch(`${getApiBaseUrl()}/bulk_status/${bulkId}`);
        const data = await resp.json();

        if (!resp.ok && data.error?.toLowerCase().includes("not found")) return;
        if (data.error?.toLowerCase().includes("not found")) return;

        if (data.status === "timeout") {
          clearInterval(poll);
          this.clearHeartbeat();
          this.ongoingBulk = false;
          this.showToast(
            "error",
            "Bulk Download Timeout",
            "Download timed out due to inactivity. Please stay on the page.",
          );
          return;
        }

        if (data.downloads) {
          const prevStatuses = this.downloads.map((d) => d.status);
          const prevIds = this.downloads.map((d) => d.downloadId);
          const prevTitles = this.downloads.map((d) => d.title);
          const prevTimestamps = this.downloads.map((d) => d.timestamp);

          this.downloads = data.downloads.map((dl: any, i: number) => ({
            ...dl,

            title:
              dl.title ||
              prevTitles[i] ||
              BulkDownloadService.extractTitleFromUrl(
                dl.url || this.downloads[i]?.url || "",
              ),
            downloadId:
              dl.downloadId ||
              dl.download_id ||
              prevIds[i] ||
              `bulk_${Date.now()}_${i}`,
            timestamp: prevTimestamps[i] || Date.now(),
          }));

          this.downloads.forEach((dl, i) => {
            if (prevStatuses[i] && prevStatuses[i] !== dl.status) {
              if (dl.status === "complete") {
                this.showToast(
                  "success",
                  "Download Complete",
                  `${dl.title || "File"} downloaded successfully`,
                );
                this.triggerAutoDownload(dl, i);
              } else if (dl.status === "error") {
                this.showToast(
                  "error",
                  "Download Failed",
                  `${dl.title || "File"}: ${dl.error || "Unknown error"}`,
                );
              }
            }
          });

          this.saveToStorage();
          this.onChange();

          const allDone = this.downloads.every(
            (d) => d.status === "complete" || d.status === "error",
          );
          if (allDone || data.status === "complete") {
            clearInterval(poll);
            this.clearHeartbeat();
            this.ongoingBulk = false;
            const { completed, failed } = this.stats;
            this.showToast(
              "info",
              "Bulk Download Complete",
              `Completed: ${completed}, Failed: ${failed}`,
            );
          }
        }
      } catch (e) {
        console.error("Poll error:", e);
      }
    }, 3000);
  }

  private triggerAutoDownload(dl: BulkDownloadItem, index: number): void {
    if (!dl.download_url) return;
    const uid = dl.downloadId ?? dl.download_id ?? dl.url;
    if (this.autoDownloadedIds.has(uid)) return;
    this.autoDownloadedIds.add(uid);
    setTimeout(() => {
      const a = document.createElement("a");
      a.href = this.resolveDownloadUrl(dl.download_url!);
      a.download = dl.title || `download_${index + 1}`;
      a.style.display = "none";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    }, 500 * index);
  }

  async startPlaylistDownload(
    playlistUrl: string,
    type: "audio" | "video",
    playlistItems: string,
    audioOptions: { format: string; quality: string },
    videoOptions: {
      quality: string;
      fps: string;
      format: string;
      embedSubs: boolean;
    },
  ): Promise<void> {
    if (this.ongoingPlaylist) return;

    try {
      const u = new URL(playlistUrl);
      if (u.protocol !== "http:" && u.protocol !== "https:") {
        this.showToast(
          "error",
          "Invalid Playlist URL",
          "Please enter a valid HTTP/HTTPS URL.",
        );
        return;
      }
      if (
        !playlistUrl.includes("youtube.com/playlist") &&
        !playlistUrl.includes("youtu.be")
      ) {
        this.showToast(
          "error",
          "Invalid Playlist URL",
          "Please enter a valid YouTube playlist URL.",
        );
        return;
      }
    } catch {
      this.showToast(
        "error",
        "Invalid Playlist URL",
        "Please enter a valid URL format.",
      );
      return;
    }

    this.ongoingPlaylist = true;
    this.showToast(
      "info",
      "Extracting Playlist",
      "Extracting videos from playlist...",
      3000,
    );

    try {
      const extractResp = await fetch(`${getApiBaseUrl()}/extract_playlist`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: playlistUrl, playlistItems }),
      });
      const extractData = await extractResp.json();
      if (!extractResp.ok || !extractData.success)
        throw new Error(extractData.error || "Failed to extract playlist");

      const videos: PlaylistVideo[] = extractData.videos;
      if (videos.length === 0) {
        this.showToast(
          "error",
          "Playlist Empty",
          "No videos found in playlist",
        );
        this.ongoingPlaylist = false;
        return;
      }

      this.showToast(
        "success",
        "Playlist Extracted",
        `Successfully extracted ${videos.length} video(s) from playlist.`,
        4000,
      );
      this.showToast(
        "info",
        "Playlist Download Started",
        `Downloading ${videos.length} video(s) from playlist...`,
      );

      const format = type === "video" ? videoOptions.quality : "mp3";
      const quality = type === "audio" ? audioOptions.quality || "128" : null;

      const playlistTimestamp = Date.now();
      videos.forEach((video, i) => {
        this.downloads.push({
          url: video.url,
          title: video.title,
          status: "queued",
          progress: 0,
          downloadId: `playlist_${playlistTimestamp}_${i}`,
          download_url: null,
          error: null,
          isPlaylist: true,
          format,
          quality,
          timestamp: playlistTimestamp,
        });
      });
      this.saveToStorage();
      this.onChange();

      for (let i = 0; i < videos.length; i++) {
        const video = videos[i];
        const item = this.downloads.find(
          (d) => d.url === video.url && d.title === video.title,
        );
        if (!item) continue;

        try {
          item.status = "downloading";
          item.progress = 0;
          this.saveToStorage();
          this.onChange();

          await this.downloadViaProxy(
            video.url,
            video.title,
            item.downloadId!,
            format,
            quality,
          );
        } catch (err: any) {
          item.status = "error";
          item.error = err.message;
          this.saveToStorage();
          this.onChange();
        }
      }

      const { completed, failed } = this.playlistStats;
      this.showToast(
        "info",
        "Playlist Download Complete",
        `Completed: ${completed}, Failed: ${failed}`,
      );
    } catch (err: any) {
      console.error("Playlist download error:", err);
      this.showToast(
        "error",
        "Playlist Download Error",
        err.message || "Failed to download playlist",
      );
    } finally {
      this.ongoingPlaylist = false;
    }
  }

  private downloadViaProxy(
    url: string,
    title: string,
    downloadId: string,
    format: string,
    quality: string | null,
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      const base = getApiBaseUrl();
      const encoded = encodeURIComponent(url);
      const dlUrl = `${base}/proxy/download?format=${format}&url=${encoded}${quality ? `&quality=${quality}` : ""}`;

      fetch(dlUrl)
        .then((r) => r.json())
        .then((data) => {
          if (!data.success)
            throw new Error(data.error || "Proxy download failed");
          const progressId = data.id;
          let lastPct = 0;

          const poll = setInterval(async () => {
            try {
              const pr = await fetch(
                `${base}/proxy/progress?progress_id=${progressId}`,
              );
              const pd = await pr.json();

              if (pd.success) {
                const raw = pd.progress ?? 0;
                const pct = Math.min(Math.round((raw / 1000) * 100), 100);
                if (pct > lastPct) {
                  lastPct = pct;
                  const item = this.downloads.find(
                    (d) => d.downloadId === downloadId,
                  );
                  if (item) {
                    item.progress = pct;
                    item.status = pct >= 100 ? "complete" : "downloading";

                    if (pd.title) {
                      item.title = pd.title;
                    }
                    this.saveToStorage();
                    this.onChange();
                  }
                }
                if (pd.download_url) {
                  clearInterval(poll);
                  if (!pd.download_url || pd.download_url === "null") {
                    reject(new Error("Download URL is null"));
                    return;
                  }
                  const item = this.downloads.find(
                    (d) => d.downloadId === downloadId,
                  );
                  if (item) {
                    item.status = "complete";
                    item.progress = 100;
                    item.download_url = pd.download_url;

                    if (pd.title) {
                      item.title = pd.title;
                    }
                    this.saveToStorage();
                    this.onChange();
                  }

                  const fileUrl = `${base}/proxy/file?file_url=${encodeURIComponent(pd.download_url)}`;
                  const a = document.createElement("a");
                  a.href = fileUrl;
                  a.download = `${title}.${format}`;
                  document.body.appendChild(a);
                  a.click();
                  document.body.removeChild(a);
                  resolve();
                }
              } else if (pd.error) {
                clearInterval(poll);
                reject(new Error(pd.error));
              }
            } catch (e: any) {
              clearInterval(poll);
              const item = this.downloads.find(
                (d) => d.downloadId === downloadId,
              );
              if (item) {
                item.status = "error";
                item.error = e.message;
                this.saveToStorage();
                this.onChange();
              }
              reject(e);
            }
          }, 3000);
        })
        .catch(reject);
    });
  }

  clearDownloads(): void {
    this.downloads = [];
    this.saveToStorage();
    this.onChange();
  }

  clearHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  dispose(): void {
    this.clearHeartbeat();
  }
}
