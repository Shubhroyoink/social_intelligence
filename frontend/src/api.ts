import type {
  Post,
  Sentiment,
  Emotion,
  DemographicsSummary,
  TrendsData,
  NetworkData,
  Narrative,
  OverviewStats,
  PipelineRunRequest,
  PipelineStatus,
} from "./types";

const API_BASE = "http://localhost:8000";

export async function fetchTopics(): Promise<string[]> {
  try {
    const res = await fetch(`${API_BASE}/api/topics`);
    if (!res.ok) return [];
    const data = await res.json();
    return data.topics || [];
  } catch (err) {
    console.error("Failed to fetch topics:", err);
    return [];
  }
}

export async function fetchOverview(topic?: string): Promise<OverviewStats | null> {
  try {
    const url = new URL(`${API_BASE}/api/overview`);
    if (topic && topic !== "All") url.searchParams.set("topic", topic);
    const res = await fetch(url.toString());
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.error("Failed to fetch overview:", err);
    return null;
  }
}

export async function fetchSentiments(topic?: string): Promise<{
  sentiments: Sentiment[];
  distribution: Record<string, number>;
  by_platform: Record<string, Record<string, number>>;
  platform_percentages: Array<{ platform: string; positive: number; neutral: number; negative: number; total_count: number }>;
  timeline: Array<{ date: string; positive: number; neutral: number; negative: number; count: number }>;
  count: number;
}> {
  try {
    const url = new URL(`${API_BASE}/api/sentiments`);
    if (topic && topic !== "All") url.searchParams.set("topic", topic);
    const res = await fetch(url.toString());
    if (!res.ok) return { sentiments: [], distribution: {}, by_platform: {}, platform_percentages: [], timeline: [], count: 0 };
    return await res.json();
  } catch (err) {
    console.error("Failed to fetch sentiments:", err);
    return { sentiments: [], distribution: {}, by_platform: {}, platform_percentages: [], timeline: [], count: 0 };
  }
}

export async function fetchEmotions(topic?: string): Promise<{
  emotions: Emotion[];
  emotion_counts: Record<string, number>;
  stance_counts: Record<string, number>;
  sarcasm_pct: number;
  timeline: Array<Record<string, any>>;
  count: number;
}> {
  try {
    const url = new URL(`${API_BASE}/api/emotions`);
    if (topic && topic !== "All") url.searchParams.set("topic", topic);
    const res = await fetch(url.toString());
    if (!res.ok) return { emotions: [], emotion_counts: {}, stance_counts: {}, sarcasm_pct: 0, timeline: [], count: 0 };
    return await res.json();
  } catch (err) {
    console.error("Failed to fetch emotions:", err);
    return { emotions: [], emotion_counts: {}, stance_counts: {}, sarcasm_pct: 0, timeline: [], count: 0 };
  }
}

export async function fetchDemographics(topic?: string): Promise<DemographicsSummary> {
  try {
    const url = new URL(`${API_BASE}/api/demographics`);
    if (topic && topic !== "All") url.searchParams.set("topic", topic);
    const res = await fetch(url.toString());
    if (!res.ok) return { languages: {}, geo: {}, interests: {} };
    return await res.json();
  } catch (err) {
    console.error("Failed to fetch demographics:", err);
    return { languages: {}, geo: {}, interests: {} };
  }
}

export async function fetchTrends(topic?: string): Promise<TrendsData> {
  try {
    const url = new URL(`${API_BASE}/api/trends`);
    if (topic && topic !== "All") url.searchParams.set("topic", topic);
    const res = await fetch(url.toString());
    if (!res.ok) return { all_trends: [], latest_trends: [], unique_keywords: [], keyword_timelines: {} };
    return await res.json();
  } catch (err) {
    console.error("Failed to fetch trends:", err);
    return { all_trends: [], latest_trends: [], unique_keywords: [], keyword_timelines: {} };
  }
}

export async function fetchNetwork(topic?: string): Promise<NetworkData> {
  try {
    const url = new URL(`${API_BASE}/api/network`);
    if (topic && topic !== "All") url.searchParams.set("topic", topic);
    const res = await fetch(url.toString());
    if (!res.ok) return { nodes: [], edges: [], kols: [], node_count: 0, edge_count: 0, kol_count: 0 };
    return await res.json();
  } catch (err) {
    console.error("Failed to fetch network:", err);
    return { nodes: [], edges: [], kols: [], node_count: 0, edge_count: 0, kol_count: 0 };
  }
}

export async function fetchNarratives(topic?: string): Promise<{
  narratives: Narrative[];
  latest: Narrative | null;
}> {
  try {
    const url = new URL(`${API_BASE}/api/narratives`);
    if (topic && topic !== "All") url.searchParams.set("topic", topic);
    const res = await fetch(url.toString());
    if (!res.ok) return { narratives: [], latest: null };
    return await res.json();
  } catch (err) {
    console.error("Failed to fetch narratives:", err);
    return { narratives: [], latest: null };
  }
}

export async function fetchWordCloud(topic?: string, limit: number = 100): Promise<Array<{ text: string; value: number }>> {
  try {
    const url = new URL(`${API_BASE}/api/wordcloud`);
    if (topic && topic !== "All") url.searchParams.set("topic", topic);
    url.searchParams.set("limit", limit.toString());
    const res = await fetch(url.toString());
    if (!res.ok) return [];
    const data = await res.json();
    return data.words || [];
  } catch (err) {
    console.error("Failed to fetch wordcloud:", err);
    return [];
  }
}

export async function fetchPosts(
  topic?: string,
  platform?: string,
  sentiment?: string,
  limit: number = 100,
  search?: string
): Promise<Post[]> {
  try {
    const url = new URL(`${API_BASE}/api/posts`);
    if (topic && topic !== "All") url.searchParams.set("topic", topic);
    if (platform && platform !== "All") url.searchParams.set("platform", platform);
    if (sentiment && sentiment !== "All") url.searchParams.set("sentiment", sentiment);
    if (search) url.searchParams.set("search", search);
    url.searchParams.set("limit", limit.toString());
    const res = await fetch(url.toString());
    if (!res.ok) return [];
    const data = await res.json();
    return data.posts || [];
  } catch (err) {
    console.error("Failed to fetch posts:", err);
    return [];
  }
}

export async function triggerPipeline(req: PipelineRunRequest): Promise<{ status: string; message: string; topic: string }> {
  const res = await fetch(`${API_BASE}/api/pipeline/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to trigger pipeline" }));
    throw new Error(err.detail || "Pipeline execution failed");
  }
  return await res.json();
}

export async function fetchPipelineStatus(): Promise<PipelineStatus> {
  try {
    const res = await fetch(`${API_BASE}/api/pipeline/status`);
    if (!res.ok) return { is_running: false, last_run: null, current_topic: null, status_message: "Offline", error: null };
    return await res.json();
  } catch {
    return { is_running: false, last_run: null, current_topic: null, status_message: "Offline", error: null };
  }
}
