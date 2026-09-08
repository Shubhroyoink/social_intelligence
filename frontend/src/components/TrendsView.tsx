import React, { useState } from 'react';
import { PlotlyChart } from './PlotlyChart';
import type { TrendsData } from '../types';

interface TrendsViewProps {
  trendsData?: TrendsData;
}

export const TrendsView: React.FC<TrendsViewProps> = ({
  trendsData = { all_trends: [], latest_trends: [], unique_keywords: [], keyword_timelines: {} },
}) => {
  const latestTrends = trendsData?.latest_trends || [];
  const uniqueKeywords = trendsData?.unique_keywords || [];

  const [selectedKeyword, setSelectedKeyword] = useState<string>('');

  const activeKeyword =
    selectedKeyword && uniqueKeywords.includes(selectedKeyword)
      ? selectedKeyword
      : uniqueKeywords[0] || latestTrends[0]?.keyword || '';

  const keywordTimeline = trendsData?.keyword_timelines?.[activeKeyword] || [];

  const timelineDates = keywordTimeline.map((item) => item.window_start || '');
  const timelineFreqs = keywordTimeline.map((item) => item.frequency || item.count || 0);

  const trendPlotlyData: Plotly.Data[] = [
    {
      x: timelineDates,
      y: timelineFreqs,
      type: 'scatter',
      mode: 'lines',
      connectgaps: true,
      line: { color: '#60a5fa', width: 2.2 },
      name: activeKeyword,
      hovertemplate: '%{x}<br>Frequency: %{y}<extra></extra>',
    },
  ];

  return (
    <div className="rounded-2xl border border-neutral-800/80 bg-neutral-900/60 p-5 backdrop-blur-sm space-y-6">
      <div className="flex items-center justify-between border-b border-neutral-800 pb-4">
        <div>
          <h3 className="text-base font-bold text-white">Trending Terms</h3>
          <p className="text-xs text-neutral-400">
            TF-IDF keyword burst detection across sliding time windows
          </p>
        </div>
        <span className="rounded-full border border-indigo-500/20 bg-indigo-500/10 px-2.5 py-0.5 text-[11px] font-medium text-indigo-400">
          Interactive Plotly
        </span>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
        {/* Left Column: Top terms (latest window) */}
        <div className="space-y-3">
          <h4 className="text-sm font-bold text-white">
            Top terms (latest window)
          </h4>

          <div className="space-y-2 mt-3">
            {latestTrends.slice(0, 10).map((row, idx) => (
              <div
                key={idx}
                onClick={() => setSelectedKeyword(row.keyword)}
                className={`flex items-center justify-between rounded-lg px-3 py-2 text-sm cursor-pointer transition-colors ${
                  activeKeyword === row.keyword
                    ? 'bg-neutral-800 border border-neutral-700 font-semibold text-white'
                    : 'bg-neutral-950/40 hover:bg-neutral-800/50 text-neutral-300'
                }`}
              >
                <span className="font-bold text-white">
                  {row.keyword}
                </span>
                <span className="text-neutral-400 font-normal">
                  ({row.frequency || row.count || 0} mentions)
                </span>
              </div>
            ))}

            {latestTrends.length === 0 && (
              <p className="text-xs text-neutral-500 py-4">No trend observations recorded</p>
            )}
          </div>
        </div>

        {/* Right Column: Trend over time with keyword selectbox */}
        <div className="space-y-4">
          <h4 className="text-sm font-bold text-white">
            Trend over time
          </h4>

          {uniqueKeywords.length > 0 && (
            <div className="space-y-1.5">
              <label className="text-xs text-neutral-300">Select keyword</label>
              <select
                value={activeKeyword}
                onChange={(e) => setSelectedKeyword(e.target.value)}
                className="w-full rounded-lg border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm font-semibold text-white focus:border-indigo-500 focus:outline-none"
              >
                {uniqueKeywords.map((kw) => (
                  <option key={kw} value={kw}>
                    {kw}
                  </option>
                ))}
              </select>
            </div>
          )}

          {activeKeyword && (
            <div className="text-sm font-bold text-white pt-2">
              {activeKeyword}
            </div>
          )}

          <div className="rounded-xl border border-neutral-800 bg-neutral-950/40 p-2">
            {keywordTimeline.length > 0 ? (
              <PlotlyChart
                data={trendPlotlyData}
                layout={{
                  height: 280,
                  margin: { l: 50, r: 20, t: 20, b: 50 },
                  xaxis: {
                    title: { text: 'window_start', font: { size: 12, color: '#a1a1aa' } },
                    tickfont: { size: 10, color: '#a1a1aa' },
                    gridcolor: 'rgba(255,255,255,0.05)',
                  },
                  yaxis: {
                    title: { text: 'frequency', font: { size: 12, color: '#a1a1aa' } },
                    tickfont: { size: 10, color: '#a1a1aa' },
                    gridcolor: 'rgba(255,255,255,0.08)',
                  },
                }}
                className="h-72 w-full"
              />
            ) : (
              <div className="flex h-64 items-center justify-center text-xs text-neutral-500">
                {activeKeyword ? `No timeline data for "${activeKeyword}"` : 'Select a keyword'}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
