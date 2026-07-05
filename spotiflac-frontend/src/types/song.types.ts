export interface Song {
  title: string;
  artist?: string;
  url: string;
  thumbnail?: string;
  duration?: string;
  year?: string;
  language?: string;
  subtitle?: string;
  album?: string;
  genre?: string;
  plays?: number;
  likes?: number;
}

export interface DirectUrlInfo {
  source: string;
  url: string;
  is_playlist?: boolean;
  title?: string;
}
