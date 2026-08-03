export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
  /** Set when a format-specific extractor was skipped or failed (e.g. an image
   *  above the decompression-bomb decode limit). Core fields stay exact. */
  metadata_warning: string | null;
  // Image-specific
  image_width: number | null;
  image_height: number | null;
  exif: Record<string, string> | null;
  // PDF-specific
  pdf_pages: number | null;
  pdf_author: string | null;
  pdf_title: string | null;
  // Audio/Video
  duration_seconds: number | null;
  codec: string | null;
  bitrate: number | null;
}

export interface FileUploadResponse {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  metadata: FileMetadataDetail | null;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
}

// --- Video scene search ---

export type VideoStatus =
  | "segmented"
  | "indexing"
  | "indexed"
  | "failed"
  | string;

export interface Video {
  id: string;
  title: string;
  status: VideoStatus;
  source_key: string;
  source_filename: string;
  scene_count: number;
  embedded_count: number;
  duration_seconds: number | null;
  scene_threshold: number;
  clip_model: string;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface Scene {
  number: number;
  start_seconds: number;
  end_seconds: number;
  start_timecode: string;
  end_timecode: string;
  keyframe_key: string;
  clip_key: string;
  embedded: boolean;
  keyframe_url: string | null;
  clip_url: string | null;
}

export interface VideoDetail extends Video {
  scenes: Scene[];
}

export interface SearchHit {
  video_id: string;
  video_title: string;
  scene_number: number;
  start_seconds: number;
  end_seconds: number;
  start_timecode: string;
  end_timecode: string;
  score: number;
  keyframe_url: string | null;
  clip_url: string | null;
}

export interface SearchResponse {
  mode: "text" | "image" | string;
  query: string | null;
  top_k: number;
  hits: SearchHit[];
}

export interface LibrarySummary {
  total_videos: number;
  segmented_videos: number;
  indexed_videos: number;
  total_scenes: number;
  embedded_scenes: number;
  source_bytes: number;
  scene_asset_bytes: number;
  total_bytes: number;
  total_bytes_human: string;
  index_present: boolean;
}
