import React, { useEffect, useState, useCallback } from 'react';
import { Header } from './components/Header';
import { OverviewCards } from './components/OverviewCards';
import { SentimentView } from './components/SentimentView';
import { EmotionView } from './components/EmotionView';
import { TrendsView } from './components/TrendsView';
import { DemographicsView } from './components/DemographicsView';
import { NetworkView } from './components/NetworkView';
import { NarrativeView } from './components/NarrativeView';
import { WordCloudView } from './components/WordCloudView';
import { PostsExplorer } from './components/PostsExplorer';
import { PipelineModal } from './components/PipelineModal';
import {
  fetchTopics,
  fetchOverview,
  fetchSentiments,
  fetchEmotions,
  fetchDemographics,
  fetchTrends,
  fetchNetwork,
  fetchNarratives,
  fetchWordCloud,
  fetchPosts,
  fetchPipelineStatus,
} from './api';
import type {
  OverviewStats,
  Sentiment,
  Emotion,
  DemographicsSummary,
  TrendsData,
  NetworkData,
  Narrative,
  Post,
  PipelineStatus,
} from './types';
import {
  BarChart3,
  BrainCircuit,
  Share2,
  TrendingUp,
  FileText,
  Cloud,
  Database,
  Users,
} from 'lucide-react';

