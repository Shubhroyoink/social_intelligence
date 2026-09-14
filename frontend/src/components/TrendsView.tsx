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
      line: { color: '#000000', width: 2.5 },
      name: activeKeyword,
      hovertemplate: '%{x}<br>Frequency: %{y}<extra></extra>',
    },
  ];

  return (
    <div className="rounded-lg border-2 border-black bg-white p-5 shadow-neo space-y-6">
      <div className="flex items-center justify-between border-b-2 border-black pb-4">
        <div>
          <h3 className="text-base font-black text-black uppercase tracking-wide">Trending Terms</h3>
          <p className="text-xs font-semibold text-neutral-600">
            TF-IDF keyword burst detection across sliding time windows
          </p>
        </div>
        <span className="rounded-md border-2 border-black bg-neutral-100 px-2.5 py-0.5 text-[11px] font-black text-black shadow-neo-sm">
          Interactive Plotly
        </span>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
        {/* Left Column: Top terms (latest window) */}
        <div className="space-y-3">
          <h4 className="text-sm font-black text-black uppercase tracking-wide">
            Top terms (latest window)
          </h4>

          <div className="space-y-2 mt-3">
            {latestTrends.slice(0, 10).map((row, idx) => {
              const isActive = activeKeyword === row.keyword;
              return (
                <div
                  key={idx}
                  onClick={() => setSelectedKeyword(row.keyword)}
                  className={`flex items-center justify-between rounded-lg px-3.5 py-2.5 text-sm cursor-pointer transition-all border-2 border-black ${
                    isActive
                      ? 'bg-black font-black text-white shadow-neo-sm translate-x-[1px] translate-y-[1px]'
                      : 'bg-white hover:bg-neutral-100 font-bold text-black shadow-neo-sm'
                  }`}
                >
                  <span className={`font-black ${isActive ? 'text-white' : 'text-black'}`}>
                    {row.keyword}
                  </span>
                  <span className={`font-bold text-xs ${isActive ? 'text-neutral-300' : 'text-neutral-600'}`}>
                    ({row.frequency || row.count || 0} mentions)
                  </span>
                </div>
              );
            })}

            {latestTrends.length === 0 && (
              <p className="text-xs font-bold text-neutral-500 py-4">No trend observations recorded</p>
            )}
          </div>
        </div>

        {/* Right Column: Trend over time with keyword selectbox */}
        <div className="space-y-4">
          <h4 className="text-sm font-black text-black uppercase tracking-wide">
            Trend over time
          </h4>

          {uniqueKeywords.length > 0 && (
            <div className="space-y-1.5">
              <label className="text-xs font-black uppercase text-neutral-700">Select keyword</label>
              <select
                value={activeKeyword}
                onChange={(e) => setSelectedKeyword(e.target.value)}
                className="w-full rounded-lg border-2 border-black bg-white px-3 py-2 text-sm font-black text-black shadow-neo-sm focus:outline-none cursor-pointer"
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
            <div className="text-base font-black text-black uppercase tracking-wide pt-1">
              {activeKeyword}
            </div>
          )}

          <div className="rounded-lg border-2 border-black bg-white p-2 shadow-neo-sm">
            {keywordTimeline.length > 0 ? (
              <PlotlyChart
                data={trendPlotlyData}
                layout={{
                  height: 280,
                  margin: { l: 50, r: 20, t: 20, b: 50 },
                  xaxis: {
                    title: { text: 'window_start', font: { size: 12, color: '#000000' } },
                    tickfont: { size: 10, color: '#000000' },
                    gridcolor: '#e5e7eb',
                  },
                  yaxis: {
                    title: { text: 'frequency', font: { size: 12, color: '#000000' } },
                    tickfont: { size: 10, color: '#000000' },
                    gridcolor: '#e5e7eb',
                  },
                }}
                className="h-72 w-full"
              />
            ) : (
              <div className="flex h-64 items-center justify-center text-xs font-bold text-neutral-500">
                {activeKeyword ? `No timeline data for "${activeKeyword}"` : 'Select a keyword'}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
