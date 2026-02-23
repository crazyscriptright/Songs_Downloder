import { SearchService } from "@/services/SearchService";
import { YouTubeService } from "@/services/YouTubeService";
import type {
  DirectUrlInfo,
  JioSaavnSuggestion,
  PreviewData,
  SearchType,
  Song,
  SoundCloudTrack,
  SourceId,
  SourceInfo,
} from "@/types";
import { createLazyImageHTML } from "@/utils/imageUtils";
import { initLazyLoadingForNewImages } from "@/utils/lazyLoader";
import { convertYouTubeMusicUrl } from "@/utils/urlDetector";
import {
  createSourceSection,
  type AdvancedCallback,
  type DownloadCallback,
} from "./SongCard";
import { SourceNavigation } from "./SourceNavigation";

type StatusFn = (type: string, title: string, subtitle?: string) => void;
type ToastFn = (
  type: "success" | "error" | "info",
  title: string,
  msg: string,
  dur?: number,
) => void;

const LINK_ICON =
  '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:inline;margin-right:8px;"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>';

export class ResultsContainer {
  private el: HTMLElement;
  private sourceNav: SourceNavigation;
  private searchType: SearchType = "music";

  /** External callbacks wired by App */
  onDownload: DownloadCallback = () => {};
  onAdvanced: AdvancedCallback = () => {};
  showStatus: StatusFn = () => {};
  showToast: ToastFn = () => {};

  constructor(sourceNav: SourceNavigation) {
    this.el = document.getElementById("results") as HTMLElement;
    this.sourceNav = sourceNav;
  }

  setSearchType(t: SearchType): void {
    this.searchType = t;
  }

  /** Clear results area and reset navigation. */
  clear(): void {
    this.el.innerHTML = "";
    this.sourceNav.reset();
  }

  displayResults(data: Record<string, Song[]>): void {
    this.el.innerHTML = "";

    const sources: SourceInfo[] = [];
    const order: { key: string; name: string; id: SourceId }[] = [
      { key: "jiosaavn", name: "JioSaavn", id: "jiosaavn" },
      { key: "ytmusic", name: "YouTube Music", id: "ytmusic" },
      { key: "soundcloud", name: "SoundCloud", id: "soundcloud" },
      { key: "ytvideo", name: "YouTube Videos", id: "ytvideo" },
    ];

    for (const s of order) {
      const arr = data[s.key];
      if (arr && arr.length > 0) {
        sources.push({ id: s.id, name: s.name, count: arr.length, data: arr });
      }
    }

    if (sources.length === 0) {
      this.el.innerHTML =
        '<div class="empty-state"><i>\u2205</i><h3>No results found</h3><p>Try a different search query</p></div>';
      return;
    }

    this.sourceNav.render(sources);
    this.sourceNav.onSwitch = (id) => this.switchSource(id);

    sources.forEach((source, index) => {
      const songs = data[source.id] || [];
      const section = createSourceSection(
        source.name,
        songs,
        source.id,
        this.searchType,
        this.onDownload,
        this.onAdvanced,
      );
      const isActive = this.sourceNav.userSelectedTab
        ? source.id === this.sourceNav.userSelectedTab
        : index === 0;
      section.className = "source-section" + (isActive ? " active" : "");
      this.el.appendChild(section);
    });

    setTimeout(() => initLazyLoadingForNewImages(), 0);
  }

