import { getApiBaseUrl } from '@/config';
import type {
    JioSaavnSuggestion,
    PreviewData,
    SearchResults,
    SearchType,
    Song,
    SourceId,
} from '@/types';

export type SourceResultCallback = (
  source: SourceId,
  results: Song[],
  completedCount: number,
  totalCount: number,
) => void;

/**
 * Handles music/video search across multiple platforms.
 */
export class SearchService {
  /**
   * Initiate a URL-based search (single endpoint) and return the search_id for polling.
   */
  static async searchByUrl(query: string, type: SearchType): Promise<string> {
    const response = await fetch(`${getApiBaseUrl()}/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, type }),
    });
    const data = await response.json();
    return data.search_id as string;
  }

  /**
   * Poll the backend for URL search results.
   */
  static async pollSearchStatus(searchId: string): Promise<SearchResults> {
    const response = await fetch(`${getApiBaseUrl()}/search_status/${searchId}`);
    return response.json();
  }

  /**
   * Run a parallel keyword search across multiple platforms.
   * Calls `onSourceResult` each time a source returns results.
   */
  static async searchParallel(
    query: string,
    type: SearchType,
    onSourceResult: SourceResultCallback,
  ): Promise<SearchResults> {
    const endpoints: SourceId[] = [];
    if (type === 'music' || type === 'all') {
      endpoints.push('jiosaavn', 'soundcloud', 'ytmusic');
    }
    if (type === 'video' || type === 'all') {
      endpoints.push('ytvideo');
    }

    const totalSources = endpoints.length;
    let completedSources = 0;

    const allResults: SearchResults = {
      jiosaavn: [],
      soundcloud: [],
      ytmusic: [],
      ytvideo: [],
    };

    const promises = endpoints.map(async (source) => {
      try {
        const response = await fetch(`${getApiBaseUrl()}/search/${source}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query, type }),
        });
        const data = await response.json();
        allResults[source] = data.results || [];
      } catch {
        allResults[source] = [];
      }
      completedSources++;
      onSourceResult(source, allResults[source], completedSources, totalSources);
    });

    await Promise.allSettled(promises);
    return allResults;
  }

  /**
   * Fetch URL preview data from the backend.
   */
  static async fetchPreview(url: string): Promise<PreviewData | null> {
    try {
      const response = await fetch(`${getApiBaseUrl()}/preview_url`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      });

      if (response.ok) {
        return response.json();
      }
      const errorData = await response.json();
      if (errorData.error) {
        throw new Error(errorData.error);
      }
      return null;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Fetch JioSaavn recommendation tracks for a given pid.
   */
  static async fetchJioSaavnSuggestions(
    pid: string,
    language = 'hindi',
  ): Promise<JioSaavnSuggestion[]> {
    const response = await fetch(
      `${getApiBaseUrl()}/jiosaavn_suggestions/${pid}?language=${language}`,
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    if (data.error) throw new Error(data.error);
    return data.suggestions || [];
  }
}