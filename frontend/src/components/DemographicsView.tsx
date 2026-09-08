import React from 'react';
import { PlotlyChart } from './PlotlyChart';
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
  const languages = demographics?.languages || {};
  const geo = demographics?.geo || {};
  const interests = demographics?.interests || {};

  const langEntries = Object.entries(languages).sort((a, b) => b[1] - a[1]);
  const geoEntries = Object.entries(geo).sort((a, b) => a[1] - b[1]).slice(0, 15);
  const interestEntries = Object.entries(interests).sort((a, b) => a[1] - b[1]);

  return (
    <div className="rounded-2xl border border-neutral-800/80 bg-neutral-900/60 p-5 backdrop-blur-sm space-y-6">
      <div className="border-b border-neutral-800 pb-3">
        <h3 className="text-base font-bold text-white">Demographics</h3>
        <p className="text-xs text-neutral-400">Inferred linguistic, geographic, and domain intelligence</p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Column 1: Language Distribution */}
        <div className="flex flex-col justify-between rounded-xl border border-neutral-800 bg-neutral-950/40 p-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-neutral-300 mb-2">
            Language Distribution
          </h4>

          <div className="h-64 flex items-center justify-center">
            {langEntries.length > 0 ? (
              <PlotlyChart
                className="w-full h-full"
                data={[
                  {
                    labels: langEntries.map(([k]) => k.toUpperCase()),
                    values: langEntries.map(([, v]) => v),
                    type: 'pie',
                    hole: 0.4,
                    marker: { colors: PIE_COLORS },
                    textinfo: 'label+percent',
                    hoverinfo: 'label+value+percent',
                  } as any,
                ]}
                layout={{
                  showlegend: true,
                  legend: { orientation: 'h', y: -0.2, x: 0 },
                  margin: { l: 15, r: 15, t: 15, b: 20 },
                }}
              />
            ) : (
              <p className="text-xs text-neutral-500">No language data</p>
            )}
          </div>
        </div>

        {/* Column 2: Geographic Mentions */}
        <div className="flex flex-col justify-between rounded-xl border border-neutral-800 bg-neutral-950/40 p-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-neutral-300 mb-2">
            Geographic Mentions
          </h4>

          <div className="h-64">
            {geoEntries.length > 0 ? (
              <PlotlyChart
                className="w-full h-full"
                data={[
                  {
                    x: geoEntries.map(([, v]) => v),
                    y: geoEntries.map(([k]) => k),
                    type: 'bar',
                    orientation: 'h',
                    marker: { color: '#f43f5e' },
                    hoverinfo: 'x+y',
                  } as any,
                ]}
                layout={{
                  xaxis: { title: { text: 'Mentions', font: { size: 10 } } },
                  yaxis: { automargin: true },
                  margin: { l: 80, r: 20, t: 15, b: 35 },
                }}
              />
            ) : (
              <div className="flex h-full items-center justify-center">
                <p className="text-xs text-neutral-500">No geographic data</p>
              </div>
            )}
          </div>
        </div>

        {/* Column 3: Professional Interests */}
        <div className="flex flex-col justify-between rounded-xl border border-neutral-800 bg-neutral-950/40 p-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-neutral-300 mb-2">
            Professional Interests
          </h4>

          <div className="h-64">
            {interestEntries.length > 0 ? (
              <PlotlyChart
                className="w-full h-full"
                data={[
                  {
                    x: interestEntries.map(([, v]) => v),
                    y: interestEntries.map(([k]) => k),
                    type: 'bar',
                    orientation: 'h',
                    marker: { color: '#10b981' },
                    hoverinfo: 'x+y',
                  } as any,
                ]}
                layout={{
                  xaxis: { title: { text: 'Posts', font: { size: 10 } } },
                  yaxis: { automargin: true },
                  margin: { l: 85, r: 20, t: 15, b: 35 },
                }}
              />
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