  switchSource(sourceId: SourceId): void {
    this.el
      .querySelectorAll(".source-section")
      .forEach((s) => s.classList.remove("active"));
    const target = document.getElementById(sourceId);
    if (target) {
      target.classList.add("active");
      this.el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  async displayDirectUrl(info: DirectUrlInfo): Promise<void> {
    this.el.innerHTML = "";

    const loadingSection = document.createElement("div");
    loadingSection.className = "source-section active";
    loadingSection.style.maxWidth = "900px";
    loadingSection.style.margin = "0 auto";
    loadingSection.innerHTML = `
      <div class="source-header">
        <h2>${LINK_ICON}${info.source} - Loading...</h2>
      </div>
      <div class="url-result-card" style="background:var(--bg-card);padding:40px;border-radius:15px;border:2px solid var(--accent-color);text-align:center;">
        <div style="display:inline-block;width:50px;height:50px;border:5px solid var(--border-color);border-radius:50%;border-top-color:var(--accent-color);animation:spin 1s linear infinite;"></div>
        <p style="color:var(--text-secondary);margin-top:20px;font-size:1.1em;">\u23F3 Fetching preview data...</p>
      </div>
    `;
    this.el.appendChild(loadingSection);
    this.el.scrollIntoView({ behavior: "smooth", block: "start" });

    let processedInfo = { ...info };
    let youtubeData: ReturnType<typeof convertYouTubeMusicUrl> | null = null;

    if (
      info.source === "YouTube" &&
      (info.url.includes("music.youtube.com") ||
        info.url.includes("youtube.com") ||
        info.url.includes("youtu.be"))
    ) {
      youtubeData = convertYouTubeMusicUrl(info.url);
      processedInfo.url = youtubeData.convertedUrl;
      processedInfo.source = "YouTube";
    }

    let previewData: PreviewData | null = null;
    try {
      previewData = await SearchService.fetchPreview(processedInfo.url);
    } catch {
      this.showStatus(
        "error",
        "Invalid URL",
        "Unable to process the provided URL",
      );
      this.el.innerHTML = "";
      return;
    }

    let urlMode: SearchType = this.searchType;
    if (this.searchType === "all") {
      if (info.url.includes("music.youtube.com")) urlMode = "music";
      else if (
        info.url.includes("youtube.com/watch") ||
        info.url.includes("youtu.be/")
      )
        urlMode = "video";
      else if (info.source === "SoundCloud" || info.source === "JioSaavn")
        urlMode = "music";
      else urlMode = "music";
    }

    const section = document.createElement("div");
    section.className = "source-section active";
    section.style.maxWidth = "900px";
    section.style.margin = "0 auto";

    const previewHTML = this.buildPreviewHTML(
      processedInfo,
      previewData,
      youtubeData,
    );
    const optionsHTML = this.buildOptionsHTML(urlMode, info);
    const downloadTitle = (previewData && previewData.title) || info.url;

    section.innerHTML = `
      <div class="source-header">
        <h2>${LINK_ICON}${processedInfo.source} - Ready to Download</h2>
      </div>
      <div class="url-result-card" style="background:var(--bg-card);padding:30px;border-radius:15px;border:2px solid var(--accent-color);">
        ${previewHTML}
        ${optionsHTML}
        <button id="direct-url-download-btn" class="download-btn"
          style="width:100%;padding:15px;font-size:1.2em;font-weight:bold;"
          data-url="${processedInfo.url}" data-title="${downloadTitle}">
          Download Now
        </button>
        ${this.buildRecommendationsPlaceholder(previewData, info)}
      </div>
    `;

    this.el.innerHTML = "";
    this.el.appendChild(section);

    setTimeout(() => {
      const btn = document.getElementById(
        "direct-url-download-btn",
      ) as HTMLButtonElement | null;
      if (btn) {
        btn.addEventListener("click", () => {
          const url = btn.dataset.url!;
          const title = btn.dataset.title!;
          this.onDownload(url, title, btn, true);
        });
      }
      this.wireAdvancedToggle();
      this.wireOptionsTabSwitcher();
      this.wirePlaylistToggle();
      initLazyLoadingForNewImages();
    }, 0);

    if (previewData?.source === "JioSaavn" && previewData.pid) {
      this.loadJioSaavnSuggestions(
        previewData.pid,
        section,
        previewData.language || "",
      );
    }

    if (
      previewData?.source === "SoundCloud" &&
      previewData.soundcloud_data?.recommended_tracks?.length
    ) {
      this.renderSoundCloudRecommendations(
        previewData.soundcloud_data.recommended_tracks,
        section,
      );
    }

    this.showStatus(
      "complete",
      "Ready to download!",
      "All options configured and ready",
    );
    setTimeout(
      () => this.el.scrollIntoView({ behavior: "smooth", block: "start" }),
      100,
    );
  }

  private buildPreviewHTML(
    processedInfo: DirectUrlInfo,
    preview: PreviewData | null,
    ytData: ReturnType<typeof convertYouTubeMusicUrl> | null,
  ): string {
    if (ytData?.videoId) {
      const channel = preview
        ? preview.uploader || preview.channel || "Unknown"
        : "Unknown";
      const title = preview?.title || "YouTube Video";
      return `
        <div class="preview-grid" style="display:grid;grid-template-columns:560px 1fr;gap:20px;margin-bottom:25px;">
          <div>${YouTubeService.createIframe(ytData.videoId, title)}</div>
          <div>
            <h3 style="font-size:1.6em;margin-bottom:12px;color:var(--text-primary);line-height:1.3;">${title}</h3>
            <div style="color:var(--text-secondary);margin-bottom:15px;">
              <p style="margin:5px 0;"><strong>Channel:</strong> ${channel}</p>
              <p style="margin:5px 0;"><strong>Source:</strong> ${processedInfo.source}</p>
              <p style="margin:5px 0;font-size:0.9em;color:var(--text-tertiary);">
                <a href="${processedInfo.url}" target="_blank" style="color:var(--accent-color);text-decoration:none;">${processedInfo.url}</a>
              </p>
            </div>
          </div>
        </div>`;
    }

    if (preview?.soundcloud_data && preview.source === "SoundCloud") {
      const t = preview.soundcloud_data.main_track;
      const thumb =
        t.thumbnail ||
        'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect fill="%23333"/><text x="50%" y="50%" text-anchor="middle" dy=".3em" fill="%23666">\u266A</text></svg>';
      return `
        <div style="margin-bottom:30px;">
          <h3 style="font-size:1.4em;margin-bottom:15px;color:var(--accent-color);border-bottom:2px solid var(--accent-color);padding-bottom:8px;">Main Track</h3>
          <div style="display:grid;grid-template-columns:200px 1fr;gap:20px;padding:20px;background:var(--bg-secondary);border-radius:12px;">
            <div><img src="${thumb}" alt="${t.title}" style="width:100%;border-radius:8px;box-shadow:0 4px 15px rgba(0,0,0,0.3);" /></div>
            <div>
              <h4 style="font-size:1.3em;margin-bottom:8px;color:var(--text-primary);">${t.title}</h4>
              <div style="color:var(--text-secondary);margin-bottom:12px;">
                <p style="margin:3px 0;"><strong>Artist:</strong> ${t.artist}</p>
                <p style="margin:3px 0;"><strong>Duration:</strong> ${t.duration}</p>
                <p style="margin:3px 0;"><strong>Plays:</strong> ${t.plays ? t.plays.toLocaleString() : "0"}</p>
                <p style="margin:3px 0;"><strong>Likes:</strong> ${t.likes ? t.likes.toLocaleString() : "0"}</p>
                ${t.genre ? `<p style="margin:3px 0;"><strong>Genre:</strong> ${t.genre}</p>` : ""}
              </div>
            </div>
          </div>
        </div>`;
    }

    if (preview && !preview.error && preview.thumbnail) {
      const thumb = preview.thumbnail;
      return `
        <div class="preview-grid-generic" style="display:grid;grid-template-columns:320px 1fr;gap:20px;margin-bottom:25px;">
          <div>${createLazyImageHTML(thumb, "Thumbnail", "lazy-image", "width:100%;border-radius:10px;box-shadow:0 4px 15px rgba(0,0,0,0.3);")}</div>
          <div>
            <h3 style="font-size:1.6em;margin-bottom:12px;color:var(--text-primary);line-height:1.3;">${preview.title}</h3>
            <div style="color:var(--text-secondary);margin-bottom:15px;">
              <p style="margin:5px 0;"><strong>Artist:</strong> ${preview.uploader || preview.channel || "Unknown"}</p>
              ${preview.album ? `<p style="margin:5px 0;"><strong>Album:</strong> ${preview.album}</p>` : ""}
              ${preview.language ? `<p style="margin:5px 0;"><strong>Language:</strong> ${preview.language}</p>` : ""}
              ${preview.duration ? `<p style="margin:5px 0;"><strong>Duration:</strong> ${preview.duration}</p>` : ""}
              ${preview.plays ? `<p style="margin:5px 0;"><strong>Plays:</strong> ${preview.plays.toLocaleString()}</p>` : ""}
              ${preview.likes ? `<p style="margin:5px 0;"><strong>Likes:</strong> ${preview.likes.toLocaleString()}</p>` : ""}
              ${preview.genre ? `<p style="margin:5px 0;"><strong>Genre:</strong> ${preview.genre}</p>` : ""}
              <p style="margin:5px 0;"><strong>Source:</strong> ${preview.source || processedInfo.source}</p>
            </div>
          </div>
        </div>`;
    }

    if (preview && !preview.error) {
      return `
        <div style="margin-bottom:20px;">
          <h3 style="font-size:1.6em;margin-bottom:12px;color:var(--text-primary);">${preview.title}</h3>
          <p style="color:var(--text-secondary);margin:5px 0;"><strong>Artist:</strong> ${preview.uploader || preview.channel || "Unknown"}</p>
          ${preview.album ? `<p style="color:var(--text-secondary);margin:5px 0;"><strong>Album:</strong> ${preview.album}</p>` : ""}
          ${preview.duration ? `<p style="color:var(--text-secondary);margin:5px 0;"><strong>Duration:</strong> ${preview.duration}</p>` : ""}
          <p style="color:var(--text-secondary);margin:5px 0;"><strong>Source:</strong> ${preview.source || processedInfo.source}</p>
        </div>`;
    }

    return `
      <div style="margin-bottom:20px;">
        <h3 style="font-size:1.8em;margin-bottom:10px;color:var(--accent-color);">URL Validated</h3>
        <p style="color:var(--text-secondary);font-size:1.1em;"><strong>Source:</strong> ${processedInfo.source}</p>
        <p style="color:var(--text-tertiary);font-size:0.9em;word-break:break-all;">${processedInfo.url}</p>
      </div>`;
  }

  private buildOptionsHTML(urlMode: SearchType, info: DirectUrlInfo): string {
    const isVideo = urlMode === "video";
    const isYouTube = info.source === "YouTube";

    const basicTab = isVideo
      ? this.buildVideoBasicOptions(isYouTube)
      : this.buildAudioBasicOptions();

    const advancedTab = this.buildAdvancedTab(
      isVideo,
      info.is_playlist || false,
      urlMode,
    );

    return `
      <div style="margin-bottom:20px;">
        <button class="advanced-toggle" id="advancedToggleBtn" style="width:100%;text-align:center;margin-bottom:10px;">
          <span id="advancedToggleText">Show Download Options</span>
        </button>
        <div id="advancedOptions" class="advanced-options">
          <div class="options-tabs">
            <button class="tab-btn active" data-tab="basic">\uD83D\uDCE6 Basic</button>
            <button class="tab-btn" data-tab="advanced">\u26A1 Advanced</button>
          </div>
          <div id="basicOptionsTab" class="options-tab-content active">${basicTab}</div>
          <div id="advancedOptionsTab" class="options-tab-content">${advancedTab}</div>
        </div>
      </div>`;
  }

  private buildVideoBasicOptions(isYouTube: boolean): string {
    const qualityRow = isYouTube
      ? `<div class="option-row">
           <div class="option-group"><label>Video Quality</label>
             <select id="videoQuality">
               <option value="8k">8K (4320p)</option><option value="4k">4K (2160p)</option>
               <option value="2k">2K (1440p)</option><option value="1080" selected>Full HD (1080p)</option>
               <option value="720">HD (720p)</option><option value="480">SD (480p)</option>
               <option value="360">Low (360p)</option><option value="240">Very Low (240p)</option>
               <option value="144">Mobile (144p)</option><option value="best">\u2605 Best Available</option>
             </select></div>
           <div class="option-group"><label>Frame Rate</label>
             <select id="videoFPS">
               <option value="60">60 FPS</option><option value="30" selected>30 FPS</option><option value="any">Any</option>
             </select></div>
         </div>
         <div class="option-row">
           <div class="option-group"><label>Video Format</label>
             <select id="videoFormat">
               <option value="mkv" selected>MKV</option><option value="mp4">MP4</option><option value="webm">WebM</option>
             </select></div>
         </div>`
      : `<div class="option-row">
           <div class="option-group"><label>Video Format</label>
             <select id="videoFormat">
               <option value="mp4" selected>MP4</option><option value="mkv">MKV</option><option value="webm">WebM</option>
             </select></div>
         </div>`;

    return `${qualityRow}
      <div class="option-row"><div class="option-group">
        <label><input type="checkbox" id="embedSubs" checked> Embed Subtitles</label>
        <label><input type="checkbox" id="addMetadata" checked> Add Metadata</label>
      </div></div>`;
  }

  private buildAudioBasicOptions(): string {
    return `
      <div class="option-row">
        <div class="option-group"><label>Audio Format</label>
          <select id="audioFormat">
            <option value="mp3" selected>MP3</option><option value="m4a">M4A</option>
            <option value="opus">Opus</option><option value="vorbis">Vorbis</option>
            <option value="wav">WAV</option><option value="flac">FLAC</option>
          </select></div>
        <div class="option-group"><label>Audio Quality</label>
          <select id="audioQuality">
            <option value="0" selected>Best (320kbps)</option><option value="2">High (256kbps)</option>
            <option value="5">Medium (192kbps)</option><option value="9">Low (128kbps)</option>
          </select></div>
      </div>
      <div class="option-row"><div class="option-group">
        <label><input type="checkbox" id="embedThumbnail" checked> Embed Thumbnail</label>
        <label><input type="checkbox" id="addMetadata" checked> Add Metadata</label>
      </div></div>`;
  }

  private buildAdvancedTab(
    isVideo: boolean,
    isPlaylist: boolean,
    urlMode: SearchType,
  ): string {
    let html = "";

    if (isPlaylist) {
      const label = urlMode === "video" ? "Video" : "Song";
      html += `
        <div style="background:var(--gradient-primary);padding:15px;border-radius:10px;margin-bottom:20px;">
          <h4 style="margin:0 0 10px;color:var(--bg-primary);">Playlist Detected!</h4>
          <p style="margin:0;color:var(--bg-primary);opacity:0.9;font-size:0.9em;">Choose how to download.</p>
        </div>
        <div class="option-row">
          <div class="option-group"><label>Playlist Handling</label>
            <select id="playlistOption">
              <option value="no-playlist" selected>Single ${label} Only</option>
              <option value="yes-playlist">Entire Playlist</option>
              <option value="playlist-items">Specific Items</option>
            </select></div>
          <div class="option-group" id="playlistItemsGroup" style="display:none;">
            <label>Items</label><input type="text" id="playlistItems" placeholder="e.g. 1,2,5-10">
          </div>
        </div>`;
    }

    if (isVideo) {
      html += `
        <div class="option-row">
          <div class="option-group"><label>Subtitles</label>
            <select id="subtitleOption">
              <option value="none" selected>None</option><option value="auto">Auto (English)</option><option value="all">All Languages</option>
            </select></div>
          <div class="option-group"><label>Speed Limit</label>
            <input type="text" id="speedLimit" placeholder="e.g. 1M, 500K"></div>
        </div>
        <div class="option-row"><div class="option-group">
          <label><input type="checkbox" id="geoBypass"> Geo-bypass</label>
          <label><input type="checkbox" id="preferFreeFormats"> Prefer Free Formats (VP9/AV1)</label>
        </div></div>
        <div class="option-row"><div class="option-group">
          <label><input type="checkbox" id="embedSubs" checked> Embed Subtitles</label>
          <label><input type="checkbox" id="addChapters"> Add Chapters</label>
        </div></div>`;
    } else {
      html += `
        <div class="option-row">
          <div class="option-group"><label>Speed Limit</label>
            <input type="text" id="speedLimit" placeholder="e.g. 1M, 500K"></div>
          <div class="option-group"><label><input type="checkbox" id="geoBypass"> Geo-bypass</label></div>
        </div>
        <div class="option-row"><div class="option-group">
          <label><input type="checkbox" id="preferFreeFormats"> Prefer Free Formats</label>
          <label><input type="checkbox" id="addMetadata" checked> Add Metadata</label>
        </div></div>`;
    }

    html += `
      <div class="option-group">
        <label>Custom yt-dlp Arguments</label>
        <input type="text" id="customArgs" placeholder="e.g. --retries 10">
        <small style="color:var(--text-tertiary);font-size:0.85em;margin-top:5px;display:block;">Only whitelisted arguments accepted</small>
      </div>
      <div class="option-group">
        <label>Max File Size</label>
        <input type="text" id="maxFileSize" placeholder="e.g. 100M, 1G">
        <small style="color:var(--text-tertiary);font-size:0.85em;margin-top:5px;display:block;">Skip files larger than this</small>
      </div>`;

    return html;
  }

  private buildRecommendationsPlaceholder(
    preview: PreviewData | null,
    info: DirectUrlInfo,
  ): string {
    if (preview?.source === "JioSaavn" && preview.pid) {
      return `
        <div id="jiosaavn-suggestions-container" style="margin:25px 0;">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:15px;">
            <h3 style="font-size:1.4em;color:var(--info-color);margin:0;">Recommended Tracks</h3>
            <div class="loading-spinner" style="width:20px;height:20px;border:2px solid var(--border-color);border-top:2px solid var(--info-color);border-radius:50%;animation:spin 1s linear infinite;"></div>
          </div>
          <p style="color:var(--text-secondary);font-style:italic;">Loading recommendations...</p>
        </div>`;
    }
    return "";
  }

  private async loadJioSaavnSuggestions(
    pid: string,
    section: HTMLElement,
    language: string,
  ): Promise<void> {
    try {
      const suggestions = await SearchService.fetchJioSaavnSuggestions(
        pid,
        language,
      );
      const container = section.querySelector(
        "#jiosaavn-suggestions-container",
      );
      if (!container || !suggestions.length) {
        container?.remove();
        return;
      }

      container.innerHTML = `
        <h3 style="font-size:1.4em;margin-bottom:15px;color:var(--info-color);border-bottom:2px solid var(--info-color);padding-bottom:8px;">
          Recommended Tracks (${suggestions.length})
        </h3>
        <div class="recommended-tracks-grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:15px;">
          ${suggestions.map((s: JioSaavnSuggestion) => this.buildRecommendationCard(s)).join("")}
        </div>`;

      setTimeout(() => initLazyLoadingForNewImages(), 0);
    } catch {
      const c = section.querySelector("#jiosaavn-suggestions-container");
      c?.remove();
    }
  }

  private renderSoundCloudRecommendations(
    tracks: SoundCloudTrack[],
    section: HTMLElement,
  ): void {
    const html = `
      <div style="margin:25px 0;">
        <h3 style="font-size:1.4em;margin-bottom:15px;color:var(--info-color);border-bottom:2px solid var(--info-color);padding-bottom:8px;">
          Recommended Tracks (${tracks.length})
        </h3>
        <div class="recommended-tracks-grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:15px;">
          ${tracks.map((t) => this.buildRecommendationCard(t)).join("")}
        </div>
      </div>`;

    const btn = section.querySelector("#direct-url-download-btn");
    if (btn) btn.insertAdjacentHTML("afterend", html);
  }

  private buildRecommendationCard(track: {
    title: string;
    artist: string;
    url: string;
    thumbnail?: string;
    duration?: string;
    plays?: number;
  }): string {
    const hasThumb =
      track.thumbnail &&
      track.thumbnail.trim() !== "" &&
      track.thumbnail !== "null";
    const thumbHTML = hasThumb
      ? `<img src="${track.thumbnail}" alt="${track.title}" loading="lazy" style="width:60px;height:60px;border-radius:6px;object-fit:cover;" />`
      : '<div style="width:60px;height:60px;border-radius:6px;background:var(--bg-secondary);display:flex;align-items:center;justify-content:center;color:var(--text-tertiary);font-size:24px;">\u266A</div>';

    const safeTitle = track.title.replace(/'/g, "\\'");
    const btnId = `rec-btn-${Math.random().toString(36).slice(2, 8)}`;

    // We'll bind events after insertion
    return `
      <div class="recommended-track-card" style="background:var(--bg-card);border-radius:10px;padding:15px;border:1px solid var(--border-color);">
        <div style="display:flex;gap:12px;">
          <div style="flex-shrink:0;">${thumbHTML}</div>
          <div style="flex:1;min-width:0;">
            <h5 style="font-size:1em;margin-bottom:4px;color:var(--text-primary);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${track.title}</h5>
            <p style="font-size:0.85em;color:var(--text-secondary);margin-bottom:6px;">${track.artist}</p>
            <div style="font-size:0.75em;color:var(--text-tertiary);margin-bottom:8px;">
              ${track.duration || ""} ${track.plays ? "\u2022 " + track.plays.toLocaleString() + " plays" : ""}
            </div>
            <button class="download-btn rec-download" id="${btnId}" data-url="${track.url}" data-title="${safeTitle}"
              style="padding:6px 10px;font-size:0.85em;">Download</button>
          </div>
        </div>
      </div>`;
  }

  /* ---------------------------------------------------------------- */
  /* Interactive wiring helpers                                        */
  /* ---------------------------------------------------------------- */

  private wireAdvancedToggle(): void {
    const toggle = document.getElementById("advancedToggleBtn");
    const panel = document.getElementById("advancedOptions");
    const text = document.getElementById("advancedToggleText");
    if (!toggle || !panel) return;
    toggle.addEventListener("click", () => {
      const visible = panel.classList.toggle("show");
      if (text)
        text.textContent = visible
          ? "Hide Download Options"
          : "Show Download Options";
    });
  }

  private wireOptionsTabSwitcher(): void {
    document
      .querySelectorAll<HTMLButtonElement>(".tab-btn[data-tab]")
      .forEach((btn) => {
        btn.addEventListener("click", () => {
          document
            .querySelectorAll(".tab-btn")
            .forEach((b) => b.classList.remove("active"));
          document
            .querySelectorAll(".options-tab-content")
            .forEach((c) => c.classList.remove("active"));
          btn.classList.add("active");
          const target =
            btn.dataset.tab === "basic"
              ? "basicOptionsTab"
              : "advancedOptionsTab";
          document.getElementById(target)?.classList.add("active");
        });
      });
  }

  private wirePlaylistToggle(): void {
    const sel = document.getElementById(
      "playlistOption",
    ) as HTMLSelectElement | null;
    const group = document.getElementById("playlistItemsGroup");
    if (!sel || !group) return;
    sel.addEventListener("change", () => {
      group.style.display = sel.value === "playlist-items" ? "" : "none";
    });
  }
}
