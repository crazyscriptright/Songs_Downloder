import { useState, useEffect, useCallback } from 'react';
import { getApiBaseUrl } from '../config';

export function useDownloadManager() {
  const [downloads, setDownloads] = useState([]);
  const [autoDownloadedIds] = useState(new Set());

  // Load downloads from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem('allDownloads');
      if (stored) {
        const allDownloads = JSON.parse(stored);
        const downloadArray = Object.values(allDownloads).map((download) => ({
          url: download.url,
          title: download.title,
          status: download.status,
          progress: download.progress || 0,
          error: download.error || null,
          downloadId: download.id,
          download_url: download.download_url || null,
        }));

        downloadArray.forEach((download) => {
          if (download.status === 'complete') {
            const uniqueId = download.downloadId || download.url;
            autoDownloadedIds.add(uniqueId);
          }
        });

        setDownloads(downloadArray);
      }
    } catch (e) {
      console.error('Error loading downloads from storage:', e);
    }
  }, [autoDownloadedIds]);

  // Save downloads to localStorage
  const saveDownloads = useCallback((downloadList) => {
    try {
      const allDownloads = {};
      downloadList.forEach((download) => {
        if (download.downloadId) {
          allDownloads[download.downloadId] = {
            id: download.downloadId,
            title: download.title,
            url: download.url,
            status: download.status,
            progress: download.progress || 0,
            error: download.error || null,
            download_url: download.download_url || null,
          };
        }
      });
      localStorage.setItem('allDownloads', JSON.stringify(allDownloads));
    } catch (e) {
      console.error('Error saving downloads to storage:', e);
    }
  }, []);

  // Update downloads and save
  const updateDownloads = useCallback((newDownloads) => {
    setDownloads(newDownloads);
    saveDownloads(newDownloads);
  }, [saveDownloads]);

  // Download via proxy API
  const downloadViaProxy = useCallback(async (url, title, downloadId, format = 'mp3', quality = '360') => {
    try {
      const encodedUrl = encodeURIComponent(url);
      const downloadUrl = `${getApiBaseUrl()}/proxy/download?format=${format}&url=${encodedUrl}&quality=${quality}`;

      const response = await fetch(downloadUrl);
      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || 'Proxy download failed');
      }

      const progressId = data.id;
      let lastProgressPercent = 0;

      // Poll for progress
      const pollInterval = setInterval(async () => {
        try {
          const progressResponse = await fetch(
            `${getApiBaseUrl()}/proxy/progress?progress_id=${progressId}`
          );
          const progressData = await progressResponse.json();

          if (progressData.success) {
            const rawProgress = progressData.progress || 0;
            const progressPercent = Math.min(Math.round((rawProgress / 1000) * 100), 100);

            if (progressPercent > lastProgressPercent) {
              lastProgressPercent = progressPercent;

              setDownloads((prev) => {
                const updated = prev.map((d) =>
                  d.downloadId === downloadId
                    ? {
                        ...d,
                        progress: progressPercent,
                        status: progressPercent >= 100 ? 'complete' : 'downloading',
                      }
                    : d
                );
                saveDownloads(updated);
                return updated;
              });
            }

            if (progressData.download_url) {
              clearInterval(pollInterval);

              if (progressData.download_url === null || progressData.download_url === 'null') {
                throw new Error('Download failed: Code 1805 - Download URL is null');
              }

              setDownloads((prev) => {
                const updated = prev.map((d) =>
                  d.downloadId === downloadId
                    ? {
                        ...d,
                        status: 'complete',
                        progress: 100,
                        download_url: progressData.download_url,
                      }
                    : d
                );
                saveDownloads(updated);
                return updated;
              });

              // Auto-download the file
              const fileUrl = `${getApiBaseUrl()}/proxy/file?file_url=${encodeURIComponent(
                progressData.download_url
              )}`;
              const link = document.createElement('a');
              link.href = fileUrl;
              link.download = `${title}.${format}`;
              document.body.appendChild(link);
              link.click();
              document.body.removeChild(link);
            }
          } else if (progressData.error) {
            clearInterval(pollInterval);
            throw new Error(progressData.error);
          }
        } catch (pollError) {
          console.error('Progress polling error:', pollError);
          clearInterval(pollInterval);

          setDownloads((prev) => {
            const updated = prev.map((d) =>
              d.downloadId === downloadId
                ? {
                    ...d,
                    status: 'error',
                    error: pollError.message || 'Progress polling failed',
                  }
                : d
            );
            saveDownloads(updated);
            return updated;
          });
        }
      }, 3000);
    } catch (error) {
      console.error(`❌ Proxy download error: ${error.message}`);

      setDownloads((prev) => {
        const updated = prev.map((d) =>
          d.downloadId === downloadId
            ? {
                ...d,
                status: 'error',
                error: error.message || 'Proxy download failed',
              }
            : d
        );
        saveDownloads(updated);
        return updated;
      });

      throw error;
    }
  }, [saveDownloads]);

  return {
    downloads,
    updateDownloads,
    downloadViaProxy,
    autoDownloadedIds,
  };
}