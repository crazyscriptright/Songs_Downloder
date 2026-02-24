import type { SearchType, Song, SourceId } from "@/types";
import { initLazyLoading } from "@/utils/lazyLoader";
import { isMusicUrl } from "@/utils/urlDetector";

import { DownloadService } from "@/services/DownloadService";
import { SearchService } from "@/services/SearchService";

import { DownloadManager } from "@/components/DownloadManager";
import { ResultsContainer } from "@/components/ResultsContainer";
import { SearchBox } from "@/components/SearchBox";
import { SourceNavigation } from "@/components/SourceNavigation";
import { ToastNotification } from "@/components/ToastNotification";

const STATUS_DEFAULT_ICONS: Record<string, string> = {
  success:
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>',
  complete:
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>',
  error:
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>',
  warning:
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
};

export class App {
  private searchType: SearchType = "music";
  private currentSearchId: string | null = null;

  private statusDiv: HTMLElement;
  private toast: ToastNotification;
  private searchBox: SearchBox;
  private sourceNav: SourceNavigation;
  private results: ResultsContainer;
  private downloadMgr: DownloadManager;

  private downloadService: DownloadService;

  constructor() {
    this.statusDiv = document.getElementById("status") as HTMLElement;

    this.toast = new ToastNotification();
    this.searchBox = new SearchBox();
    this.sourceNav = new SourceNavigation();
    this.results = new ResultsContainer(this.sourceNav);
    this.downloadMgr = new DownloadManager();

    this.downloadService = new DownloadService(
      () => this.downloadMgr.render(),
      (t, title, msg, dur) => this.toast.show(t, title, msg, dur),
    );
    this.downloadMgr.setService(this.downloadService);
  }

  init(): void {
    this.downloadService.loadFromStorage();
    this.downloadMgr.render();

    this.searchBox.onSearch = () => this.performSearch();
    this.searchBox.onTypeChange = (type: SearchType) => {
      this.searchType = type;
      this.results.setSearchType(type);
    };

    this.results.onDownload = (url, title, btn, adv) =>
      this.downloadService.downloadSong(url, title, btn, adv);
    this.results.onAdvanced = (url, title, _btn) => {
      this.searchBox.query = url;
      this.searchBox.selectSearchType(this.searchType);
      this.performSearch();
    };
    this.results.showStatus = (t, title, sub) => this.showStatus(t, title, sub);
    this.results.showToast = (t, title, msg, dur) =>
      this.toast.show(t, title, msg, dur);

    initLazyLoading();
    this.initScrollOverlay();
    this.initOfflineDetection();

    window.addEventListener("popstate", () => this.handlePopState());

    this.handlePopState();
  }

  private showStatus(type: string, title: string, subtitle = ""): void {
    this.statusDiv.className = `status ${type} show`;
    this.statusDiv.style.display = "";

    let iconHTML: string;
    if (type === "searching" || type === "info") {
      iconHTML = '<div class="spinner"></div>';
    } else {
      iconHTML = `<span class="status-icon">${STATUS_DEFAULT_ICONS[type] || ""}</span>`;
    }

    const sub = subtitle ? `<br><small>${subtitle}</small>` : "";
    this.statusDiv.innerHTML = `${iconHTML}<strong>${title}</strong>${sub}`;
  }

  private hideStatus(): void {
    this.statusDiv.className = "status";
    setTimeout(() => {
      this.statusDiv.style.display = "none";
    }, 300);
  }

  /** Fade in a theme-colored overlay as the user scrolls past the hero area */
  private initScrollOverlay(): void {
    const update = () => {
      // Start fading in after 80px, reach full overlay around 500px scroll
      const scrollY = window.scrollY || document.documentElement.scrollTop;
      const start = 80;
      const end = 500;
      const clamped = Math.min(
        Math.max((scrollY - start) / (end - start), 0),
        1,
      );
      // Max overlay opacity ~0.85 so texture is still subtly visible
      const opacity = +(clamped * 0.85).toFixed(3);
      document.body.style.setProperty(
        "--scroll-overlay-opacity",
        String(opacity),
      );
    };

    let ticking = false;
    window.addEventListener(
      "scroll",
      () => {
        if (!ticking) {
          requestAnimationFrame(() => {
            update();
            ticking = false;
          });
          ticking = true;
        }
      },
      { passive: true },
    );

    // Run once on load (in case page is already scrolled)
    update();
  }

  /** Show toast when device goes offline/online */
  private initOfflineDetection(): void {
    window.addEventListener("offline", () => {
      this.toast.show(
        "error",
        "You're offline",
        "Check your internet connection",
        8000,
      );
    });

    window.addEventListener("online", () => {
      this.toast.show("success", "Back online", "Connection restored", 3000);
    });
  }

  async performSearch(): Promise<void> {
    const query = this.searchBox.query;
    if (!query) return;

    // Mark search as in progress to prevent suggestions
    this.searchBox.setSearchInProgress(true);

    const isMusicUrlFlag = isMusicUrl(query);

    if (isMusicUrlFlag) {
      try {
        new URL(query);
      } catch {
        this.toast.show(
          "error",
          "Invalid URL Format",
          "Please enter a valid URL.",
        );
        this.searchBox.setSearchInProgress(false);
        return;
      }
    }

    const newUrl = new URL(window.location.href);
    newUrl.searchParams.set("q", encodeURIComponent(query));
    newUrl.searchParams.set("type", this.searchType);
    window.history.pushState({}, "", newUrl.toString());

    this.results.clear();

    if (isMusicUrlFlag) {
      await this.searchByUrl(query);
    } else {
      await this.searchByKeyword(query);
    }
  }

