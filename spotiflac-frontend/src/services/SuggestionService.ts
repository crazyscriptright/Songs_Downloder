import { getApiBaseUrl } from '@/config';
import type { SuggestionResponse } from '@/types';

/**
 * Manages search suggestion fetching from the backend.
 */
export class SuggestionService {
  /** Fetch search suggestions for a given query string. */
  static async fetchSuggestions(query: string): Promise<string[]> {
    if (!query || query.length < 2) return [];

    try {
      const apiUrl = getApiBaseUrl();
      const response = await fetch(
        `${apiUrl}/suggestions?q=${encodeURIComponent(query)}`,
      );

      if (!response.ok) {
        console.error('Failed to fetch suggestions:', response.statusText);
        return [];
      }

      const data: SuggestionResponse = await response.json();
      return data.suggestions || [];
    } catch (error) {
      console.error('Suggestions error:', error);
      return [];
    }
  }
}