import React, { useState } from 'react';
import { getApiBaseUrl } from '../config';

export default function SongCard({ song, source, downloads, updateDownloads }) {
  const [isDownloading, setIsDownloading] = useState(false);

  const handleDownload = async () => {
    setIsDownloading(true);

    try {
      const downloadId = `download_${Date.now()}`;
      const newDownload = {
        url: song.url,
        title: song.title,
        status: 'downloading',
        progress: 0,
        downloadId,
      };

      updateDownloads([...downloads, newDownload]);

      const response = await fetch(`${getApiBaseUrl()}/download`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: song.url,
          title: song.title,
        }),
      });

      const data = await response.json();

      if (data.download_id) {
        // Poll for download status
        pollDownloadStatus(data.download_id, downloadId);
      }
    } catch (error) {
      console.error('Download error:', error);
      setIsDownloading(false);
    }
  };

  const pollDownloadStatus = async (backendId, downloadId) => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`${getApiBaseUrl()}/download_status/${backendId}`);
        const data = await response.json();

        if (data.status === 'complete') {
          clearInterval(interval);
          setIsDownloading(false);

          updateDownloads((prev) =>
            prev.map((d) =>
              d.downloadId === downloadId
                ? { ...d, status: 'complete', progress: 100, download_url: data.download_url }
                : d
            )
          );

          // Auto-download
          if (data.download_url) {
            const link = document.createElement('a');
            link.href = data.download_url.startsWith('http')
              ? data.download_url
              : `${getApiBaseUrl()}${data.download_url}`;
            link.download = song.title;
            link.click();
          }
        } else if (data.status === 'error') {
          clearInterval(interval);
          setIsDownloading(false);
          updateDownloads((prev) =>
            prev.map((d) => (d.downloadId === downloadId ? { ...d, status: 'error', error: data.error } : d))
          );
        } else {
          // Update progress
          updateDownloads((prev) =>
            prev.map((d) => (d.downloadId === downloadId ? { ...d, progress: data.progress || 0 } : d))
          );
        }
      } catch (error) {
        console.error('Poll error:', error);
      }
    }, 3000);
  };

  return (
    <div
      className="rounded-lg p-4 border-2 transition-all cursor-pointer"
      style={{
        background: 'var(--bg-card)',
        borderColor: 'var(--border-color)',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'translateY(-5px)';
        e.currentTarget.style.borderColor = 'var(--accent-color)';
        e.currentTarget.style.boxShadow = '0 5px 20px var(--shadow-color)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'translateY(0)';
        e.currentTarget.style.borderColor = 'var(--border-color)';
        e.currentTarget.style.boxShadow = 'none';
      }}
    >
      {/* Thumbnail */}
      {song.thumbnail && (
        <img
          src={song.thumbnail}
          alt={song.title}
          className="w-full rounded-lg mb-3"
          style={{ aspectRatio: source === 'ytvideo' ? '16/9' : '1/1', objectFit: 'cover' }}
        />
      )}

      {/* Title */}
      <h3
        className="font-bold text-base mb-1 overflow-hidden"
        style={{
          color: 'var(--text-primary)',
          display: '-webkit-box',
          WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical',
        }}
      >
        {song.title}
      </h3>

      {/* Artist */}
      {song.artist && (
        <p
          className="text-sm mb-3 overflow-hidden"
          style={{
            color: 'var(--text-secondary)',
            display: '-webkit-box',
            WebkitLineClamp: 1,
            WebkitBoxOrient: 'vertical',
          }}
        >
          {song.artist}
        </p>
      )}

      {/* Metadata */}
      {(song.duration || song.views) && (
        <div className="flex gap-3 text-xs mb-3" style={{ color: 'var(--text-tertiary)' }}>
          {song.duration && <span>⏱ {song.duration}</span>}
          {song.views && <span>👁 {song.views}</span>}
        </div>
      )}

      {/* Download Button */}
      <button
        onClick={handleDownload}
        disabled={isDownloading}
        className="w-full px-4 py-2 rounded-lg font-bold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        style={{
          background: isDownloading ? 'var(--warning-color)' : 'var(--accent-color)',
          color: isDownloading ? '#000' : 'var(--bg-primary)',
          border: `1px solid ${isDownloading ? 'var(--warning-color)' : 'var(--accent-color)'}`,
        }}
        onMouseEnter={(e) => {
          if (!isDownloading) {
            e.currentTarget.style.transform = 'scale(1.05)';
            e.currentTarget.style.boxShadow = '0 4px 8px var(--shadow-color)';
          }
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'scale(1)';
          e.currentTarget.style.boxShadow = 'none';
        }}
      >
        {isDownloading ? 'Downloading...' : 'Download'}
      </button>
    </div>
  );
}