  private async searchByUrl(query: string): Promise<void> {
    this.showStatus(
      "searching",
      "Processing URL...",
      "Extracting music information",
    );
    this.searchBox.input.disabled = true;

    const timeoutId = setTimeout(() => {
      this.showStatus(
        "info",
        "Still processing...",
        "URL analysis is taking longer than expected.",
      );
    }, 20000);

    try {
      const searchId = await SearchService.searchByUrl(query, this.searchType);
      this.currentSearchId = searchId;
      clearTimeout(timeoutId);
      this.pollSearchResults();
    } catch {
      clearTimeout(timeoutId);
      this.showStatus(
        "error",
        "URL processing failed!",
        "Please check the URL and try again",
      );
      this.toast.show(
        "error",
        "URL Processing Failed",
        "Please check the URL and try again.",
      );
      this.searchBox.input.disabled = false;
      this.searchBox.setSearchInProgress(false);
    }
  }

  private async pollSearchResults(): Promise<void> {
    if (!this.currentSearchId) return;

    try {
      const data = await SearchService.pollSearchStatus(this.currentSearchId);

      if (data.status === "complete") {
        if (
          data.query_type === "url" &&
          data.direct_url &&
          data.direct_url.length > 0
        ) {
          await this.results.displayDirectUrl(data.direct_url[0]);
        } else {
          this.results.displayResults({
            jiosaavn: data.jiosaavn || [],
            soundcloud: data.soundcloud || [],
            ytmusic: data.ytmusic || [],
            ytvideo: data.ytvideo || [],
          });
        }

        const total =
          (data.ytmusic?.length || 0) +
          (data.ytvideo?.length || 0) +
          (data.jiosaavn?.length || 0) +
          (data.soundcloud?.length || 0) +
          (data.direct_url?.length || 0);

        if (data.query_type === "url") {
          this.showStatus(
            "complete",
            total > 0
              ? "Info extracted successfully!"
              : "Could not extract info from URL",
            total > 0
              ? "Ready to download your content"
              : "Please check the URL and try again",
          );
        } else {
          this.showStatus(
            "complete",
            "Search complete!",
            `Found ${total} result${total !== 1 ? "s" : ""} across all sources`,
          );
        }

        this.searchBox.input.disabled = false;
        this.searchBox.setSearchInProgress(false);
      } else {
        setTimeout(() => this.pollSearchResults(), 500);
      }
    } catch {
      this.showStatus(
        "error",
        "Connection lost!",
        "Unable to fetch search results",
      );
      this.searchBox.input.disabled = false;
      this.searchBox.setSearchInProgress(false);
    }
  }

  private async searchByKeyword(query: string): Promise<void> {
    this.showStatus(
      "searching",
      "Searching all platforms...",
      "JioSaavn \u2022 SoundCloud \u2022 YouTube Music",
    );
    this.searchBox.input.disabled = true;

    const allResults: Record<string, Song[]> = {
      jiosaavn: [],
      soundcloud: [],
      ytmusic: [],
      ytvideo: [],
    };

    const timeoutId = setTimeout(() => {
      this.showStatus(
        "info",
        "Search is taking a bit longer...",
        "Connecting to music services. Please wait...",
      );
    }, 20000);

    const handleSourceResult = (
      source: SourceId,
      results: Song[],
      completed: number,
      total: number,
    ) => {
      allResults[source] = results;

      if (completed === 1) clearTimeout(timeoutId);

      const names: string[] = [];
      if (allResults.jiosaavn.length)
        names.push(`JioSaavn (${allResults.jiosaavn.length})`);
      if (allResults.soundcloud.length)
        names.push(`SoundCloud (${allResults.soundcloud.length})`);
      if (allResults.ytmusic.length)
        names.push(`YTMusic (${allResults.ytmusic.length})`);
      if (allResults.ytvideo.length)
        names.push(`YTVideo (${allResults.ytvideo.length})`);

      if (names.length > 0) {
        this.showStatus(
          "searching",
          `Found results: ${names.join(" • ")}`,
          `${completed}/${total} sources completed`,
        );
        this.results.displayResults({ ...allResults });
      }

      if (completed >= total) {
        clearTimeout(timeoutId);
        const totalCount =
          allResults.jiosaavn.length +
          allResults.soundcloud.length +
          allResults.ytmusic.length +
          allResults.ytvideo.length;
        if (totalCount > 0) {
          this.showStatus(
            "complete",
            "Search completed!",
            `Found ${totalCount} results across all platforms`,
          );
        } else {
          this.showStatus(
            "warning",
            "No results found",
            "Try different keywords or check spelling",
          );
        }
        this.searchBox.input.disabled = false;
        this.searchBox.setSearchInProgress(false);
      }
    };

    await SearchService.searchParallel(
      query,
      this.searchType,
      handleSourceResult,
    );
    clearTimeout(timeoutId);
  }

  private handlePopState(): void {
    const params = new URLSearchParams(window.location.search);
    const q = params.get("q");
    const t = params.get("type");

    if (q) {
      this.searchBox.query = decodeURIComponent(q);
      if (t) {
        this.searchType = t as SearchType;
        this.searchBox.selectSearchType(this.searchType);
        this.results.setSearchType(this.searchType);
      }
      this.performSearch();
    } else {
      this.searchBox.query = "";
      this.results.clear();
      this.hideStatus();
    }
  }
}
