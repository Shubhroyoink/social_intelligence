import React, { useState } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
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

  return (
    <div className="rounded-2xl border border-neutral-800/80 bg-neutral-900/60 p-5 backdrop-blur-sm space-y-6">
      <div className="border-b border-neutral-800 pb-4">
        <h3 className="text-base font-bold text-white">Trending Terms</h3>
        <p className="text-xs text-neutral-400">
          TF-IDF keyword burst detection across sliding time windows
        </p>
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

          <div className="h-64 mt-2 rounded-xl border border-neutral-800 bg-neutral-950/40 p-2">
            {keywordTimeline.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={keywordTimeline}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                  <XAxis dataKey="window_start" stroke="#71717a" fontSize={10} tickFormatter={(val) => (val || '').slice(0, 10)} />
                  <YAxis stroke="#71717a" fontSize={11} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', borderRadius: '8px', fontSize: '12px' }}
                    itemStyle={{ color: '#ffffff' }}
                  />
                  <Line
                    type="monotone"
                    dataKey="frequency"
                    stroke="#818cf8"
                    strokeWidth={2.5}
                    dot={{ r: 4, fill: '#818cf8' }}
                    name={activeKeyword}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center">
                <p className="text-xs text-neutral-500">
                  {activeKeyword ? `No timeline data for "${activeKeyword}"` : 'Select a keyword'}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
