import {
  BulkDownloadService,
  type BulkAdvancedOptions,
  type BulkDownloadItem,
} from "@/services/BulkDownloadService";
import "@/styles/bulk.css";
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type FormEvent,
} from "react";
import { IoMusicalNote, IoVideocam } from "react-icons/io5";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type Tab = "bulk" | "playlist";
type DownloadType = "music" | "video";

/* ------------------------------------------------------------------ */
/*  Reusable sub-components                                            */
/* ------------------------------------------------------------------ */

function StatCard({ value, label }: { value: number; label: string }) {
  return (
    <div className="stat-card">
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Toast (lightweight — reuse existing toast container in RootLayout) */
/* ------------------------------------------------------------------ */

function showToast(
  type: "success" | "error" | "info",
  title: string,
  message: string,
  duration = 5000,
) {
  const container = document.getElementById("toastContainer");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  const icons: Record<string, string> = { success: "✓", error: "✕", info: "ℹ" };
  toast.innerHTML = `
    <div class="toast-icon">${icons[type] || "ℹ"}</div>
    <div class="toast-content">
      <div class="toast-title">${title}</div>
      <div class="toast-message">${message}</div>
    </div>
    <button class="toast-close" onclick="this.parentElement.remove()">×</button>
  `;
  container.appendChild(toast);
  if (duration > 0) {
    setTimeout(() => {
      toast.classList.add("removing");
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }
}

/* ------------------------------------------------------------------ */
/*  Main page component                                                */
/* ------------------------------------------------------------------ */

export default function Bulk() {
  /* ---- tabs ---- */
  const [activeTab, setActiveTab] = useState<Tab>("bulk");

  /* ---- bulk state ---- */
  const [bulkUrls, setBulkUrls] = useState("");
  const [bulkDownloadType, setBulkDownloadType] =
    useState<DownloadType>("music");
  const [bulkAudioFormat, setBulkAudioFormat] = useState("mp3");
  const [bulkAudioQuality, setBulkAudioQuality] = useState("0");
  const [bulkEmbedThumbnail, setBulkEmbedThumbnail] = useState(true);
  const [bulkVideoQuality, setBulkVideoQuality] = useState("1080");
  const [bulkVideoFPS, setBulkVideoFPS] = useState("30");
  const [bulkVideoFormat, setBulkVideoFormat] = useState("mkv");
  const [bulkEmbedSubs, setBulkEmbedSubs] = useState(true);
  const [bulkAddMetadata, setBulkAddMetadata] = useState(true);

  /* ---- playlist state ---- */
  const [playlistUrl, setPlaylistUrl] = useState("");
  const [playlistType, setPlaylistType] = useState<"audio" | "video">("audio");
  const [playlistItemsOption, setPlaylistItemsOption] = useState("all");
  const [customRange, setCustomRange] = useState("");
  const [plAudioFormat, setPlAudioFormat] = useState("mp3");
  const [plAudioQuality, setPlAudioQuality] = useState("0");
  const [plEmbedThumbnail, setPlEmbedThumbnail] = useState(true);
  const [plAddMetadata, setPlAddMetadata] = useState(true);
  const [plVideoQuality, setPlVideoQuality] = useState("best");
  const [plVideoFPS, setPlVideoFPS] = useState("any");
  const [plVideoFormat, setPlVideoFormat] = useState("mkv");
  const [plEmbedSubs, setPlEmbedSubs] = useState(false);

  /* ---- download tracking ---- */
  const [downloads, setDownloads] = useState<BulkDownloadItem[]>([]);
  const serviceRef = useRef<BulkDownloadService | null>(null);

  /* ---- computed ---- */
  const urlCount = bulkUrls
    .split("\n")
    .map((u) => u.trim())
    .filter(Boolean).length;
  const bulkStats = {
    completed: downloads.filter((d) => d.status === "complete" && !d.isPlaylist)
      .length,
    failed: downloads.filter((d) => d.status === "error" && !d.isPlaylist)
      .length,
  };
  const plStats = {
    total: downloads.filter((d) => d.isPlaylist).length,
    completed: downloads.filter((d) => d.isPlaylist && d.status === "complete")
      .length,
    failed: downloads.filter((d) => d.isPlaylist && d.status === "error")
      .length,
  };

  /* ---- init service ---- */
  const syncDownloads = useCallback(() => {
    if (serviceRef.current) {
      setDownloads([...serviceRef.current.downloads]);
    }
  }, []);

  useEffect(() => {
    const svc = new BulkDownloadService(syncDownloads, showToast);
    svc.loadFromStorage();
    serviceRef.current = svc;
    syncDownloads();

    const onBeforeUnload = () => svc.dispose();
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => {
      window.removeEventListener("beforeunload", onBeforeUnload);
      svc.dispose();
    };
  }, [syncDownloads]);

  /* ---- handlers ---- */

  const handleStartBulk = async (e: FormEvent) => {
    e.preventDefault();
    const urls = bulkUrls
      .split("\n")
      .map((u) => u.trim())
      .filter(Boolean);
    const isVideo = bulkDownloadType === "video";
    const opts: BulkAdvancedOptions = {
      keepVideo: isVideo,
      addMetadata: bulkAddMetadata,
      ...(isVideo
        ? {
            videoQuality: bulkVideoQuality,
            videoFPS: bulkVideoFPS,
            videoFormat: bulkVideoFormat,
            embedSubtitles: bulkEmbedSubs,
          }
        : {
            audioFormat: bulkAudioFormat,
            audioQuality: bulkAudioQuality,
            embedThumbnail: bulkEmbedThumbnail,
          }),
    };
    await serviceRef.current?.startBulkDownload(urls, opts);
  };

  const handleClearBulk = () => {
    setBulkUrls("");
    serviceRef.current?.clearDownloads();
  };

  const handleStartPlaylist = async (e: FormEvent) => {
    e.preventDefault();
    const items = playlistItemsOption === "custom" ? customRange : "";
    await serviceRef.current?.startPlaylistDownload(
      playlistUrl.trim(),
      playlistType,
      items,
      { format: plAudioFormat, quality: plAudioQuality },
      {
        quality: plVideoQuality,
        fps: plVideoFPS,
        format: plVideoFormat,
        embedSubs: plEmbedSubs,
      },
    );
  };

  const handleClearPlaylist = () => {
    setPlaylistUrl("");
    setCustomRange("");
  };

  /* ---- render ---- */

  return (
    <div className="bulk-page">
      <h2 className="bulk-title">Bulk &amp; Playlist Downloader</h2>
      <p className="bulk-subtitle">
        Download multiple songs or entire playlists at once
      </p>

      {/* Tabs */}
      <div className="tabs">
        <button
          className={`tab-btn ${activeTab === "bulk" ? "active" : ""}`}
          onClick={() => setActiveTab("bulk")}
        >
          Bulk URLs
        </button>
        <button
          className={`tab-btn ${activeTab === "playlist" ? "active" : ""}`}
          onClick={() => setActiveTab("playlist")}
        >
          Playlist
        </button>
      </div>

      {/* ============== BULK TAB ============== */}
      {activeTab === "bulk" && (
        <form className="content-box" onSubmit={handleStartBulk}>
          <h3 className="section-title">Bulk URL Downloader</h3>
          <p className="help-text">
            Paste one URL per line. Downloads will be processed sequentially.
          </p>

          <textarea
            className="url-input-area"
            value={bulkUrls}
            onChange={(e: ChangeEvent<HTMLTextAreaElement>) =>
              setBulkUrls(e.target.value)
            }
            placeholder={
              "https://www.youtube.com/watch?v=...\nhttps://soundcloud.com/...\nhttps://www.jiosaavn.com/song/...\n\nPaste your URLs here (one per line)"
            }
          />

          {/* Download type */}
          <div className="download-type-selector">
            <label className="type-label">Download Type (YouTube only):</label>
            <div className="type-options">
              <label className="radio-label">
                <input
                  type="radio"
                  name="bulkDlType"
                  value="music"
                  checked={bulkDownloadType === "music"}
                  onChange={() => setBulkDownloadType("music")}
                />
                <IoMusicalNote size={16} />
                Music
              </label>
              <label className="radio-label">
                <input
                  type="radio"
                  name="bulkDlType"
                  value="video"
                  checked={bulkDownloadType === "video"}
                  onChange={() => setBulkDownloadType("video")}
                />
                <IoVideocam size={16} />
                Video
              </label>
            </div>
          </div>

          {/* Audio options */}
          {bulkDownloadType === "music" && (
            <div className="options-section">
              <div className="options-grid">
                <div className="input-group">
                  <label>Audio Format</label>
                  <select
                    value={bulkAudioFormat}
                    onChange={(e) => setBulkAudioFormat(e.target.value)}
                  >
                    <option value="mp3">MP3</option>
                    <option value="m4a">M4A</option>
                    <option value="opus">Opus</option>
                    <option value="vorbis">Vorbis</option>
                    <option value="wav">WAV</option>
                    <option value="flac">FLAC</option>
                  </select>
                </div>
                <div className="input-group">
                  <label>Audio Quality</label>
                  <select
                    value={bulkAudioQuality}
                    onChange={(e) => setBulkAudioQuality(e.target.value)}
                  >
                    <option value="0">Best (0)</option>
                    <option value="2">High (2)</option>
                    <option value="5">Medium (5)</option>
                    <option value="9">Low (9)</option>
                  </select>
                </div>
              </div>
              <div className="checkbox-group">
                <input
                  type="checkbox"
                  id="bulkEmbedThumb"
                  checked={bulkEmbedThumbnail}
                  onChange={(e) => setBulkEmbedThumbnail(e.target.checked)}
                />
                <label htmlFor="bulkEmbedThumb">Embed Thumbnail</label>
              </div>
            </div>
          )}

          {/* Video options */}
          {bulkDownloadType === "video" && (
            <div className="options-section">
              <div className="options-grid">
                <div className="input-group">
                  <label>Video Quality</label>
                  <select
                    value={bulkVideoQuality}
                    onChange={(e) => setBulkVideoQuality(e.target.value)}
                  >
                    <option value="2160">4K (2160p)</option>
                    <option value="1440">2K (1440p)</option>
                    <option value="1080">Full HD (1080p)</option>
                    <option value="720">HD (720p)</option>
                    <option value="480">SD (480p)</option>
                    <option value="360">Low (360p)</option>
                  </select>
                </div>
                <div className="input-group">
                  <label>Video FPS</label>
                  <select
                    value={bulkVideoFPS}
                    onChange={(e) => setBulkVideoFPS(e.target.value)}
                  >
                    <option value="60">60 FPS</option>
                    <option value="30">30 FPS</option>
                    <option value="24">24 FPS</option>
                  </select>
                </div>
                <div className="input-group">
                  <label>Video Format</label>
                  <select
                    value={bulkVideoFormat}
                    onChange={(e) => setBulkVideoFormat(e.target.value)}
                  >
                    <option value="mkv">MKV (Best Quality)</option>
                    <option value="mp4">MP4 (Compatible)</option>
                    <option value="webm">WebM</option>
                  </select>
                </div>
              </div>
              <div className="checkbox-group">
                <input
                  type="checkbox"
                  id="bulkEmbedSubtitles"
                  checked={bulkEmbedSubs}
                  onChange={(e) => setBulkEmbedSubs(e.target.checked)}
                />
                <label htmlFor="bulkEmbedSubtitles">Embed Subtitles</label>
              </div>
            </div>
          )}

          {/* Common option */}
          <div className="checkbox-group">
            <input
              type="checkbox"
              id="bulkMeta"
              checked={bulkAddMetadata}
              onChange={(e) => setBulkAddMetadata(e.target.checked)}
            />
            <label htmlFor="bulkMeta">Add Metadata</label>
          </div>

          {/* Buttons */}
          <div className="button-group">
            <button type="submit" className="btn btn-primary">
              Start Bulk Download
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleClearBulk}
            >
              Clear URLs
            </button>
          </div>

          {/* Stats */}
          <div className="stats">
            <StatCard value={urlCount} label="Total URLs" />
            <StatCard value={bulkStats.completed} label="Completed" />
            <StatCard value={bulkStats.failed} label="Failed" />
          </div>
        </form>
      )}

      {/* ============== PLAYLIST TAB ============== */}
      {activeTab === "playlist" && (
        <form className="content-box" onSubmit={handleStartPlaylist}>
          <h3 className="section-title">Playlist Downloader</h3>
          <p className="help-text">
            Download entire playlists from YouTube with advanced options
          </p>

          <div className="input-group">
            <label>Playlist URL</label>
            <input
              type="text"
              value={playlistUrl}
              onChange={(e) => setPlaylistUrl(e.target.value)}
              placeholder="https://www.youtube.com/playlist?list=..."
            />
          </div>

          <div className="options-grid">
            <div className="input-group">
              <label>Download Type</label>
              <select
                value={playlistType}
                onChange={(e) =>
                  setPlaylistType(e.target.value as "audio" | "video")
                }
              >
                <option value="audio">Audio Only</option>
                <option value="video">Video</option>
              </select>
            </div>
            <div className="input-group">
              <label>Playlist Items</label>
              <select
                value={playlistItemsOption}
                onChange={(e) => setPlaylistItemsOption(e.target.value)}
              >
                <option value="all">All Items</option>
                <option value="custom">Custom Range</option>
              </select>
            </div>
          </div>

          {playlistItemsOption === "custom" && (
            <div className="input-group">
              <label>Custom Range (e.g., 1-5, 10, 15-20)</label>
              <input
                type="text"
                value={customRange}
                onChange={(e) => setCustomRange(e.target.value)}
                placeholder="1-5,10,15-20"
              />
            </div>
          )}

          {/* Audio options */}
          {playlistType === "audio" && (
            <div className="options-section">
              <h4 className="options-heading">Audio Options</h4>
              <div className="options-grid">
                <div className="input-group">
                  <label>Audio Format</label>
                  <select
                    value={plAudioFormat}
                    onChange={(e) => setPlAudioFormat(e.target.value)}
                  >
                    <option value="mp3">MP3</option>
                    <option value="m4a">M4A</option>
                    <option value="opus">Opus</option>
                    <option value="vorbis">Vorbis</option>
                    <option value="wav">WAV</option>
                    <option value="flac">FLAC</option>
                  </select>
                </div>
                <div className="input-group">
                  <label>Audio Quality</label>
                  <select
                    value={plAudioQuality}
                    onChange={(e) => setPlAudioQuality(e.target.value)}
                  >
                    <option value="0">Best (0)</option>
                    <option value="2">High (2)</option>
                    <option value="5">Medium (5)</option>
                    <option value="9">Low (9)</option>
                  </select>
                </div>
              </div>
              <div className="checkbox-group">
                <input
                  type="checkbox"
                  id="plEmbedThumb"
                  checked={plEmbedThumbnail}
                  onChange={(e) => setPlEmbedThumbnail(e.target.checked)}
                />
                <label htmlFor="plEmbedThumb">Embed Thumbnail</label>
              </div>
              <div className="checkbox-group">
                <input
                  type="checkbox"
                  id="plMeta"
                  checked={plAddMetadata}
                  onChange={(e) => setPlAddMetadata(e.target.checked)}
                />
                <label htmlFor="plMeta">Add Metadata</label>
              </div>
            </div>
          )}

          {/* Video options */}
          {playlistType === "video" && (
            <div className="options-section">
              <h4 className="options-heading">Video Options</h4>
              <div className="options-grid">
                <div className="input-group">
                  <label>Video Quality</label>
                  <select
                    value={plVideoQuality}
                    onChange={(e) => setPlVideoQuality(e.target.value)}
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
                <div className="input-group">
                  <label>Frame Rate</label>
                  <select
                    value={plVideoFPS}
                    onChange={(e) => setPlVideoFPS(e.target.value)}
                  >
                    <option value="any">Any FPS</option>
                    <option value="60">60 FPS</option>
                    <option value="30">30 FPS</option>
                  </select>
                </div>
                <div className="input-group">
                  <label>Video Format</label>
                  <select
                    value={plVideoFormat}
                    onChange={(e) => setPlVideoFormat(e.target.value)}
                  >
                    <option value="mkv">MKV</option>
                    <option value="mp4">MP4</option>
                    <option value="webm">WebM</option>
                  </select>
                </div>
              </div>
              <div className="checkbox-group">
                <input
                  type="checkbox"
                  id="plEmbedSubtitles"
                  checked={plEmbedSubs}
                  onChange={(e) => setPlEmbedSubs(e.target.checked)}
                />
                <label htmlFor="plEmbedSubtitles">Embed Subtitles</label>
              </div>
            </div>
          )}

          {/* Buttons */}
          <div className="button-group">
            <button type="submit" className="btn btn-primary">
              Download Playlist
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleClearPlaylist}
            >
              Clear URL
            </button>
          </div>

          {/* Stats */}
          <div className="stats">
            <StatCard value={plStats.total} label="Total Items" />
            <StatCard value={plStats.completed} label="Completed" />
            <StatCard value={plStats.failed} label="Failed" />
          </div>
        </form>
      )}
    </div>
  );
}