export function App() {
  const [topics, setTopics] = useState<string[]>([]);
  const [selectedTopic, setSelectedTopic] = useState<string>('All');
  const [activeTab, setActiveTab] = useState<
    'all' | 'sentiment' | 'trends' | 'emotions' | 'demographics' | 'network' | 'narrative' | 'wordcloud' | 'posts'
  >('all');

  // Filter states for posts
  const [filterPlatform, setFilterPlatform] = useState('All');
  const [filterSentiment, setFilterSentiment] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');

  // Data states
  const [stats, setStats] = useState<OverviewStats | null>(null);
  const [sentimentsData, setSentimentsData] = useState<{
    sentiments: Sentiment[];
    distribution: Record<string, number>;
    by_platform: Record<string, Record<string, number>>;
    platform_percentages: Array<{ platform: string; positive: number; neutral: number; negative: number; total_count: number }>;
    timeline: Array<{ date: string; positive: number; neutral: number; negative: number; count: number }>;
  }>({ sentiments: [], distribution: {}, by_platform: {}, platform_percentages: [], timeline: [] });

  const [emotionsData, setEmotionsData] = useState<{
    emotions: Emotion[];
    emotion_counts: Record<string, number>;
    stance_counts: Record<string, number>;
    sarcasm_pct: number;
    timeline: Array<Record<string, any>>;
  }>({ emotions: [], emotion_counts: {}, stance_counts: {}, sarcasm_pct: 0, timeline: [] });

  const [demographics, setDemographics] = useState<DemographicsSummary>({
    languages: {},
    geo: {},
    interests: {},
  });
  
  const [trendsData, setTrendsData] = useState<TrendsData>({
    all_trends: [],
    latest_trends: [],
    unique_keywords: [],
    keyword_timelines: {},
  });

  const [network, setNetwork] = useState<NetworkData>({
    nodes: [],
    edges: [],
    kols: [],
    node_count: 0,
    edge_count: 0,
    kol_count: 0,
  });

  const [narratives, setNarratives] = useState<{ narratives: Narrative[]; latest: Narrative | null }>({
    narratives: [],
    latest: null,
  });

  const [wordCloudWords, setWordCloudWords] = useState<Array<{ text: string; value: number }>>([]);
  const [posts, setPosts] = useState<Post[]>([]);

  // Pipeline execution & modal
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus>({
    is_running: false,
    last_run: null,
    current_topic: null,
    status_message: 'Idle',
    error: null,
  });

  const loadData = useCallback(async (topic: string) => {
    setIsRefreshing(true);
    try {
      const [
        fetchedTopics,
        fetchedOverview,
        fetchedSentiments,
        fetchedEmotions,
        fetchedDemographics,
        fetchedTrends,
        fetchedNetwork,
        fetchedNarratives,
        fetchedWords,
        fetchedPosts,
        status,
      ] = await Promise.all([
        fetchTopics(),
        fetchOverview(topic),
        fetchSentiments(topic),
        fetchEmotions(topic),
        fetchDemographics(topic),
        fetchTrends(topic),
        fetchNetwork(topic),
        fetchNarratives(topic),
        fetchWordCloud(topic),
        fetchPosts(topic, filterPlatform, filterSentiment, 100, searchQuery),
        fetchPipelineStatus(),
      ]);

      setTopics(fetchedTopics);
      setStats(fetchedOverview);
      setSentimentsData(fetchedSentiments);
      setEmotionsData(fetchedEmotions);
      setDemographics(fetchedDemographics);
      setTrendsData(fetchedTrends);
      setNetwork(fetchedNetwork);
      setNarratives(fetchedNarratives);
      setWordCloudWords(fetchedWords);
      setPosts(fetchedPosts);
      setPipelineStatus(status);
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setIsRefreshing(false);
    }
  }, [filterPlatform, filterSentiment, searchQuery]);

  useEffect(() => {
    loadData(selectedTopic);
  }, [selectedTopic, loadData]);

  // Periodic poll while pipeline runs
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const status = await fetchPipelineStatus();
        setPipelineStatus((prev) => {
          if (
            prev.is_running === status.is_running &&
            prev.status_message === status.status_message &&
            prev.last_run === status.last_run &&
            prev.error === status.error
          ) {
            return prev;
          }
          return status;
        });
        if (status.is_running) {
          loadData(selectedTopic);
        }
      } catch (e) {
        // silent fail for background poll
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [selectedTopic, loadData]);

  const tabs = [
    { id: 'all', label: 'Complete Streamlit View', icon: BrainCircuit },
    { id: 'sentiment', label: 'Sentiment Distribution', icon: BarChart3 },
    { id: 'emotions', label: 'Emotion & Stance', icon: BrainCircuit },
    { id: 'trends', label: 'Trending Terms', icon: TrendingUp },
    { id: 'demographics', label: 'Demographics', icon: Users },
    { id: 'network', label: 'Network & KOLs', icon: Share2 },
    { id: 'narrative', label: 'AI Narrative', icon: FileText },
    { id: 'wordcloud', label: 'Word Cloud', icon: Cloud },
    { id: 'posts', label: 'Sample Posts', icon: Database },
  ] as const;

  return (
    <div className="min-h-screen bg-neutral-950 pb-16">
      {/* Top Header */}
      <Header
        topics={topics}
        selectedTopic={selectedTopic}
        onSelectTopic={setSelectedTopic}
        onOpenPipelineModal={() => setIsModalOpen(true)}
        onRefresh={() => loadData(selectedTopic)}
        isRefreshing={isRefreshing}
        pipelineStatus={pipelineStatus}
      />

      <main className="mx-auto max-w-7xl px-4 pt-6 sm:px-6 lg:px-8 space-y-8">
        {/* Streamlit Top Section: Executive Summary / AI Narrative */}
        <NarrativeView
          narrative={narratives.latest}
          narratives={narratives.narratives}
        />

        {/* Streamlit 4 KPI Metrics Row: Posts Collected, Posts Analyzed, Positive, Negative */}
        <OverviewCards stats={stats} />

        {/* View Mode Navigation Tabs */}
        <div className="flex overflow-x-auto border-b border-neutral-800/80 pb-px scrollbar-none">
          <div className="flex gap-2">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 whitespace-nowrap border-b-2 px-4 py-2.5 text-xs font-semibold transition-all ${
                    isActive
                      ? 'border-indigo-500 text-indigo-400 bg-indigo-500/10 rounded-t-lg'
                      : 'border-transparent text-neutral-400 hover:border-neutral-700 hover:text-neutral-200'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Tab Content */}
        <div className="space-y-8">
          {/* Complete Streamlit View (renders all sections top to bottom matching app.py exactly) */}
          {activeTab === 'all' && (
            <>
              {/* 1. Sentiment Distribution, Timeline & Platform */}
              <SentimentView
                distribution={sentimentsData.distribution}
                by_platform={sentimentsData.by_platform}
                platform_percentages={sentimentsData.platform_percentages}
                timeline={sentimentsData.timeline}
              />

              <hr className="border-neutral-800" />

              {/* 2. Trending Terms & Trend over time line chart */}
              <TrendsView trendsData={trendsData} />

              <hr className="border-neutral-800" />

              {/* 3. Emotion Analysis, Timeline & Stance */}
              <EmotionView
                emotion_counts={emotionsData.emotion_counts}
                stance_counts={emotionsData.stance_counts}
                sarcasm_pct={emotionsData.sarcasm_pct}
                timeline={emotionsData.timeline}
              />

              <hr className="border-neutral-800" />

              {/* 4. Demographics (Language, Geography, Interests) */}
              <DemographicsView demographics={demographics} />

              <hr className="border-neutral-800" />

              {/* 5. Network & Influence Analysis + KOL Table + Graph */}
              <NetworkView network={network} />

              <hr className="border-neutral-800" />

              {/* 6. Word Cloud */}
              <WordCloudView words={wordCloudWords} />

              <hr className="border-neutral-800" />

              {/* 7. View Sample Posts */}
              <PostsExplorer
                posts={posts}
                onSearch={setSearchQuery}
                onFilterPlatform={setFilterPlatform}
                onFilterSentiment={setFilterSentiment}
                selectedPlatform={filterPlatform}
                selectedSentiment={filterSentiment}
              />
            </>
          )}

          {/* Focused Tab Views */}
          {activeTab === 'sentiment' && (
            <SentimentView
              distribution={sentimentsData.distribution}
              by_platform={sentimentsData.by_platform}
              platform_percentages={sentimentsData.platform_percentages}
              timeline={sentimentsData.timeline}
            />
          )}

          {activeTab === 'trends' && (
            <TrendsView trendsData={trendsData} />
          )}

          {activeTab === 'emotions' && (
            <EmotionView
              emotion_counts={emotionsData.emotion_counts}
              stance_counts={emotionsData.stance_counts}
              sarcasm_pct={emotionsData.sarcasm_pct}
              timeline={emotionsData.timeline}
            />
          )}

          {activeTab === 'demographics' && (
            <DemographicsView demographics={demographics} />
          )}

          {activeTab === 'network' && (
            <NetworkView network={network} />
          )}

          {activeTab === 'narrative' && (
            <NarrativeView
              narrative={narratives.latest}
              narratives={narratives.narratives}
            />
          )}

          {activeTab === 'wordcloud' && (
            <WordCloudView words={wordCloudWords} />
          )}

          {activeTab === 'posts' && (
            <PostsExplorer
              posts={posts}
              onSearch={setSearchQuery}
              onFilterPlatform={setFilterPlatform}
              onFilterSentiment={setFilterSentiment}
              selectedPlatform={filterPlatform}
              selectedSentiment={filterSentiment}
            />
          )}
        </div>
      </main>

      {/* Pipeline Execution Modal */}
      <PipelineModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onTriggerSuccess={() => loadData(selectedTopic)}
      />
    </div>
  );
}

export default App;
