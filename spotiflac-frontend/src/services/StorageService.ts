import type { DownloadItem } from '@/types';

const DOWNLOADS_KEY = 'allDownloads';
const THEME_KEY = 'theme';

/**
 * Thin wrapper around localStorage for persisting app state.
 */
export class StorageService {
  /** Load all saved downloads from localStorage. */
  static loadDownloads(): Record<string, DownloadItem> {
    try {
      const stored = localStorage.getItem(DOWNLOADS_KEY);
      return stored ? JSON.parse(stored) : {};
    } catch (e) {
      console.error('Error loading downloads from storage:', e);
      return {};
    }
  }

  /** Persist downloads map to localStorage. */
  static saveDownloads(downloads: Record<string, DownloadItem>): void {
    try {
      localStorage.setItem(DOWNLOADS_KEY, JSON.stringify(downloads));
    } catch (e) {
      console.error('Error saving downloads to storage:', e);
    }
  }

  /** Get the saved theme preference ('light' | 'dark' | null). */
  static getTheme(): string | null {
    return localStorage.getItem(THEME_KEY);
  }

  /** Save the theme preference. */
  static setTheme(theme: 'light' | 'dark'): void {
    localStorage.setItem(THEME_KEY, theme);
  }
}