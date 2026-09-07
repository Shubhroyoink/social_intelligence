import React from 'react';
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Legend,
  LineChart,
  Line,
} from 'recharts';

interface SentimentViewProps {
  distribution?: Record<string, number>;
  by_platform?: Record<string, Record<string, number>>;
  platform_percentages?: Array<{ platform: string; positive: number; neutral: number; negative: number; total_count: number }>;
  timeline?: Array<{ date: string; positive: number; neutral: number; negative: number; count: number }>;
}

const STREAMLIT_COLORS = {
  positive: '#2ca02c',
  neutral: '#999999',
  negative: '#d62728',
};

export const SentimentView: React.FC<SentimentViewProps> = ({
  distribution = {},
  by_platform = {},
  platform_percentages = [],
  timeline = [],
}) => {
  // If platform_percentages is empty, calculate from by_platform as fallback
  const computedPlatformData = (platform_percentages && platform_percentages.length > 0)
    ? platform_percentages
    : Object.entries(by_platform || {}).map(([plat, counts]) => {
        const total_p = Object.values(counts).reduce((a, b) => a + b, 0);
        return {
          platform: plat.toUpperCase(),
          positive: total_p ? Math.round(((counts.positive || 0) * 100) / total_p) : 0,
          neutral: total_p ? Math.round(((counts.neutral || 0) * 100) / total_p) : 0,
          negative: total_p ? Math.round(((counts.negative || 0) * 100) / total_p) : 0,
          total_count: total_p,
        };
      });

  const pieData = [
    { name: 'positive', value: distribution?.positive || 0, color: STREAMLIT_COLORS.positive },
    { name: 'neutral', value: distribution?.neutral || 0, color: STREAMLIT_COLORS.neutral },
    { name: 'negative', value: distribution?.negative || 0, color: STREAMLIT_COLORS.negative },
  ].filter((d) => d.value > 0);

  const total = pieData.reduce((sum, d) => sum + d.value, 0);

  return (
    <div className="space-y-6">
      {/* 1. Sentiment Distribution Donut */}
      <div className="rounded-2xl border border-neutral-800/80 bg-neutral-900/60 p-5 backdrop-blur-sm">
        <h3 className="text-sm font-bold text-white">Sentiment Distribution</h3>
        <p className="text-xs text-neutral-400">Classified using Cardiff NLP Twitter-RoBERTa</p>

        <div className="mt-4 flex h-64 items-center justify-center">
          {total > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={95}
                  paddingAngle={2}
                  dataKey="value"
                  nameKey="name"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', borderRadius: '8px', fontSize: '12px' }}
                  itemStyle={{ color: '#ffffff' }}
                />
                <Legend verticalAlign="bottom" height={36} wrapperStyle={{ fontSize: '12px' }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-xs text-neutral-500">No sentiment data available</p>
          )}
        </div>
      </div>

      {/* 2. Sentiment Timeline */}
      <div className="rounded-2xl border border-neutral-800/80 bg-neutral-900/60 p-5 backdrop-blur-sm">
        <h3 className="text-sm font-bold text-white">Sentiment Timeline</h3>
        <p className="text-xs text-neutral-400">Daily percentage of positive, neutral, and negative posts over time</p>

        <div className="mt-4 h-72">
          {timeline && timeline.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={timeline}>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                <XAxis dataKey="date" stroke="#71717a" fontSize={11} />
                <YAxis stroke="#71717a" fontSize={11} unit="%" domain={[0, 100]} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', borderRadius: '8px', fontSize: '12px' }}
                  itemStyle={{ color: '#ffffff' }}
                />
                <Legend wrapperStyle={{ fontSize: '12px' }} />
                <Line type="monotone" dataKey="positive" stroke={STREAMLIT_COLORS.positive} strokeWidth={2.5} dot={{ r: 3 }} name="positive" />
                <Line type="monotone" dataKey="neutral" stroke={STREAMLIT_COLORS.neutral} strokeWidth={2.5} dot={{ r: 3 }} name="neutral" />
                <Line type="monotone" dataKey="negative" stroke={STREAMLIT_COLORS.negative} strokeWidth={2.5} dot={{ r: 3 }} name="negative" />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-full items-center justify-center">
              <p className="text-xs text-neutral-500">Timeline requires posts across multiple dates</p>
            </div>
          )}
        </div>
      </div>

      {/* 3. Sentiment by Platform */}
      <div className="rounded-2xl border border-neutral-800/80 bg-neutral-900/60 p-5 backdrop-blur-sm">
        <h3 className="text-sm font-bold text-white">Sentiment by Platform</h3>
        <p className="text-xs text-neutral-400">Percentage distribution normalized per platform (YouTube, Telegram, X)</p>

        <div className="mt-4 h-64">
          {computedPlatformData && computedPlatformData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={computedPlatformData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                <XAxis dataKey="platform" stroke="#71717a" fontSize={11} />
                <YAxis stroke="#71717a" fontSize={11} unit="%" domain={[0, 100]} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', borderRadius: '8px', fontSize: '12px' }}
                  itemStyle={{ color: '#ffffff' }}
                />
                <Legend wrapperStyle={{ fontSize: '12px' }} />
                <Bar dataKey="positive" fill={STREAMLIT_COLORS.positive} name="positive" radius={[4, 4, 0, 0]} />
                <Bar dataKey="neutral" fill={STREAMLIT_COLORS.neutral} name="neutral" radius={[4, 4, 0, 0]} />
                <Bar dataKey="negative" fill={STREAMLIT_COLORS.negative} name="negative" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-full items-center justify-center">
              <p className="text-xs text-neutral-500">No platform breakdown data available</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
