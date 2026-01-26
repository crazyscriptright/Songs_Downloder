import React, { useState } from 'react';
import StatsCard from './StatsCard';
import DownloadItem from './DownloadItem';
import { getApiBaseUrl } from '../config';

export default function BulkUrlsTab({ downloads, updateDownloads, autoDownloadedIds }) {
  const [urlsText, setUrlsText] = useState('');
  const [downloadType, setDownloadType] = useState('music');
  const [audioFormat, setAudioFormat] = useState('mp3');
  const [audioQuality, setAudioQuality] = useState('0');
  const [embedThumbnail, setEmbedThumbnail] = useState(true);
  const [videoQuality, setVideoQuality] = useState('1080');
  const [videoFPS, setVideoFPS] = useState('30');
  const [videoFormat, setVideoFormat] = useState('mkv');
  const [embedSubs, setEmbedSubs] = useState(true);
  const [addMetadata, setAddMetadata] = useState(true);
  const [isDownloading, setIsDownloading] = useState(false);

  const urls = urlsText.split('\n').map((url) => url.trim()).filter((url) => url.length > 0);
  const completed = downloads.filter((d) => d.status === 'complete').length;
  const failed = downloads.filter((d) => d.status === 'error').length;

  const startBulkDownload = async () => {
    if (urls.length === 0) {
      alert('Please enter at least one URL');
      return;
    }

    if (isDownloading) {
      alert('Bulk download already in progress. Please wait.');
      return;
    }

    setIsDownloading(true);

    const isVideoMode = downloadType === 'video';
    const options = {
      keepVideo: isVideoMode,
      addMetadata,
    };

    if (isVideoMode) {
      options.videoQuality = videoQuality;
      options.videoFPS = videoFPS;
      options.videoFormat = videoFormat;
      options.embedSubtitles = embedSubs;
    } else {
      options.audioFormat = audioFormat;
      options.audioQuality = audioQuality;
      options.embedThumbnail = embedThumbnail;
    }

    const bulkDownloads = urls.map((url, index) => ({
      url,
      title: `Item ${index + 1}`,
      status: 'queued',
      progress: 0,
      error: null,
      downloadId: null,
    }));

    updateDownloads(bulkDownloads);

    try {
      const response = await fetch(`${getApiBaseUrl()}/bulk_download`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ urls, advancedOptions: options }),
      });

      const data = await response.json();

      if (data.bulk_id) {
        pollBulkProgress(data.bulk_id);
      } else {
        setIsDownloading(false);
      }
    } catch (error) {
      console.error('Bulk download error:', error);
      setIsDownloading(false);
      alert(`Error: ${error.message}`);
    }
  };

  const pollBulkProgress = async (bulkId) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`${getApiBaseUrl()}/bulk_status/${bulkId}`);
        const data = await response.json();

        if (!response.ok && data.error) {
          if (data.error.toLowerCase().includes('not found')) {
            return;
          }
        }

        if (data.error && data.error.toLowerCase().includes('not found')) {
          return;
        }

        if (data.downloads) {
          updateDownloads(data.downloads);

          const allDone = data.downloads.every(
            (d) => d.status === 'complete' || d.status === 'error'
          );

          if (allDone) {
            clearInterval(pollInterval);
            setIsDownloading(false);
          }
        }
      } catch (error) {
        console.error('Poll error:', error);
      }
    }, 3000);
  };

  const clearUrls = () => {
    setUrlsText('');
    updateDownloads([]);
  };

  return (
    <div>
      <div
        className="rounded-2xl p-10 mb-8 border"
        style={{
          background: 'var(--bg-card)',
          borderColor: 'var(--border-color)',
          boxShadow: '0 10px 30px rgba(0, 0, 0, 0.2)',
        }}
      >
        <h2 className="text-2xl font-bold mb-5" style={{ color: 'var(--text-primary)' }}>
          Bulk URL Downloader
        </h2>
        <p className="text-sm mb-4" style={{ color: 'var(--text-tertiary)' }}>
          Paste one URL per line. Downloads will be processed sequentially.
        </p>

        <textarea
          value={urlsText}
          onChange={(e) => setUrlsText(e.target.value)}
          className="w-full min-h-[300px] p-4 rounded-lg border-2 resize-y mb-4 transition-all font-mono text-sm"
          style={{
            background: 'var(--bg-primary)',
            borderColor: 'var(--border-color)',
            color: 'var(--text-primary)',
          }}
          onFocus={(e) => {
            e.currentTarget.style.borderColor = 'var(--accent-color)';
            e.currentTarget.style.boxShadow = '0 0 0 3px var(--shadow-color)';
          }}
          onBlur={(e) => {
            e.currentTarget.style.borderColor = 'var(--border-color)';
            e.currentTarget.style.boxShadow = 'none';
          }}
          placeholder="https://www.youtube.com/watch?v=...&#10;https://soundcloud.com/...&#10;https://www.jiosaavn.com/song/...&#10;&#10;Paste your URLs here (one per line)"
        />

        {/* Download Type Selector */}
        <div className="mb-5">
          <label className="block mb-3 font-semibold" style={{ color: 'var(--text-primary)' }}>
            Download Type (YouTube only):
          </label>
          <div className="flex gap-4">
            <label className="flex items-center cursor-pointer">
              <input
                type="radio"
                name="downloadType"
                value="music"
                checked={downloadType === 'music'}
                onChange={(e) => setDownloadType(e.target.value)}
                className="mr-2"
              />
              <span>🎵 Music (Audio Only)</span>
            </label>
            <label className="flex items-center cursor-pointer">
              <input
                type="radio"
                name="downloadType"
                value="video"
                checked={downloadType === 'video'}
                onChange={(e) => setDownloadType(e.target.value)}
                className="mr-2"
              />
              <span>🎬 Video</span>
            </label>
          </div>
        </div>

        {/* Audio Options */}
        {downloadType === 'music' && (
          <div className="mb-5">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-4">
              <div>
                <label className="block mb-2 font-semibold" style={{ color: 'var(--text-secondary)' }}>
                  Audio Format
                </label>
                <select
                  value={audioFormat}
                  onChange={(e) => setAudioFormat(e.target.value)}
                  className="w-full p-3 rounded-lg border-2 text-base transition-all"
                  style={{
                    background: 'var(--bg-primary)',
                    borderColor: 'var(--border-color)',
                    color: 'var(--text-primary)',
                  }}
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
                <label className="block mb-2 font-semibold" style={{ color: 'var(--text-secondary)' }}>
                  Audio Quality
                </label>
                <select
                  value={audioQuality}
                  onChange={(e) => setAudioQuality(e.target.value)}
                  className="w-full p-3 rounded-lg border-2 text-base transition-all"
                  style={{
                    background: 'var(--bg-primary)',
                    borderColor: 'var(--border-color)',
                    color: 'var(--text-primary)',
                  }}
                >
                  <option value="0">Best (0)</option>
                  <option value="2">High (2)</option>
                  <option value="5">Medium (5)</option>
                  <option value="9">Low (9)</option>
                </select>
              </div>
            </div>

            <label className="flex items-center gap-3 mb-4 cursor-pointer">
              <input
                type="checkbox"
                checked={embedThumbnail}
                onChange={(e) => setEmbedThumbnail(e.target.checked)}
                className="w-5 h-5"
              />
              <span className="font-medium" style={{ color: 'var(--text-secondary)' }}>
                Embed Thumbnail
              </span>
            </label>
          </div>
        )}

        {/* Video Options */}
        {downloadType === 'video' && (
          <div className="mb-5">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-4">
              <div>
                <label className="block mb-2 font-semibold" style={{ color: 'var(--text-secondary)' }}>
                  Video Quality
                </label>
                <select
                  value={videoQuality}
                  onChange={(e) => setVideoQuality(e.target.value)}
                  className="w-full p-3 rounded-lg border-2 text-base transition-all"
                  style={{
                    background: 'var(--bg-primary)',
                    borderColor: 'var(--border-color)',
                    color: 'var(--text-primary)',
                  }}
                >
                  <option value="2160">4K (2160p)</option>
                  <option value="1440">2K (1440p)</option>
                  <option value="1080">Full HD (1080p)</option>
                  <option value="720">HD (720p)</option>
                  <option value="480">SD (480p)</option>
                  <option value="360">Low (360p)</option>
                </select>
              </div>

              <div>
                <label className="block mb-2 font-semibold" style={{ color: 'var(--text-secondary)' }}>
                  Video FPS
                </label>
                <select
                  value={videoFPS}
                  onChange={(e) => setVideoFPS(e.target.value)}
                  className="w-full p-3 rounded-lg border-2 text-base transition-all"
                  style={{
                    background: 'var(--bg-primary)',
                    borderColor: 'var(--border-color)',
                    color: 'var(--text-primary)',
                  }}
                >
                  <option value="60">60 FPS</option>
                  <option value="30">30 FPS</option>
                  <option value="24">24 FPS</option>
                </select>
              </div>

              <div>
                <label className="block mb-2 font-semibold" style={{ color: 'var(--text-secondary)' }}>
                  Video Format
                </label>
                <select
                  value={videoFormat}
                  onChange={(e) => setVideoFormat(e.target.value)}
                  className="w-full p-3 rounded-lg border-2 text-base transition-all"
                  style={{
                    background: 'var(--bg-primary)',
                    borderColor: 'var(--border-color)',
                    color: 'var(--text-primary)',
                  }}
                >
                  <option value="mkv">MKV (Best Quality)</option>
                  <option value="mp4">MP4 (Compatible)</option>
                  <option value="webm">WebM</option>
                </select>
              </div>
            </div>

            <label className="flex items-center gap-3 mb-4 cursor-pointer">
              <input
                type="checkbox"
                checked={embedSubs}
                onChange={(e) => setEmbedSubs(e.target.checked)}
                className="w-5 h-5"
              />
              <span className="font-medium" style={{ color: 'var(--text-secondary)' }}>
                Embed Subtitles
              </span>
            </label>
          </div>
        )}

        {/* Common Options */}
        <label className="flex items-center gap-3 mb-5 cursor-pointer">
          <input
            type="checkbox"
            checked={addMetadata}
            onChange={(e) => setAddMetadata(e.target.checked)}
            className="w-5 h-5"
          />
          <span className="font-medium" style={{ color: 'var(--text-secondary)' }}>
            Add Metadata
          </span>
        </label>

        <div className="flex gap-4 mt-5">
          <button
            onClick={startBulkDownload}
            disabled={isDownloading}
            className="flex-1 px-10 py-4 text-lg font-semibold border-0 rounded-lg cursor-pointer transition-all text-white disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ background: 'var(--gradient-secondary)' }}
            onMouseEnter={(e) => {
              if (!isDownloading) {
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = '0 8px 20px var(--shadow-color)';
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = 'none';
            }}
          >
            Start Bulk Download
          </button>
          <button
            onClick={clearUrls}
            className="flex-1 px-10 py-4 text-lg font-semibold rounded-lg cursor-pointer transition-all border-2"
            style={{
              background: 'var(--bg-secondary)',
              color: 'var(--text-secondary)',
              borderColor: 'var(--border-color)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--border-color)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'var(--bg-secondary)';
            }}
          >
            Clear URLs
          </button>
        </div>

        <div className="grid grid-cols-3 gap-4 mt-5">
          <StatsCard value={urls.length} label="Total URLs" />
          <StatsCard value={completed} label="Completed" />
          <StatsCard value={failed} label="Failed" />
        </div>
      </div>

      <div className="mt-8">
        {downloads.map((download, index) => (
          <DownloadItem
            key={index}
            download={download}
            index={index}
            autoDownloadedIds={autoDownloadedIds}
          />
        ))}
      </div>
    </div>
  );
}