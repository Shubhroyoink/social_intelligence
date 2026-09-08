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
} from 'recharts';
import type { DemographicsSummary } from '../types';

interface DemographicsViewProps {
  demographics?: DemographicsSummary;
}

const PIE_COLORS = [
  '#6366f1', '#ec4899', '#8b5cf6', '#10b981', '#f59e0b',
  '#06b6d4', '#3b82f6', '#f43f5e', '#84cc16', '#14b8a6'
];

export const DemographicsView: React.FC<DemographicsViewProps> = ({
  demographics = { languages: {}, geo: {}, interests: {} },
}) => {
  const langData = Object.entries(demographics?.languages || {}).map(([language, count], i) => ({
    name: language.toUpperCase(),
    value: count,
    color: PIE_COLORS[i % PIE_COLORS.length],
  })).sort((a, b) => b.value - a.value);

  const geoData = Object.entries(demographics?.geo || {}).map(([region, count]) => ({
    region,
    count,
  })).sort((a, b) => a.count - b.count).slice(0, 15);

  const interestData = Object.entries(demographics?.interests || {}).map(([interest, count]) => ({
    interest,
    count,
  })).sort((a, b) => a.count - b.count);

  return (
    <div className="rounded-2xl border border-neutral-800/80 bg-neutral-900/60 p-5 backdrop-blur-sm space-y-6">
      <div className="border-b border-neutral-800 pb-3">
        <h3 className="text-base font-bold text-white">Demographics</h3>
        <p className="text-xs text-neutral-400">Inferred linguistic, geographic, and domain intelligence</p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Column 1: Language Distribution */}
        <div className="flex flex-col justify-between rounded-xl border border-neutral-800 bg-neutral-950/40 p-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-neutral-300">
            Language Distribution
          </h4>

          <div className="mt-2 h-56 flex items-center justify-center">
            {langData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={langData}
                    cx="50%"
                    cy="50%"
                    innerRadius={45}
                    outerRadius={75}
                    paddingAngle={3}
                    dataKey="value"
                    nameKey="name"
                  >
                    {langData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', borderRadius: '8px', fontSize: '12px' }}
                    itemStyle={{ color: '#ffffff' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-xs text-neutral-500">No language data</p>
            )}
          </div>
        </div>

        {/* Column 2: Geographic Mentions */}
        <div className="flex flex-col justify-between rounded-xl border border-neutral-800 bg-neutral-950/40 p-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-neutral-300">
            Geographic Mentions
          </h4>

          <div className="mt-2 h-56">
            {geoData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={geoData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" horizontal={false} />
                  <XAxis type="number" stroke="#71717a" fontSize={10} />
                  <YAxis type="category" dataKey="region" stroke="#71717a" fontSize={10} width={80} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', borderRadius: '8px', fontSize: '12px' }}
                    itemStyle={{ color: '#ffffff' }}
                  />
                  <Bar dataKey="count" fill="#f43f5e" radius={[0, 4, 4, 0]} name="Mentions" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center">
                <p className="text-xs text-neutral-500">No geographic data</p>
              </div>
            )}
          </div>
        </div>

        {/* Column 3: Professional Interests */}
        <div className="flex flex-col justify-between rounded-xl border border-neutral-800 bg-neutral-950/40 p-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-neutral-300">
            Professional Interests
          </h4>

          <div className="mt-2 h-56">
            {interestData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={interestData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" horizontal={false} />
                  <XAxis type="number" stroke="#71717a" fontSize={10} />
                  <YAxis type="category" dataKey="interest" stroke="#71717a" fontSize={10} width={85} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', borderRadius: '8px', fontSize: '12px' }}
                    itemStyle={{ color: '#ffffff' }}
                  />
                  <Bar dataKey="count" fill="#10b981" radius={[0, 4, 4, 0]} name="Posts" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center">
                <p className="text-xs text-neutral-500">No interest data</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
