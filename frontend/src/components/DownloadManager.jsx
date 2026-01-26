import React from 'react';
import { getApiBaseUrl } from '../config';

export default function DownloadManager({ downloads, isVisible, onToggle }) {
  const activeDownloads = downloads.filter(
    (d) => d.status === 'downloading' || d.status === 'queued' || d.status === 'complete'
  );

  return (
    <>
      {/* Floating Download Manager Panel */}
      <div
        className={`fixed top-5 right-5 w-96 max-h-[70vh] rounded-xl border shadow-2xl z-[1000] overflow-hidden ${
          isVisible ? 'flex flex-col' : 'hidden'
        }`}
        style={{
          background: 'var(--bg-card)',
          borderColor: 'var(--border-color)',
        }}
      >
        <div
          className="p-4 flex justify-between items-center rounded-t-xl"
          style={{ background: 'var(--accent-color)', color: 'white' }}
        >
          <h3 className="text-lg font-semibold">Downloads</h3>
          <button
            onClick={onToggle}
            className="px-3 py-1 rounded text-sm cursor-pointer transition-all"
            style={{ background: 'rgba(255, 255, 255, 0.2)' }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.3)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.2)';
            }}
          >
            Close
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-3">
          {activeDownloads.length === 0 ? (
            <div className="text-center py-5" style={{ color: 'var(--text-tertiary)' }}>
              No active downloads
            </div>
          ) : (
            activeDownloads.map((download, index) => {
              const borderLeftColor =
                download.status === 'complete'
                  ? 'var(--success-color)'
                  : download.status === 'downloading'
                  ? 'var(--info-color)'
                  : download.status === 'error'
                  ? 'var(--error-color)'
                  : 'transparent';

              const managerTitle =
                download.title && !download.title.startsWith('Item ')
                  ? download.title
                  : download.url;

              return (
                <div
                  key={index}
                  className="rounded-lg p-3 mb-3 border"
                  style={{
                    background: 'var(--bg-secondary)',
                    borderColor: 'var(--border-color)',
                    borderLeft: `4px solid ${borderLeftColor}`,
                  }}
                >
                  <div
                    className="font-semibold text-sm mb-2 overflow-hidden text-ellipsis whitespace-nowrap"
                    style={{ color: 'var(--text-primary)' }}
                  >
                    {managerTitle}
                  </div>

                  <div
                    className="w-full h-1.5 rounded overflow-hidden mb-2"
                    style={{ background: 'var(--border-color)' }}
                  >
                    <div
                      className="h-full transition-all duration-300"
                      style={{
                        width: `${download.progress}%`,
                        background: 'var(--accent-color)',
                      }}
                    />
                  </div>

                  <div
                    className="text-xs flex justify-between items-center"
                    style={{ color: 'var(--text-tertiary)' }}
                  >
                    <span>
                      {download.status === 'complete'
                        ? 'Complete'
                        : download.status === 'error'
                        ? 'Failed'
                        : `${Math.round(download.progress)}%`}
                    </span>
                    {download.status === 'complete' && download.download_url && (
                      <a
                        href={
                          download.download_url.startsWith('http')
                            ? download.download_url
                            : `${getApiBaseUrl()}${download.download_url}`
                        }
                        download
                        className="px-3 py-1 rounded text-xs font-semibold text-white transition-all"
                        style={{ background: 'var(--accent-color)' }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.background = 'var(--accent-secondary)';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = 'var(--accent-color)';
                        }}
                      >
                        Download
                      </a>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Toggle Button */}
      <button
        onClick={onToggle}
        className="fixed bottom-8 right-8 w-15 h-15 rounded-full border-0 cursor-pointer flex items-center justify-center text-2xl text-white transition-all z-[999]"
        style={{
          background: 'var(--accent-color)',
          boxShadow: '0 4px 20px var(--shadow-color)',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'scale(1.1)';
          e.currentTarget.style.boxShadow = '0 6px 30px var(--shadow-color)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'scale(1)';
          e.currentTarget.style.boxShadow = '0 4px 20px var(--shadow-color)';
        }}
      >
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="7 10 12 15 17 10"></polyline>
          <line x1="12" y1="15" x2="12" y2="3"></line>
        </svg>
        {activeDownloads.length > 0 && (
          <span
            className="absolute -top-1 -right-1 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white"
            style={{ background: 'var(--error-color)' }}
          >
            {activeDownloads.length}
          </span>
        )}
      </button>
    </>
  );
}