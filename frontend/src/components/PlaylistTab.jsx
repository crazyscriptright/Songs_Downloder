import React, { useState } from 'react';
import StatsCard from './StatsCard';
import { getApiBaseUrl } from '../config';

export default function PlaylistTab({ downloads, updateDownloads, downloadViaProxy }) {
  const [playlistUrl, setPlaylistUrl] = useState('');
  const [playlistType, setPlaylistType] = useState('audio');
  const [playlistItems, setPlaylistItems] = useState('all');
  const [customRange, setCustomRange] = useState('');
  const [audioFormat, setAudioFormat] = useState('mp3');
  const [audioQuality, setAudioQuality] = useState('0');
  const [embedThumbnail, setEmbedThumbnail] = useState(true);
  const [addMetadata, setAddMetadata] = useState(true);
  const [videoQuality, setVideoQuality] = useState('best');
  const [videoFPS, setVideoFPS] = useState('any');
  const [videoFormat, setVideoFormat] = useState('mkv');
  const [embedSubtitles, setEmbedSubtitles] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);

  const playlistVideos = downloads.filter((d) => d.isPlaylist);
  const total = playlistVideos.length;
  const completed = playlistVideos.filter((d) => d.status === 'complete').length;
  const failed = playlistVideos.filter((d) => d.status === 'error').length;

  const startPlaylistDownload = async () => {
    if (!playlistUrl.trim()) {
      alert('Please enter a playlist URL');
      return;
    }

    if (isDownloading) {
      return;
    }

    let playlistItemsRange = '';
    if (playlistItems === 'custom') {
      const range = customRange.trim();
      if (range) {
        const validRange = /^(\d+|\d+-\d+)(,(\d+|\d+-\d+))*$/;
        if (!validRange.test(range)) {
          alert('Invalid playlist range format. Use formats like: 1-5, 1,3,5, or 1-3,5-7');
          return;
        }
        playlistItemsRange = range;
      }
    }

    setIsDownloading(true);

    try {
      console.log('📋 Extracting playlist videos...');
      const extractResponse = await fetch(`${getApiBaseUrl()}/extract_playlist`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: playlistUrl,
          playlistItems: playlistItemsRange,
        }),
      });

      const extractData = await extractResponse.json();

      if (!extractResponse.ok || !extractData.success) {
        throw new Error(extractData.error || 'Failed to extract playlist');
      }

      const videos = extractData.videos;
      console.log(`✅ Extracted ${videos.length} videos from playlist`);

      if (videos.length === 0) {
        alert('No videos found in playlist');
        setIsDownloading(false);
        return;
      }

      const format = playlistType === 'video' ? videoQuality : 'mp3';
      const quality = playlistType === 'audio' ? audioQuality : null;

      const newDownloads = videos.map((video, index) => ({
        url: video.url,
        title: video.title,
        status: 'queued',
        progress: 0,
        downloadId: `playlist_${Date.now()}_${index}`,
        isPlaylist: true,
        format: format,
        quality: quality,
      }));

      updateDownloads([...downloads, ...newDownloads]);

      // Download videos sequentially
      for (let i = 0; i < videos.length; i++) {
        const video = videos[i];
        const downloadItem = newDownloads[i];

        try {
          console.log(`⬇️ Downloading ${i + 1}/${videos.length}: ${video.title}`);

          updateDownloads((prev) =>
            prev.map((d) =>
              d.downloadId === downloadItem.downloadId
                ? { ...d, status: 'downloading', progress: 0 }
                : d
            )
          );

          await downloadViaProxy(
            video.url,
            video.title,
            downloadItem.downloadId,
            format,
            quality
          );

          console.log(`✅ Completed ${i + 1}/${videos.length}: ${video.title}`);
        } catch (error) {
          console.error(`❌ Failed to download ${video.title}:`, error);
        }
      }

      console.log('🎉 Playlist download completed!');
      setIsDownloading(false);
    } catch (error) {
      console.error('Playlist download error:', error);
      alert(`Error: ${error.message}`);
      setIsDownloading(false);
    }
  };

  const clearPlaylist = () => {
    setPlaylistUrl('');
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
          Playlist Downloader
        </h2>
        <p className="text-sm mb-4" style={{ color: 'var(--text-tertiary)' }}>
          Download entire playlists from YouTube with advanced options
        </p>

        <div className="mb-5">
          <label className="block mb-2 font-semibold" style={{ color: 'var(--text-secondary)' }}>
            Playlist URL
          </label>
          <input
            type="text"
            value={playlistUrl}
            onChange={(e) => setPlaylistUrl(e.target.value)}
            placeholder="https://www.youtube.com/playlist?list=..."
            className="w-full p-3 rounded-lg border-2 text-base transition-all"
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
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-5">
          <div>
            <label className="block mb-2 font-semibold" style={{ color: 'var(--text-secondary)' }}>
              Download Type
            </label>
            <select
              value={playlistType}
              onChange={(e) => setPlaylistType(e.target.value)}
              className="w-full p-3 rounded-lg border-2 text-base transition-all"
              style={{
                background: 'var(--bg-primary)',
                borderColor: 'var(--border-color)',
                color: 'var(--text-primary)',
              }}
            >
              <option value="audio">Audio Only</option>
              <option value="video">Video</option>
            </select>
          </div>

          <div>
            <label className="block mb-2 font-semibold" style={{ color: 'var(--text-secondary)' }}>
              Playlist Items
            </label>
            <select
              value={playlistItems}
              onChange={(e) => setPlaylistItems(e.target.value)}
              className="w-full p-3 rounded-lg border-2 text-base transition-all"
              style={{
                background: 'var(--bg-primary)',
                borderColor: 'var(--border-color)',
                color: 'var(--text-primary)',
              }}
            >
              <option value="all">All Items</option>
              <option value="custom">Custom Range</option>
            </select>
          </div>
        </div>

        {playlistItems === 'custom' && (
          <div className="mb-5">
            <label className="block mb-2 font-semibold" style={{ color: 'var(--text-secondary)' }}>
              Custom Range (e.g., 1-5, 10, 15-20)
            </label>
            <input
              type="text"
              value={customRange}
              onChange={(e) => setCustomRange(e.target.value)}
              placeholder="1-5,10,15-20"
              className="w-full p-3 rounded-lg border-2 text-base transition-all"
              style={{
                background: 'var(--bg-primary)',
                borderColor: 'var(--border-color)',
                color: 'var(--text-primary)',
              }}
            />
          </div>
        )}

        {/* Audio Options */}
        {playlistType === 'audio' && (
          <div className="mb-5">
            <h3 className="text-lg font-semibold mb-4" style={{ color: 'var(--text-secondary)' }}>
              Audio Options
            </h3>
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

            <label className="flex items-center gap-3 mb-4 cursor-pointer">
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
          </div>
        )}

        {/* Video Options */}
        {playlistType === 'video' && (
          <div className="mb-5">
            <h3 className="text-lg font-semibold mb-4" style={{ color: 'var(--text-secondary)' }}>
              Video Options
            </h3>
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
                <label className="block mb-2 font-semibold" style={{ color: 'var(--text-secondary)' }}>
                  Frame Rate
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
                  <option value="any">Any FPS</option>
                  <option value="60">60 FPS</option>
                  <option value="30">30 FPS</option>
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
                  <option value="mkv">MKV</option>
                  <option value="mp4">MP4</option>
                  <option value="webm">WebM</option>
                </select>
              </div>
            </div>

            <label className="flex items-center gap-3 mb-4 cursor-pointer">
              <input
                type="checkbox"
                checked={embedSubtitles}
                onChange={(e) => setEmbedSubtitles(e.target.checked)}
                className="w-5 h-5"
              />
              <span className="font-medium" style={{ color: 'var(--text-secondary)' }}>
                Embed Subtitles
              </span>
            </label>
          </div>
        )}

        <div className="flex gap-4 mt-5">
          <button
            onClick={startPlaylistDownload}
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
            Download Playlist
          </button>
          <button
            onClick={clearPlaylist}
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
            Clear URL
          </button>
        </div>

        <div className="grid grid-cols-3 gap-4 mt-5">
          <StatsCard value={total} label="Total Items" />
          <StatsCard value={completed} label="Completed" />
          <StatsCard value={failed} label="Failed" />
        </div>
      </div>
    </div>
  );
}