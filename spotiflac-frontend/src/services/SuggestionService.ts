import { ApiService } from "@/services/ApiService";

/**
 * Manages search suggestion fetching from the backend.
 */
export class SuggestionService {
  /** Fetch search suggestions for a given query string. */
  static async fetchSuggestions(query: string): Promise<string[]> {
    if (!query || query.length < 2) return [];

    try {
      const data = await ApiService.get<{ suggestions: string[] }>(
        `/suggestions?q=${encodeURIComponent(query)}`,
      );
      return data.suggestions || [];
    } catch (error) {
      console.error("Suggestions error:", error);
      return [];
    }
  }
}
