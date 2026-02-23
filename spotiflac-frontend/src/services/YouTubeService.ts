import { getApiBaseUrl } from '@/config';
import type { ProxyProgressResponse } from '@/types';

/**
 * YouTube-specific helpers: URL conversion, iframe creation, and proxy download.
 */
export class YouTubeService {
  /** Create an embeddable YouTube iframe HTML string. */
  static createIframe(videoId: string, title = 'YouTube Video'): string {
    if (!videoId) return '';
    return `
      <div style="padding-bottom: 56.25%; position: relative;">
        <iframe
          width="100%" height="100%"
          src="https://www.youtube-nocookie.com/embed/${videoId}?modestbranding=1"
          frameborder="0"
          allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture; fullscreen"
          style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%;"
          title="${title}">
        </iframe>
      </div>
    `;
  }

  /**
   * Download a YouTube file via the backend proxy.
   * Triggers a browser save-as dialog when complete.
   */
  static async downloadFile(downloadUrl: string, title: string, format: string): Promise<void> {
    const API_BASE = getApiBaseUrl();
    const proxyUrl = `${API_BASE}/proxy/file?url=${encodeURIComponent(downloadUrl)}`;
    const response = await fetch(proxyUrl);
    if (!response.ok) throw new Error('Download failed');

    const blob = await response.blob();

    let filename = `${title}.${format}`;
    const contentDisposition = response.headers.get('Content-Disposition');
    if (contentDisposition?.includes('filename=')) {
      filename = contentDisposition.split('filename=')[1].replace(/"/g, '');
    }

    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  }

  /**
   * Initiate and poll a proxy API download for a YouTube video.
   * Returns true on success.
   */
  static async downloadViaProxy(
    videoUrl: string,
    title: string,
    format: string,
    audioQuality: string,
    onProgress: (percent: number, text: string) => void,
  ): Promise<string> {
    const API_BASE = getApiBaseUrl();
    const encodedUrl = encodeURIComponent(videoUrl);

    const isVideoFormat = ['8k', '4k', '2k', '1440', '1080', '720', '480', '360', '240', '144', 'best'].includes(format);

    let downloadUrl: string;
    if (isVideoFormat) {
      downloadUrl = `${API_BASE}/proxy/download?format=${format}&url=${encodedUrl}`;
    } else {
      downloadUrl = `${API_BASE}/proxy/download?format=${format}&url=${encodedUrl}&quality=${audioQuality}`;
    }

    const response = await fetch(downloadUrl);
    const data = await response.json();

    if (!response.ok || data.success === false) {
      throw new Error(data.message || 'Proxy API initiation failed');
    }

    const jobId = data.id as string;
    const maxAttempts = 60;
    let attempts = 0;
    let lastPercent = 0;

    return new Promise<string>((resolve, reject) => {
      const pollInterval = setInterval(async () => {
        attempts++;
        try {
          const progressResponse = await fetch(`${API_BASE}/proxy/progress?id=${jobId}`);
          const progressData: ProxyProgressResponse = await progressResponse.json();

          let percent: number;
          let statusText: string;

          if (progressData.progress < 100) {
            percent = Math.round((progressData.progress / 100) * 10);
            statusText = progressData.text || 'Initializing...';
          } else if (progressData.progress < 500) {
            percent = 10 + Math.round(((progressData.progress - 100) / 400) * 40);
            statusText = progressData.text || 'Downloading...';
          } else {
            percent = 50 + Math.round(((progressData.progress - 500) / 500) * 50);
            statusText = progressData.text || 'Converting...';
          }

          if (percent > lastPercent) {
            lastPercent = percent;
            onProgress(percent, statusText);
          }

          if (progressData.success === 1 && progressData.progress === 1000) {
            clearInterval(pollInterval);
            if (!progressData.download_url) {
              reject(new Error(progressData.text || 'No download URL provided'));
              return;
            }
            // Download the file
            await YouTubeService.downloadFile(progressData.download_url, title, format);
            resolve(progressData.download_url);
          } else if (attempts >= maxAttempts) {
            clearInterval(pollInterval);
            reject(new Error('Proxy API timeout'));
          }
        } catch (error) {
          clearInterval(pollInterval);
          reject(error);
        }
      }, 3000);
    });
  }
}