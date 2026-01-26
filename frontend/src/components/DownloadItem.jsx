import React from 'react';
import { getApiBaseUrl } from '../config';

export default function DownloadItem({ download, index, autoDownloadedIds }) {
  const statusClass = `status-${download.status}`;
  const statusText = download.status.charAt(0).toUpperCase() + download.status.slice(1);

  const displayTitle =
    download.title && !download.title.startsWith('Item ') ? download.title : download.url;

  const borderLeftColor =
    download.status === 'downloading'
      ? 'var(--info-color)'
      : download.status === 'complete'
      ? 'var(--success-color)'
      : download.status === 'error'
      ? 'var(--error-color)'
      : 'transparent';

  // Auto-download completed files (only once per download)
  React.useEffect(() => {
    if (download.status === 'complete' && download.download_url) {
      const uniqueId = download.downloadId || download.download_id || download.url;

      if (!autoDownloadedIds.has(uniqueId)) {
        autoDownloadedIds.add(uniqueId);

        setTimeout(() => {
          const link = document.createElement('a');
          const downloadUrl = download.download_url.startsWith('http')
            ? download.download_url
            : `${getApiBaseUrl()}${download.download_url}`;
          link.href = downloadUrl;
          link.download = download.title || `download_${index + 1}`;
          link.style.display = 'none';
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
        }, 500 * index);
      }
    }
  }, [download, index, autoDownloadedIds]);

  return (
    <div
      className="rounded-lg p-4 mb-3 border"
      style={{
        background: 'var(--bg-secondary)',
        borderColor: 'var(--border-color)',
        borderLeft: `4px solid ${borderLeftColor}`,
      }}
    >
      <div className="flex justify-between items-center mb-3">
        <div className="font-semibold" style={{ color: 'var(--text-primary)' }}>
          {displayTitle}
        </div>
        <div
          className={`text-sm px-3 py-1 rounded font-semibold ${statusClass}`}
          style={{
            background:
              download.status === 'queued'
                ? 'rgba(167, 139, 250, 0.2)'
                : download.status === 'downloading'
                ? 'rgba(52, 211, 153, 0.2)'
                : download.status === 'complete'
                ? 'rgba(52, 211, 153, 0.2)'
                : 'rgba(248, 113, 113, 0.2)',
            color:
              download.status === 'queued'
                ? 'var(--info-color)'
                : download.status === 'downloading'
                ? 'var(--accent-color)'
                : download.status === 'complete'
                ? 'var(--success-color)'
                : 'var(--error-color)',
          }}
        >
          {statusText}
        </div>
      </div>

      <div
        className="w-full h-2 rounded overflow-hidden mb-2"
        style={{ background: 'var(--border-color)' }}
      >
        <div
          className="h-full rounded transition-all duration-300"
          style={{
            width: `${download.progress}%`,
            background: 'var(--accent-color)',
          }}
        />
      </div>

      <div className="text-sm" style={{ color: 'var(--text-tertiary)' }}>
        {download.error || download.speed || 'Waiting...'}
        {download.status === 'complete' && download.download_url && (
          <a
            href={
              download.download_url.startsWith('http')
                ? download.download_url
                : `${getApiBaseUrl()}${download.download_url}`
            }
            download
            className="inline-block mt-2 px-4 py-2 rounded font-semibold text-sm text-white transition-all hover:-translate-y-0.5"
            style={{ background: 'var(--accent-color)' }}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className="inline mr-1 align-middle"
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            Download File
          </a>
        )}
      </div>
    </div>
  );
}