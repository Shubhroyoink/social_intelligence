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

  const [selectedKeyword, setSelectedKeyword] = useState<string>(
    uniqueKeywords[0] || (latestTrends[0]?.keyword ?? '')
  );

  const activeKeyword = uniqueKeywords.includes(selectedKeyword)
    ? selectedKeyword
    : uniqueKeywords[0] || '';

  const keywordTimeline = trendsData?.keyword_timelines?.[activeKeyword] || [];

  const timelineDates = keywordTimeline.map((item) => (item.window_start || '').slice(0, 10));
  const timelineFreqs = keywordTimeline.map((item) => item.frequency || item.count || 0);

  const trendPlotlyData: Plotly.Data[] = [
    {
      x: timelineDates,
      y: timelineFreqs,
      type: 'scatter',
      mode: 'lines',
      connectgaps: false,
      line: { color: '#818cf8', width: 2 },
      name: activeKeyword,
      hovertemplate: '%{x}: %{y} mentions<extra></extra>',
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

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Left Column: Top terms */}
        <div className="space-y-3">
          <h4 className="text-xs font-bold uppercase tracking-wider text-neutral-300">
            Top terms (latest window)
          </h4>

          <div className="space-y-2 mt-2">
            {latestTrends.slice(0, 10).map((row, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between rounded-lg border border-neutral-800/80 bg-neutral-950/60 px-3 py-2 text-xs"
              >
                <span className="font-bold text-white">
                  {row.keyword}
                </span>
                <span className="text-neutral-400 font-medium">
                  {row.frequency || row.count || 0} mentions
                </span>
              </div>
            ))}

            {latestTrends.length === 0 && (
              <p className="text-xs text-neutral-500 py-4">No trend observations recorded</p>
            )}
          </div>
        </div>

        {/* Right Column: Trend over time with keyword selectbox */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold uppercase tracking-wider text-neutral-300">
              Trend over time
            </h4>

            {uniqueKeywords.length > 0 && (
              <div className="flex items-center gap-2">
                <label className="text-xs text-neutral-400">Select keyword:</label>
                <select
                  value={activeKeyword}
                  onChange={(e) => setSelectedKeyword(e.target.value)}
                  className="rounded-lg border border-neutral-800 bg-neutral-950 px-2.5 py-1 text-xs font-semibold text-indigo-300 focus:border-indigo-500 focus:outline-none"
                >
                  {uniqueKeywords.slice(0, 10).map((kw) => (
                    <option key={kw} value={kw}>
                      {kw}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          <div className="mt-2 rounded-xl border border-neutral-800 bg-neutral-950/40 p-2">
            {keywordTimeline.length > 0 ? (
              <PlotlyChart
                data={trendPlotlyData}
                layout={{
                  title: { text: activeKeyword, font: { size: 12, color: '#e4e4e7' } },
                  height: 250,
                  margin: { l: 40, r: 20, t: 30, b: 35 },
                  xaxis: {
                    title: { text: 'Date', font: { size: 11, color: '#71717a' } },
                  },
                  yaxis: {
                    title: { text: 'Frequency', font: { size: 11, color: '#71717a' } },
                  },
                }}
                className="h-64 w-full"
              />
            ) : (
              <div className="flex h-60 items-center justify-center text-xs text-neutral-500">
                {activeKeyword ? `No timeline data for "${activeKeyword}"` : 'Select a keyword'}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
