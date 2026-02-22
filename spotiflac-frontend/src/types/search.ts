import { DirectUrlInfo, Song } from './song';

export type SearchType = 'music' | 'video' | 'all';
export type SourceId = 'jiosaavn' | 'soundcloud' | 'ytmusic' | 'ytvideo';

export interface SearchResults {
  jiosaavn: Song[];
  soundcloud: Song[];
  ytmusic: Song[];
  ytvideo: Song[];
  direct_url?: DirectUrlInfo[];
  query_type?: 'url' | 'search';
  search_id?: string;
  status?: string;
}

export interface SourceInfo {
  id: SourceId;
  name: string;
  count: number;
  data: Song[];
}

export interface PreviewData {
  title?: string;
  uploader?: string;
  channel?: string;
  album?: string;
  language?: string;
  duration?: string;
  plays?: number;
  likes?: number;
  genre?: string;
  thumbnail?: string;
  source?: string;
  pid?: string;
  error?: string;
  soundcloud_data?: SoundCloudData;
  soundcloud_recommendations?: SoundCloudTrack[];
}

export interface SoundCloudData {
  main_track: SoundCloudTrack;
  recommended_tracks?: SoundCloudTrack[];
}

export interface SoundCloudTrack {
  title: string;
  artist: string;
  url: string;
  thumbnail?: string;
  duration?: string;
  plays?: number;
  likes?: number;
  genre?: string;
}

export interface SuggestionResponse {
  suggestions: string[];
}

export interface JioSaavnSuggestion {
  title: string;
  artist: string;
  url: string;
  thumbnail?: string;
  album?: string;
}