export type DownloadStatus =
  | "queued"
  | "downloading"
  | "complete"
  | "error"
  | "cancelled"
  | "not_found";

export interface DownloadItem {
  id: string;
  title: string;
  url: string;
  status: DownloadStatus;
  progress: number;
  error?: string | null;
  download_url?: string | null;
  speed?: string;
  eta?: string;
  timestamp?: number;
  statusText?: string;
  requestBody?: DownloadRequestBody;
  fallbackAttempted?: boolean;
  file?: string;
}

export interface QueueItem {
  url: string;
  title: string;
  useAdvanced: boolean;
  status: "queued";
  timestamp: number;
  buttonId: string;
}

export interface DownloadRequestBody {
  url: string;
  title: string;
  advancedOptions?: AdvancedOptions;
}

export interface AdvancedOptions {
  keepVideo?: boolean;
  embedSubtitles?: boolean;
  addMetadata?: boolean;
  customArgs?: string;
  videoQuality?: string;
  videoFPS?: string;
  videoFormat?: string;
  audioFormat?: string;
  audioQuality?: string;
  embedThumbnail?: boolean;
  speedLimit?: string;
  geoBypass?: boolean;
  preferFreeFormats?: boolean;
  addChapters?: boolean;
  maxFileSize?: string;
  playlistOption?: string;
  playlistItems?: string;
  subtitleOption?: string;
}

export interface DownloadResponse {
  download_id: string;
  error?: string;
}

export interface DownloadStatusResponse {
  status: DownloadStatus;
  title?: string;
  url?: string;
  progress?: number;
  error?: string;
  download_url?: string;
  speed?: string;
  eta?: string;
  file?: string;
}

export interface ProxyProgressResponse {
  progress: number;
  text?: string;
  success?: number;
  download_url?: string;
}
