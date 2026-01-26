import React, { useState } from 'react';
import SongCard from './SongCard';

export default function SearchResults({ results, downloads, updateDownloads, downloadViaProxy, autoDownloadedIds }) {
  const [activeSource, setActiveSource] = useState(null);

  if (!results) return null;

  // Handle direct URL results
  if (results.query_type === 'url' && results.direct_url) {
    const urlData = results.direct_url[0];
    
    // Check if already downloading or downloaded
    const existingDownload = Object.values(downloads).find(
      d => d.url === urlData.url
    );
    
    const handleDownload = () => {
      if (existingDownload) return;
      
      // Create a download using the updateDownloads function
      const downloadId = `download_${Date.now()}`;
      updateDownloads(downloadId, {
        status: 'queued',
        title: urlData.title || 'Unknown Title',
        url: urlData.url,
        progress: 0,
        speed: '0 KB/s',
        eta: 'Waiting...'
      });
    };
    
    return (
      <div className="max-w-[900px] mx-auto">
        <div
          className="rounded-2xl p-10 border-2"
          style={{
            background: 'var(--bg-card)',
            borderColor: 'var(--accent-color)',
          }}
        >
          <h2 className="text-2xl font-bold mb-5" style={{ color: 'var(--accent-color)' }}>
            {urlData.source} - Ready to Download
          </h2>
          <div className="mb-5">
            <h3 className="text-xl font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>
              {urlData.title || 'Unknown Title'}
            </h3>
            <p style={{ color: 'var(--text-secondary)' }}>
              <strong>Source:</strong> {urlData.source}
            </p>
            <p className="text-sm mt-2" style={{ color: 'var(--text-tertiary)' }}>
              <a href={urlData.url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent-color)' }}>
                {urlData.url}
              </a>
            </p>
          </div>
          <button
            onClick={handleDownload}
            disabled={!!existingDownload}
            className="px-8 py-3 rounded-lg font-semibold text-white transition-all gradient-secondary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {existingDownload 
              ? existingDownload.status === 'completed' 
                ? '✓ Downloaded' 
                : existingDownload.status === 'downloading'
                ? 'Downloading...'
                : existingDownload.status === 'error'
                ? '✗ Failed'
                : 'In Queue'
              : 'Download'
            }
          </button>
        </div>
      </div>
    );
  }

  // Multi-source results
  const sources = [];
  if (results.jiosaavn?.length > 0) sources.push({ id: 'jiosaavn', name: 'JioSaavn', data: results.jiosaavn });
  if (results.ytmusic?.length > 0) sources.push({ id: 'ytmusic', name: 'YouTube Music', data: results.ytmusic });
  if (results.soundcloud?.length > 0) sources.push({ id: 'soundcloud', name: 'SoundCloud', data: results.soundcloud });
  if (results.ytvideo?.length > 0) sources.push({ id: 'ytvideo', name: 'YouTube Videos', data: results.ytvideo });

  if (sources.length === 0) {
    return (
      <div className="text-center py-16" style={{ color: 'var(--text-secondary)' }}>
        <div className="text-6xl mb-5">∅</div>
        <h3 className="text-2xl font-bold mb-2">No results found</h3>
        <p>Try a different search query</p>
      </div>
    );
  }

  const currentSource = activeSource || sources[0].id;
  const currentData = sources.find((s) => s.id === currentSource)?.data || [];

  return (
    <div>
      {/* Source Navigation */}
      <div
        className="flex gap-4 mb-8 justify-center flex-wrap rounded-2xl p-4"
        style={{ background: 'rgba(255, 255, 255, 0.05)' }}
      >
        {sources.map((source) => (
          <button
            key={source.id}
            onClick={() => setActiveSource(source.id)}
            className={`px-6 py-3 text-base font-bold rounded-lg cursor-pointer transition-all border-2 ${
              currentSource === source.id ? '' : ''
            }`}
            style={
              currentSource === source.id
                ? { background: 'var(--accent-color)', color: 'var(--bg-primary)', borderColor: 'var(--accent-color)' }
                : { background: 'var(--bg-card)', color: 'var(--text-secondary)', borderColor: 'var(--border-color)' }
            }
            onMouseEnter={(e) => {
              if (currentSource !== source.id) {
                e.currentTarget.style.background = 'var(--bg-secondary)';
                e.currentTarget.style.transform = 'translateY(-2px)';
              }
            }}
            onMouseLeave={(e) => {
              if (currentSource !== source.id) {
                e.currentTarget.style.background = 'var(--bg-card)';
                e.currentTarget.style.transform = 'translateY(0)';
              }
            }}
          >
            {source.name} <span className="ml-2 px-2 py-1 rounded-lg text-sm" style={{ background: 'rgba(0,0,0,0.3)' }}>{source.data.length}</span>
          </button>
        ))}
      </div>

      {/* Results Grid */}
      <div className="p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 lg:p-4 xl:grid-cols-4 xl:p-4 gap-4">
        {currentData.map((song, index) => (
          <SongCard
            key={index}
            song={song}
            source={currentSource}
            downloads={downloads}
            updateDownloads={updateDownloads}
            downloadViaProxy={downloadViaProxy}
            autoDownloadedIds={autoDownloadedIds}
          />
        ))}
      </div>
    </div>
  );
}