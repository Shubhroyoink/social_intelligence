export interface Post {
  id: string;
  platform: string;
  author_id?: string;
  author_handle?: string;
  text: string;
  raw_text?: string;
  created_at: string;
  collected_at: string;
  parent_id?: string;
  topic_query?: string;
  reactions: number;
  shares: number;
  replies?: number;
  views?: number;
  sentiment?: string;
  sentiment_score?: number;
  primary_emotion?: string;
  stance?: string;
  sarcasm_flag?: number;
}

export interface Sentiment {
  id?: number;
  post_id?: string;
  platform?: string;
  label: "positive" | "neutral" | "negative";
  score?: number;
  positive_score?: number;
  neutral_score?: number;
  negative_score?: number;
  analyzed_at?: string;
  created_at?: string;
}

export interface Emotion {
  id?: number;
  post_id?: string;
  platform?: string;
  primary_emotion: string;
  confidence?: number;
  scores_json?: string;
  emotion_json?: string;
  sarcasm_flag: number;
  stance: string;
  analyzed_at?: string;
  created_at?: string;
}

export interface DemographicsSummary {
  languages: Record<string, number>;
  geo: Record<string, number>;
  interests: Record<string, number>;
}

export interface TrendItem {
  keyword: string;
  frequency: number;
  count?: number;
  window_start?: string;
  window_end?: string;
}

export interface TrendsData {
  all_trends: TrendItem[];
  latest_window?: string;
  latest_trends: TrendItem[];
  unique_keywords: string[];
  keyword_timelines: Record<string, Array<{ window_start: string; frequency: number }>>;
}

export interface NetworkNode {
  handle: string;
  topic_query?: string;
  degree_centrality?: number;
  betweenness_centrality?: number;
  eigenvector_centrality?: number;
  community_id?: number;
  is_kol: number;
  computed_at?: string;
}

export interface NetworkEdge {
  source_handle: string;
  target_handle: string;
  weight: number;
  sentiment_shift?: number;
}

export interface NetworkData {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  kols: NetworkNode[];
  node_count: number;
  edge_count: number;
  kol_count: number;
}

export interface Narrative {
  id?: number;
  topic_query: string;
  backend?: string;
  model?: string;
  stats_json?: string;
  report_markdown?: string;
  report_text?: string;
  created_at: string;
}

export interface OverviewStats {
  total_posts: number;
  total_analyzed: number;
  positive_pct: number;
  neutral_pct: number;
  negative_pct: number;
  sarcasm_pct: number;
  kol_count: number;
  top_keyword: string | null;
  dominant_emotion: string;
  platform_counts: Record<string, number>;
}

export interface PipelineRunRequest {
  topic: string;
  channels?: string[];
  x_queries?: string[];
  youtube_urls?: string[];
  youtube_search?: boolean;
  yt_max_videos?: number;
  yt_comments?: number;
  telegram_limit?: number;
  x_limit?: number;
  do_collect?: boolean;
  do_analyze?: boolean;
  skip_emotions?: boolean;
  skip_demographics?: boolean;
  skip_network?: boolean;
  skip_narrative?: boolean;
}

export interface PipelineStatus {
  is_running: boolean;
  last_run: string | null;
  current_topic: string | null;
  status_message: string;
  error: string | null;
}
