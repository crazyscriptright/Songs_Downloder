import { ApiService } from "@/services/api.service";
import type {
  JioSaavnSuggestion,
  PreviewData,
  SearchResults,
  SearchType,
  Song,
  SourceId,
} from "@/types";

/** Format milliseconds to "m:ss" string for display. */
function formatDurationMs(ms: number): string {
  const totalSec = Math.round(ms / 1000);
  const minutes = Math.floor(totalSec / 60);
  const seconds = totalSec % 60;
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

interface SpotifyApiItem {
  name?: string;
  artists?: string[] | string;
  spotify_url?: string;
  uri?: string;
  cover_url?: string;
  album?: string;
  duration_ms?: number;
}

/** Map a Spotify API result item to the common Song shape. */
function mapSpotifyToSong(item: SpotifyApiItem): Song {
  const artists = Array.isArray(item.artists) ? item.artists.join(", ") : (item.artists ?? "");
  return {
    title: item.name ?? "",
    artist: artists,
    url: item.spotify_url ?? item.uri ?? "",
    thumbnail: item.cover_url ?? "",
    album: item.album ?? "",
    duration: item.duration_ms ? formatDurationMs(item.duration_ms) : undefined,
  };
}

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
    const data = await ApiService.post<{
      search_id: string;
      status: string;
      query_type: string;
    }>("/search", { query, type });
    return data.search_id;
  }

  /**
   * Poll the backend for URL search results.
   */
  static async pollSearchStatus(searchId: string): Promise<SearchResults> {
    const data = await ApiService.get<SearchResults>(`/search_status/${searchId}`);
    return data;
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
    if (type === "music" || type === "all") {
      endpoints.push("jiosaavn", "soundcloud", "ytmusic", "spotify");
    }
    if (type === "video" || type === "all") {
      endpoints.push("ytvideo");
    }
    if (type === "spotify") {
      endpoints.push("spotify");
    }

    const totalSources = endpoints.length;
    let completedSources = 0;

    const allResults: SearchResults = {
      jiosaavn: [],
      soundcloud: [],
      ytmusic: [],
      ytvideo: [],
      spotify: [],
    };

    const promises = endpoints.map(async (source) => {
      try {
        const data = await ApiService.post<{ results?: Song[] }>(`/search/${source}`, {
          query,
          type,
        });
        if (source === "spotify") {
          allResults[source] = (data.results || []).map(mapSpotifyToSong);
        } else {
          allResults[source] = data.results || [];
        }
      } catch {
        allResults[source] = [];
      }
      completedSources++;
      onSourceResult(source, allResults[source]!, completedSources, totalSources);
    });

    await Promise.allSettled(promises);
    return allResults;
  }

  /**
   * Fetch URL preview data from the backend.
   */
  static async fetchPreview(url: string): Promise<PreviewData | null> {
    const data = await ApiService.post<PreviewData>("/preview_url", { url });
    return data;
  }

  /**
   * Fetch JioSaavn recommendation tracks for a given pid.
   */
  static async fetchJioSaavnSuggestions(
    pid: string,
    language = "hindi",
  ): Promise<JioSaavnSuggestion[]> {
    try {
      const data = await ApiService.get<{ suggestions: JioSaavnSuggestion[] }>(
        `/jiosaavn_suggestions/${pid}?language=${language}`,
      );
      return data.suggestions || [];
    } catch {
      return [];
    }
  }
}
