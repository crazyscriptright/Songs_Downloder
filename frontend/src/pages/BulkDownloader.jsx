import { useState } from "react";
import { Link } from "react-router-dom";
import { DownloadManager } from "../components/layout/DownloadManager";
import { AnimatedBackground } from "../components/layout/AnimatedBackground";
import { PageHeader } from "../components/layout/PageHeader";
import { useTheme, useDownloadManager } from "../hooks/useDownload";
import { getApiBaseUrl } from "../utils/helpers";

export default function BulkDownloader() {
  const { theme, toggleTheme } = useTheme();
  const downloadManager = useDownloadManager();

  const [activeTab, setActiveTab] = useState("bulk");
  const [urlList, setUrlList] = useState("");
  const [playlistUrl, setPlaylistUrl] = useState("");

  // Bulk options
  const [bulkDownloadType, setBulkDownloadType] = useState("audio");
  const [bulkAudioFormat, setBulkAudioFormat] = useState("mp3");
  const [bulkAudioQuality, setBulkAudioQuality] = useState("0");
  const [bulkEmbedThumbnail, setBulkEmbedThumbnail] = useState(true);
  const [bulkAddMetadata, setBulkAddMetadata] = useState(true);
  const [bulkVideoQuality, setBulkVideoQuality] = useState("best");
  const [bulkVideoFPS, setBulkVideoFPS] = useState("any");
  const [bulkVideoFormat, setBulkVideoFormat] = useState("mkv");
  const [bulkEmbedSubtitles, setBulkEmbedSubtitles] = useState(false);

  // Playlist options
  const [playlistType, setPlaylistType] = useState("audio");
  const [playlistItems, setPlaylistItems] = useState("all");
  const [customRange, setCustomRange] = useState("");
  const [playlistAudioFormat, setPlaylistAudioFormat] = useState("mp3");
  const [playlistAudioQuality, setPlaylistAudioQuality] = useState("0");
  const [playlistEmbedThumbnail, setPlaylistEmbedThumbnail] = useState(true);
  const [playlistAddMetadata, setPlaylistAddMetadata] = useState(true);
  const [playlistVideoQuality, setPlaylistVideoQuality] = useState("best");
  const [playlistVideoFPS, setPlaylistVideoFPS] = useState("any");
  const [playlistVideoFormat, setPlaylistVideoFormat] = useState("mkv");
  const [playlistEmbedSubtitles, setPlaylistEmbedSubtitles] = useState(false);

  // Statistics
  const [stats, setStats] = useState({
    totalUrls: 0,
    completed: 0,
    failed: 0,
  });

  const handleBulkDownload = async () => {
    const urls = urlList.split("\n").filter((url) => url.trim());
    if (urls.length === 0) {
      alert("Please enter at least one URL");
      return;
    }

    setStats((prev) => ({ ...prev, totalUrls: urls.length }));

    // Prepare options for backend
    const options = {
      audioFormat: bulkAudioFormat,
      audioQuality: bulkAudioQuality,
      embedThumbnail: bulkEmbedThumbnail,
      addMetadata: bulkAddMetadata,
      keepVideo: bulkDownloadType === "video",
      videoQuality: bulkVideoQuality,
      videoFPS: bulkVideoFPS,
      videoFormat: bulkVideoFormat,
      embedSubtitles: bulkEmbedSubtitles,
    };

    // Send bulk download request to backend first
    try {
      const response = await fetch(`${getApiBaseUrl()}/bulk_download`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          urls: urls.map(url => url.trim()), 
          advancedOptions: options 
        }),
      });

      const data = await response.json();
      console.log("Bulk download started:", data);

      if (data.bulk_id) {
        // Create download entries in UI with bulkId-index format
        urls.forEach((url, index) => {
          const id = `${data.bulk_id}-${index}`;
          downloadManager.addDownload(id, {
            title: `URL ${index + 1}`,
            url: url.trim(),
            status: "queued",
            progress: 0,
            type: bulkDownloadType,
            format: bulkDownloadType === "audio" ? bulkAudioFormat : bulkVideoFormat,
            quality: bulkDownloadType === "audio" ? bulkAudioQuality : bulkVideoQuality,
          });
        });

        // Poll for progress
        pollBulkProgress(data.bulk_id);
      }
    } catch (error) {
      console.error("Bulk download error:", error);
      alert(`Error: ${error.message}`);
    }
  };

  // Poll bulk download progress
  const pollBulkProgress = async (bulkId) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`${getApiBaseUrl()}/bulk_status/${bulkId}`);
        const data = await response.json();

        console.log("Bulk status:", data);

        if (data.downloads) {
          // Update download manager with backend status
          data.downloads.forEach((download, index) => {
            const id = `${bulkId}-${index}`;
            downloadManager.updateDownload(id, {
              title: download.title || `URL ${index + 1}`,
              status: download.status,
              progress: download.progress || 0,
              url: download.url,
              downloadUrl: download.download_url,
              error: download.error,
            });
          });

          // Update stats
          const completed = data.downloads.filter(d => d.status === 'complete').length;
          const failed = data.downloads.filter(d => d.status === 'error').length;
          setStats(prev => ({ ...prev, completed, failed }));

          // Check if all done
          const allDone = data.downloads.every(
            (d) => d.status === "complete" || d.status === "error"
          );

          if (allDone) {
            clearInterval(pollInterval);
            console.log("All bulk downloads completed");
          }
        }
      } catch (error) {
        console.error("Poll error:", error);
        clearInterval(pollInterval);
      }
    }, 2000);
  };

  const handlePlaylistDownload = async () => {
    const url = playlistUrl.trim();
    if (!url) {
      alert("Please enter a playlist URL");
      return;
    }

    const id = Date.now().toString();
    
    // Add to download manager UI
    downloadManager.addDownload(id, {
      title: "Playlist",
      url: url,
      status: "downloading",
      progress: 0,
      type: playlistType,
      items: playlistItems === "custom" ? customRange : "all",
      format:
        playlistType === "audio" ? playlistAudioFormat : playlistVideoFormat,
      quality:
        playlistType === "audio" ? playlistAudioQuality : playlistVideoQuality,
      embedThumbnail: playlistType === "audio" ? playlistEmbedThumbnail : false,
      addMetadata: playlistType === "audio" ? playlistAddMetadata : false,
      fps: playlistType === "video" ? playlistVideoFPS : undefined,
      embedSubtitles: playlistType === "video" ? playlistEmbedSubtitles : false,
    });

    // Build options for backend
    const options = {
      keepVideo: playlistType === "video",
    };

    // Custom args for playlist items
    let customArgs = "";
    if (playlistItems === "custom" && customRange.trim()) {
      const validRange = /^(\d+|\d+-\d+)(,(\d+|\d+-\d+))*$/;
      if (!validRange.test(customRange.trim())) {
        alert("Invalid playlist range format. Use formats like: 1-5, 1,3,5, or 1-3,5-7");
        return;
      }
      customArgs += ` --playlist-items ${customRange.trim()}`;
    }

    if (playlistType === "audio") {
      options.audioFormat = playlistAudioFormat;
      options.audioQuality = playlistAudioQuality;
      options.embedThumbnail = playlistEmbedThumbnail;
      options.addMetadata = playlistAddMetadata;
    } else {
      options.videoQuality = playlistVideoQuality;
      options.videoFPS = playlistVideoFPS;
      options.videoFormat = playlistVideoFormat;
      options.embedSubtitles = playlistEmbedSubtitles;
      options.addMetadata = true;
    }

    if (customArgs) {
      options.customArgs = customArgs;
    }

    console.log("Starting playlist download:", { url, options });

    try {
      const response = await fetch(`${getApiBaseUrl()}/download`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url,
          title: url,
          advancedOptions: options,
        }),
      });

      const data = await response.json();
      console.log("Playlist download started:", data);

      if (data.download_id) {
        downloadManager.updateDownload(id, {
          downloadId: data.download_id,
          status: "downloading",
        });

        // Poll for progress
        pollPlaylistProgress(data.download_id, id);
      }
    } catch (error) {
      console.error("Playlist download error:", error);
      alert(`Error: ${error.message}`);
      downloadManager.updateDownload(id, {
        status: "error",
        error: error.message,
      });
    }
  };

  // Poll playlist progress
  const pollPlaylistProgress = async (downloadId, uiId) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`${getApiBaseUrl()}/download_status/${downloadId}`);
        const data = await response.json();

        console.log("Playlist status:", data);

        downloadManager.updateDownload(uiId, {
          status: data.status,
          progress: data.progress || 0,
          title: data.title || "Playlist",
          downloadUrl: data.download_url,
          error: data.error,
        });

        if (data.status === "complete" || data.status === "error") {
          clearInterval(pollInterval);
          console.log("Playlist download finished:", data.status);
        }
      } catch (error) {
        console.error("Poll error:", error);
        clearInterval(pollInterval);
        downloadManager.updateDownload(uiId, {
          status: "error",
          error: "Failed to fetch status",
        });
      }
    }, 2000);
  };

  const urlCount = urlList.split("\n").filter((url) => url.trim()).length;

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] p-4 md:p-5 relative">
      <AnimatedBackground theme={theme} />
      <div className="max-w-[1400px] mx-auto relative z-10">
        {/* Header */}
        <PageHeader
          title="Bulk & Playlist Downloader"
          subtitle="Download multiple songs or entire playlists at once"
          showHomeLink={true}
          theme={theme}
          toggleTheme={toggleTheme}
        />

        {/* Tabs */}
        <div className="flex gap-2 md:gap-3 mb-6 md:mb-8 justify-center flex-wrap px-2">
          <button
            onClick={() => setActiveTab("bulk")}
            className={`px-6 md:px-8 py-3 rounded-xl border-2 font-semibold text-sm md:text-base transition-all ${
              activeTab === "bulk"
                ? "bg-gradient-to-br from-[var(--accent-color)] to-[var(--accent-secondary)] text-white border-[var(--accent-color)]"
                : "bg-[var(--bg-card)] text-(--text-secondary) border-(--border-color) hover:bg-[var(--accent-color)] hover:text-[var(--bg-primary)]"
            }`}
          >
            Bulk URLs
          </button>
          <button
            onClick={() => setActiveTab("playlist")}
            className={`px-6 md:px-8 py-3 rounded-xl border-2 font-semibold text-sm md:text-base transition-all ${
              activeTab === "playlist"
                ? "bg-gradient-to-br from-[var(--accent-color)] to-[var(--accent-secondary)] text-white border-[var(--accent-color)]"
                : "bg-[var(--bg-card)] text-(--text-secondary) border-(--border-color) hover:bg-[var(--accent-color)] hover:text-[var(--bg-primary)]"
            }`}
          >
            Playlist
          </button>
        </div>

        {/* Bulk URLs Tab */}
        {activeTab === "bulk" && (
          <div
            className={`bg-[var(--bg-card)] rounded-2xl p-4 md:p-8 lg:p-10 mb-8 border border-(--border-color) transition-all ${
              theme === "light"
                ? "shadow-[0_10px_30px_rgba(0,0,0,0.2)]"
                : "shadow-[0_10px_30px_rgba(0,0,0,0.4)]"
            }`}
          >
            <h2 className="text-xl md:text-2xl font-bold text-[var(--text-primary)] mb-4 md:mb-5">
              Bulk URL Downloader
            </h2>
            <p className="text-sm md:text-base text-[var(--text-tertiary)] mb-4">
              Paste one URL per line. Downloads will be processed sequentially.
            </p>

            <textarea
              value={urlList}
              onChange={(e) => setUrlList(e.target.value)}
              placeholder={`https://www.youtube.com/watch?v=...\nhttps://soundcloud.com/...\nhttps://www.jiosaavn.com/song/...\n\nPaste your URLs here (one per line)`}
              className="w-full min-h-[250px] md:min-h-[300px] p-3 md:p-4 rounded-lg border-2 border-(--border-color) bg-[var(--bg-primary)] text-[var(--text-primary)] text-sm md:text-base font-mono resize-y outline-none mb-4 leading-relaxed focus:border-[var(--accent-color)] focus:shadow-[0_0_0_3px_var(--shadow-color)] transition-all"
            />

            <div className="mb-5">
              <label className="block mb-2 text-(--text-secondary) font-semibold text-sm md:text-base">
                Download Type
              </label>
              <select
                value={bulkDownloadType}
                onChange={(e) => setBulkDownloadType(e.target.value)}
                className="w-full p-3 rounded-lg border-2 border-(--border-color) bg-[var(--bg-primary)] text-[var(--text-primary)] text-sm md:text-base outline-none cursor-pointer focus:border-[var(--accent-color)] focus:shadow-[0_0_0_3px_var(--shadow-color)] transition-all"
              >
                <option value="audio">Audio Only</option>
                <option value="video">Video</option>
              </select>
            </div>

            {/* Audio Options */}
            {bulkDownloadType === "audio" && (
              <>
                <h3 className="mt-5 mb-4 text-(--text-secondary) text-lg md:text-xl font-semibold">
                  Audio Options
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-5 mb-5">
                  <div>
                    <label className="block mb-2 text-(--text-secondary) font-semibold text-sm md:text-base">
                      Audio Format
                    </label>
                    <select
                      value={bulkAudioFormat}
                      onChange={(e) => setBulkAudioFormat(e.target.value)}
                      className="w-full p-3 rounded-lg border-2 border-(--border-color) bg-[var(--bg-primary)] text-[var(--text-primary)] text-sm md:text-base outline-none cursor-pointer focus:border-[var(--accent-color)] focus:shadow-[0_0_0_3px_var(--shadow-color)] transition-all"
                    >
                      <option value="mp3">MP3</option>
                      <option value="m4a">M4A</option>
                      <option value="opus">Opus</option>
                      <option value="vorbis">Vorbis</option>
                      <option value="wav">WAV</option>
                      <option value="flac">FLAC</option>
                    </select>
                  </div>

                  <div>
                    <label className="block mb-2 text-(--text-secondary) font-semibold text-sm md:text-base">
                      Audio Quality
                    </label>
                    <select
                      value={bulkAudioQuality}
                      onChange={(e) => setBulkAudioQuality(e.target.value)}
                      className="w-full p-3 rounded-lg border-2 border-(--border-color) bg-[var(--bg-primary)] text-[var(--text-primary)] text-sm md:text-base outline-none cursor-pointer focus:border-[var(--accent-color)] focus:shadow-[0_0_0_3px_var(--shadow-color)] transition-all"
                    >
                      <option value="0">320</option>
                      <option value="2">260</option>
                      <option value="5">128</option>
                      <option value="9">64</option>
                    </select>
                  </div>
                </div>

                <div className="flex items-center gap-3 mb-4">
                  <input
                    type="checkbox"
                    id="bulkEmbedThumbnail"
                    className="w-5 h-5 cursor-pointer"
                    checked={bulkEmbedThumbnail}
                    onChange={(e) => setBulkEmbedThumbnail(e.target.checked)}
                  />
                  <label
                    htmlFor="bulkEmbedThumbnail"
                    className="m-0 text-(--text-secondary) font-medium cursor-pointer text-sm md:text-base"
                  >
                    Embed Thumbnail
                  </label>
                </div>

                <div className="flex items-center gap-3 mb-4">
                  <input
                    type="checkbox"
                    id="bulkAddMetadata"
                    className="w-5 h-5 cursor-pointer"
                    checked={bulkAddMetadata}
                    onChange={(e) => setBulkAddMetadata(e.target.checked)}
                  />
                  <label
                    htmlFor="bulkAddMetadata"
                    className="m-0 text-(--text-secondary) font-medium cursor-pointer text-sm md:text-base"
                  >
                    Add Metadata
                  </label>
                </div>
              </>
            )}

            {/* Video Options */}
            {bulkDownloadType === "video" && (
              <>
                <h3 className="mt-5 mb-4 text-(--text-secondary) text-lg md:text-xl font-semibold">
                  Video Options
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-5 mb-5">
                  <div>
                    <label className="block mb-2 text-(--text-secondary) font-semibold text-sm md:text-base">
                      Video Quality
                    </label>
                    <select
                      value={bulkVideoQuality}
                      onChange={(e) => setBulkVideoQuality(e.target.value)}
                      className="w-full p-3 rounded-lg border-2 border-(--border-color) bg-[var(--bg-primary)] text-[var(--text-primary)] text-sm md:text-base outline-none cursor-pointer focus:border-[var(--accent-color)] focus:shadow-[0_0_0_3px_var(--shadow-color)] transition-all"
                    >
                      <option value="best">Best Available</option>
                      <option value="2160">4K (2160p)</option>
                      <option value="1440">2K (1440p)</option>
                      <option value="1080">Full HD (1080p)</option>
                      <option value="720">HD (720p)</option>
                      <option value="480">SD (480p)</option>
                      <option value="360">Low (360p)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block mb-2 text-(--text-secondary) font-semibold text-sm md:text-base">
                      Frame Rate
                    </label>
                    <select
                      value={bulkVideoFPS}
                      onChange={(e) => setBulkVideoFPS(e.target.value)}
                      className="w-full p-3 rounded-lg border-2 border-(--border-color) bg-[var(--bg-primary)] text-[var(--text-primary)] text-sm md:text-base outline-none cursor-pointer focus:border-[var(--accent-color)] focus:shadow-[0_0_0_3px_var(--shadow-color)] transition-all"
                    >
                      <option value="any">Any FPS</option>
                      <option value="60">60 FPS</option>
                      <option value="30">30 FPS</option>
                    </select>
                  </div>

                  <div>
                    <label className="block mb-2 text-(--text-secondary) font-semibold text-sm md:text-base">
                      Video Format
                    </label>
                    <select
                      value={bulkVideoFormat}
                      onChange={(e) => setBulkVideoFormat(e.target.value)}
                      className="w-full p-3 rounded-lg border-2 border-(--border-color) bg-[var(--bg-primary)] text-[var(--text-primary)] text-sm md:text-base outline-none cursor-pointer focus:border-[var(--accent-color)] focus:shadow-[0_0_0_3px_var(--shadow-color)] transition-all"
                    >
                      <option value="mkv">MKV</option>
                      <option value="mp4">MP4</option>
                      <option value="webm">WebM</option>
                    </select>
                  </div>
                </div>

                <div className="flex items-center gap-3 mb-4">
                  <input
                    type="checkbox"
                    id="bulkEmbedSubtitles"
                    className="w-5 h-5 cursor-pointer"
                    checked={bulkEmbedSubtitles}
                    onChange={(e) => setBulkEmbedSubtitles(e.target.checked)}
                  />
                  <label
                    htmlFor="bulkEmbedSubtitles"
                    className="m-0 text-(--text-secondary) font-medium cursor-pointer text-sm md:text-base"
                  >
                    Embed Subtitles
                  </label>
                </div>
              </>
            )}

            <div className="flex flex-col sm:flex-row gap-3 md:gap-4 mt-5">
              <button
                onClick={handleBulkDownload}
                disabled={urlCount === 0}
                className={`flex-1 px-6 md:px-10 py-3 md:py-4 rounded-lg text-base md:text-lg font-semibold transition-all ${
                  urlCount === 0
                    ? "opacity-50 cursor-not-allowed bg-gradient-to-br from-[var(--accent-color)] to-[var(--accent-secondary)] text-white"
                    : "bg-gradient-to-br from-[var(--accent-color)] to-[var(--accent-secondary)] text-white hover:-translate-y-0.5 hover:shadow-[0_8px_20px_var(--shadow-color)]"
                }`}
              >
                Start Bulk Download
              </button>
              <button
                onClick={() => setUrlList("")}
                className="flex-1 px-6 md:px-10 py-3 md:py-4 rounded-lg border-2 border-(--border-color) text-base md:text-lg font-semibold bg-(--bg-secondary) text-(--text-secondary) transition-all hover:bg-[var(--border-color)]"
              >
                Clear URLs
              </button>
            </div>

            <div className="grid grid-cols-3 gap-3 md:gap-5 mt-5">
              <div className="bg-(--bg-secondary) border border-(--border-color) rounded-lg p-3 md:p-5 text-center">
                <div className="text-2xl md:text-3xl font-bold text-(--accent-color) mb-1">
                  {urlCount}
                </div>
                <div className="text-(--text-secondary) text-xs md:text-sm">
                  Total URLs
                </div>
              </div>
              <div className="bg-(--bg-secondary) border border-(--border-color) rounded-lg p-3 md:p-5 text-center">
                <div className="text-2xl md:text-3xl font-bold text-(--accent-color) mb-1">
                  {stats.completed}
                </div>
                <div className="text-(--text-secondary) text-xs md:text-sm">
                  Completed
                </div>
              </div>
              <div className="bg-(--bg-secondary) border border-(--border-color) rounded-lg p-3 md:p-5 text-center">
                <div className="text-2xl md:text-3xl font-bold text-(--accent-color) mb-1">
                  {stats.failed}
                </div>
                <div className="text-(--text-secondary) text-xs md:text-sm">
                  Failed
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Playlist Tab */}
        {activeTab === "playlist" && (
          <div
            className={`bg-[var(--bg-card)] rounded-2xl p-4 md:p-8 lg:p-10 mb-8 border border-(--border-color) transition-all ${
              theme === "light"
                ? "shadow-[0_10px_30px_rgba(0,0,0,0.2)]"
                : "shadow-[0_10px_30px_rgba(0,0,0,0.4)]"
            }`}
          >
            <h2 className="text-xl md:text-2xl font-bold text-[var(--text-primary)] mb-4 md:mb-5">
              Playlist Downloader
            </h2>
            <p className="text-sm md:text-base text-[var(--text-tertiary)] mb-4">
              Download entire playlists from YouTube with advanced options
            </p>

            <div className="mb-5">
              <label className="block mb-2 text-(--text-secondary) font-semibold text-sm md:text-base">
                Playlist URL
              </label>
              <input
                type="text"
                value={playlistUrl}
                onChange={(e) => setPlaylistUrl(e.target.value)}
                placeholder="https://www.youtube.com/playlist?list=..."
                className="w-full p-3 rounded-lg border-2 border-(--border-color) bg-[var(--bg-primary)] text-[var(--text-primary)] text-sm md:text-base outline-none focus:border-[var(--accent-color)] focus:shadow-[0_0_0_3px_var(--shadow-color)] transition-all"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-5 mb-5">
              <div>
                <label className="block mb-2 text-(--text-secondary) font-semibold text-sm md:text-base">
                  Download Type
                </label>
                <select
                  value={playlistType}
                  onChange={(e) => setPlaylistType(e.target.value)}
                  className="w-full p-3 rounded-lg border-2 border-(--border-color) bg-[var(--bg-primary)] text-[var(--text-primary)] text-sm md:text-base outline-none cursor-pointer focus:border-[var(--accent-color)] focus:shadow-[0_0_0_3px_var(--shadow-color)] transition-all"
                >
                  <option value="audio">Audio Only</option>
                  <option value="video">Video</option>
                </select>
              </div>

              <div>
                <label className="block mb-2 text-(--text-secondary) font-semibold text-sm md:text-base">
                  Playlist Items
                </label>
                <select
                  value={playlistItems}
                  onChange={(e) => setPlaylistItems(e.target.value)}
                  className="w-full p-3 rounded-lg border-2 border-(--border-color) bg-[var(--bg-primary)] text-[var(--text-primary)] text-sm md:text-base outline-none cursor-pointer focus:border-[var(--accent-color)] focus:shadow-[0_0_0_3px_var(--shadow-color)] transition-all"
                >
                  <option value="all">All Items</option>
                  <option value="custom">Custom Range</option>
                </select>
              </div>
            </div>

            {playlistItems === "custom" && (
              <div className="mb-5">
                <label className="block mb-2 text-(--text-secondary) font-semibold text-sm md:text-base">
                  Custom Range (e.g., 1-5, 10, 15-20)
                </label>
                <input
                  type="text"
                  value={customRange}
                  onChange={(e) => setCustomRange(e.target.value)}
                  placeholder="1-5,10,15-20"
                  className="w-full p-3 rounded-lg border-2 border-(--border-color) bg-[var(--bg-primary)] text-[var(--text-primary)] text-sm md:text-base outline-none focus:border-[var(--accent-color)] focus:shadow-[0_0_0_3px_var(--shadow-color)] transition-all"
                />
              </div>
            )}

            {/* Audio Options */}
            {playlistType === "audio" && (
              <>
                <h3 className="mt-5 mb-4 text-(--text-secondary) text-lg md:text-xl font-semibold">
                  Audio Options
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-5 mb-5">
                  <div>
                    <label className="block mb-2 text-(--text-secondary) font-semibold text-sm md:text-base">
                      Audio Format
                    </label>
                    <select
                      value={playlistAudioFormat}
                      onChange={(e) => setPlaylistAudioFormat(e.target.value)}
                      className="w-full p-3 rounded-lg border-2 border-(--border-color) bg-[var(--bg-primary)] text-[var(--text-primary)] text-sm md:text-base outline-none cursor-pointer focus:border-[var(--accent-color)] focus:shadow-[0_0_0_3px_var(--shadow-color)] transition-all"
                    >
                      <option value="mp3">MP3</option>
                      <option value="m4a">M4A</option>
                      <option value="opus">Opus</option>
                      <option value="vorbis">Vorbis</option>
                      <option value="wav">WAV</option>
                      <option value="flac">FLAC</option>
                    </select>
                  </div>

                  <div>
                    <label className="block mb-2 text-(--text-secondary) font-semibold text-sm md:text-base">
                      Audio Quality
                    </label>
                    <select
                      value={playlistAudioQuality}
                      onChange={(e) => setPlaylistAudioQuality(e.target.value)}
                      className="w-full p-3 rounded-lg border-2 border-(--border-color) bg-[var(--bg-primary)] text-[var(--text-primary)] text-sm md:text-base outline-none cursor-pointer focus:border-[var(--accent-color)] focus:shadow-[0_0_0_3px_var(--shadow-color)] transition-all"
                    >
                      <option value="0">Best (0)</option>
                      <option value="2">High (2)</option>
                      <option value="5">Medium (5)</option>
                      <option value="9">Low (9)</option>
                    </select>
                  </div>
                </div>

                <div className="flex items-center gap-3 mb-4">
                  <input
                    type="checkbox"
                    id="playlistEmbedThumbnail"
                    className="w-5 h-5 cursor-pointer"
                    checked={playlistEmbedThumbnail}
                    onChange={(e) =>
                      setPlaylistEmbedThumbnail(e.target.checked)
                    }
                  />
                  <label
                    htmlFor="playlistEmbedThumbnail"
                    className="m-0 text-(--text-secondary) font-medium cursor-pointer text-sm md:text-base"
                  >
                    Embed Thumbnail
                  </label>
                </div>

                <div className="flex items-center gap-3 mb-4">
                  <input
                    type="checkbox"
                    id="playlistAddMetadata"
                    className="w-5 h-5 cursor-pointer"
                    checked={playlistAddMetadata}
                    onChange={(e) => setPlaylistAddMetadata(e.target.checked)}
                  />
                  <label
                    htmlFor="playlistAddMetadata"
                    className="m-0 text-(--text-secondary) font-medium cursor-pointer text-sm md:text-base"
                  >
                    Add Metadata
                  </label>
                </div>
              </>
            )}

            {/* Video Options */}
            {playlistType === "video" && (
              <>
                <h3 className="mt-5 mb-4 text-(--text-secondary) text-lg md:text-xl font-semibold">
                  Video Options
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-5 mb-5">
                  <div>
                    <label className="block mb-2 text-(--text-secondary) font-semibold text-sm md:text-base">
                      Video Quality
                    </label>
                    <select
                      value={playlistVideoQuality}
                      onChange={(e) => setPlaylistVideoQuality(e.target.value)}
                      className="w-full p-3 rounded-lg border-2 border-(--border-color) bg-[var(--bg-primary)] text-[var(--text-primary)] text-sm md:text-base outline-none cursor-pointer focus:border-[var(--accent-color)] focus:shadow-[0_0_0_3px_var(--shadow-color)] transition-all"
                    >
                      <option value="best">Best Available</option>
                      <option value="2160">4K (2160p)</option>
                      <option value="1440">2K (1440p)</option>
                      <option value="1080">Full HD (1080p)</option>
                      <option value="720">HD (720p)</option>
                      <option value="480">SD (480p)</option>
                      <option value="360">Low (360p)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block mb-2 text-(--text-secondary) font-semibold text-sm md:text-base">
                      Frame Rate
                    </label>
                    <select
                      value={playlistVideoFPS}
                      onChange={(e) => setPlaylistVideoFPS(e.target.value)}
                      className="w-full p-3 rounded-lg border-2 border-(--border-color) bg-[var(--bg-primary)] text-[var(--text-primary)] text-sm md:text-base outline-none cursor-pointer focus:border-[var(--accent-color)] focus:shadow-[0_0_0_3px_var(--shadow-color)] transition-all"
                    >
                      <option value="any">Any FPS</option>
                      <option value="60">60 FPS</option>
                      <option value="30">30 FPS</option>
                    </select>
                  </div>

                  <div>
                    <label className="block mb-2 text-(--text-secondary) font-semibold text-sm md:text-base">
                      Video Format
                    </label>
                    <select
                      value={playlistVideoFormat}
                      onChange={(e) => setPlaylistVideoFormat(e.target.value)}
                      className="w-full p-3 rounded-lg border-2 border-(--border-color) bg-[var(--bg-primary)] text-[var(--text-primary)] text-sm md:text-base outline-none cursor-pointer focus:border-[var(--accent-color)] focus:shadow-[0_0_0_3px_var(--shadow-color)] transition-all"
                    >
                      <option value="mkv">MKV</option>
                      <option value="mp4">MP4</option>
                      <option value="webm">WebM</option>
                    </select>
                  </div>
                </div>

                <div className="flex items-center gap-3 mb-4">
                  <input
                    type="checkbox"
                    id="playlistEmbedSubtitles"
                    className="w-5 h-5 cursor-pointer"
                    checked={playlistEmbedSubtitles}
                    onChange={(e) =>
                      setPlaylistEmbedSubtitles(e.target.checked)
                    }
                  />
                  <label
                    htmlFor="playlistEmbedSubtitles"
                    className="m-0 text-(--text-secondary) font-medium cursor-pointer text-sm md:text-base"
                  >
                    Embed Subtitles
                  </label>
                </div>
              </>
            )}

            <div className="flex flex-col sm:flex-row gap-3 md:gap-4 mt-5">
              <button
                onClick={handlePlaylistDownload}
                disabled={!playlistUrl.trim()}
                className={`flex-1 px-6 md:px-10 py-3 md:py-4 rounded-lg text-base md:text-lg font-semibold transition-all ${
                  !playlistUrl.trim()
                    ? "opacity-50 cursor-not-allowed bg-gradient-to-br from-[var(--accent-color)] to-[var(--accent-secondary)] text-white"
                    : "bg-gradient-to-br from-[var(--accent-color)] to-[var(--accent-secondary)] text-white hover:-translate-y-0.5 hover:shadow-[0_8px_20px_var(--shadow-color)]"
                }`}
              >
                Download Playlist
              </button>
              <button
                onClick={() => setPlaylistUrl("")}
                className="flex-1 px-6 md:px-10 py-3 md:py-4 rounded-lg border-2 border-(--border-color) text-base md:text-lg font-semibold bg-(--bg-secondary) text-(--text-secondary) transition-all hover:bg-[var(--border-color)]"
              >
                Clear URL
              </button>
            </div>

            <div className="grid grid-cols-3 gap-3 md:gap-5 mt-5">
              <div className="bg-(--bg-secondary) border border-(--border-color) rounded-lg p-3 md:p-5 text-center">
                <div className="text-2xl md:text-3xl font-bold text-(--accent-color) mb-1">
                  0
                </div>
                <div className="text-(--text-secondary) text-xs md:text-sm">
                  Total Items
                </div>
              </div>
              <div className="bg-(--bg-secondary) border border-(--border-color) rounded-lg p-3 md:p-5 text-center">
                <div className="text-2xl md:text-3xl font-bold text-(--accent-color) mb-1">
                  0
                </div>
                <div className="text-(--text-secondary) text-xs md:text-sm">
                  Completed
                </div>
              </div>
              <div className="bg-(--bg-secondary) border border-(--border-color) rounded-lg p-3 md:p-5 text-center">
                <div className="text-2xl md:text-3xl font-bold text-(--accent-color) mb-1">
                  0
                </div>
                <div className="text-(--text-secondary) text-xs md:text-sm">
                  Failed
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      <DownloadManager {...downloadManager} />
    </div>
  );
}
