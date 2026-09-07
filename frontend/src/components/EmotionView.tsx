import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  PieChart,
  Pie,
  Legend,
  LineChart,
  Line,
} from 'recharts';

interface EmotionViewProps {
  emotion_counts?: Record<string, number>;
  stance_counts?: Record<string, number>;
  sarcasm_pct?: number;
  timeline?: Array<Record<string, any>>;
}

const EMOTION_COLORS: Record<string, string> = {
  anger: '#e74c3c',
  disgust: '#8e44ad',
  fear: '#e67e22',
  joy: '#2ecc71',
  neutral: '#95a5a6',
  sadness: '#3498db',
  surprise: '#f1c40f',
};

const STANCE_COLORS: Record<string, string> = {
  supportive: '#2ca02c',
  against: '#d62728',
  neutral: '#999999',
};

export const EmotionView: React.FC<EmotionViewProps> = ({
  emotion_counts = {},
  stance_counts = {},
  sarcasm_pct = 0,
  timeline = [],
}) => {
  const totalEmotions = Object.values(emotion_counts || {}).reduce((a, b) => a + b, 0);

  const emotionData = Object.entries(emotion_counts || {}).map(([emotion, count]) => ({
    emotion,
    count,
    color: EMOTION_COLORS[emotion] || '#95a5a6',
  })).sort((a, b) => a.count - b.count);

  const stanceData = Object.entries(stance_counts || {}).map(([stance, count]) => ({
    name: stance,
    value: count,
    color: STANCE_COLORS[stance] || '#999999',
  })).filter((d) => d.value > 0);

  return (
    <div className="space-y-6">
      {/* 1. Emotion Analysis Header Row */}
      <div className="rounded-2xl border border-neutral-800/80 bg-neutral-900/60 p-5 backdrop-blur-sm">
        <h3 className="text-base font-bold text-white">Emotion Analysis</h3>
        
        <div className="mt-4 grid grid-cols-1 gap-6 lg:grid-cols-4">
          {/* Left Column */}
          <div className="space-y-4 border-b border-neutral-800 pb-4 lg:border-b-0 lg:border-r lg:pr-6">
            <div>
              <span className="text-xs font-semibold text-neutral-400">Sarcasm Detected</span>
              <div className="text-2xl font-bold text-white mt-0.5">{(sarcasm_pct || 0).toFixed(1)}%</div>
            </div>

            <div className="space-y-2 pt-2 border-t border-neutral-800">
              <span className="text-xs font-bold text-white block">Stance Breakdown</span>
              {Object.entries(stance_counts || {}).map(([stance, count]) => {
                const pct = totalEmotions > 0 ? (count / totalEmotions) * 100 : 0;
                return (
                  <div key={stance} className="text-xs text-neutral-300">
                    <span className="font-semibold text-neutral-200">{stance}:</span> {count} ({pct.toFixed(1)}%)
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right Column */}
          <div className="lg:col-span-3 h-64">
            {emotionData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={emotionData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" horizontal={false} />
                  <XAxis type="number" stroke="#71717a" fontSize={11} />
                  <YAxis type="category" dataKey="emotion" stroke="#71717a" fontSize={11} width={65} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', borderRadius: '8px', fontSize: '12px' }}
                    itemStyle={{ color: '#ffffff' }}
                  />
                  <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                    {emotionData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center">
                <p className="text-xs text-neutral-500">No emotion data available</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 2. Emotion Timeline */}
      <div className="rounded-2xl border border-neutral-800/80 bg-neutral-900/60 p-5 backdrop-blur-sm">
        <h3 className="text-sm font-bold text-white">Emotion Timeline</h3>
        <p className="text-xs text-neutral-400">Daily percentage breakdown across all 7 primary emotions</p>

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
                {Object.keys(EMOTION_COLORS).map((emoKey) => (
                  <Line
                    key={emoKey}
                    type="monotone"
                    dataKey={emoKey}
                    stroke={EMOTION_COLORS[emoKey]}
                    strokeWidth={2}
                    dot={{ r: 2 }}
                    name={emoKey}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-full items-center justify-center">
              <p className="text-xs text-neutral-500">Emotion timeline requires posts across multiple dates</p>
            </div>
          )}
        </div>
      </div>

      {/* 3. Stance Analysis */}
      <div className="rounded-2xl border border-neutral-800/80 bg-neutral-900/60 p-5 backdrop-blur-sm">
        <h3 className="text-sm font-bold text-white">Stance Analysis</h3>
        <p className="text-xs text-neutral-400">Distribution of Supportive, Against, and Neutral perspectives</p>

        <div className="mt-4 flex h-64 items-center justify-center">
          {stanceData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={stanceData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={90}
                  paddingAngle={3}
                  dataKey="value"
                  nameKey="name"
                >
                  {stanceData.map((entry, index) => (
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
            <p className="text-xs text-neutral-500">No stance data available</p>
          )}
        </div>
      </div>
    </div>
  );
};
