import React, { useMemo } from 'react';
import { PlotlyChart } from './PlotlyChart';

interface EmotionViewProps {
  emotion_counts?: Record<string, number>;
  stance_counts?: Record<string, number>;
  sarcasm_pct?: number;
  timeline?: Array<Record<string, any>>;
}

const EMOTION_COLORS: Record<string, string> = {
  anger: '#dc2626',
  disgust: '#7c3aed',
  fear: '#ea580c',
  joy: '#16a34a',
  neutral: '#475569',
  sadness: '#0284c7',
  surprise: '#ca8a04',
};

const STANCE_COLORS: Record<string, string> = {
  supportive: '#16a34a',
  against: '#dc2626',
  neutral: '#475569',
};

export const EmotionView: React.FC<EmotionViewProps> = ({
  emotion_counts = {},
  stance_counts = {},
  sarcasm_pct = 0,
  timeline = [],
}) => {
  const totalEmotions = Object.values(emotion_counts || {}).reduce((a, b) => a + b, 0);

  // 1. Emotion Horizontal Bar Data
  const emotionEntries = Object.entries(emotion_counts || {}).sort((a, b) => a[1] - b[1]);
  const emotionBarData: Plotly.Data[] = [
    {
      x: emotionEntries.map((e) => e[1]),
      y: emotionEntries.map((e) => e[0]),
      type: 'bar',
      orientation: 'h',
      marker: {
        color: emotionEntries.map((e) => EMOTION_COLORS[e[0]] || '#475569'),
        line: { color: '#000000', width: 1.5 },
      },
      hovertemplate: '%{y}: %{x} posts<extra></extra>',
    },
  ];

  // 2. Exact Streamlit daily resampled Emotion Timeline
  const { timelineDates, resampledEmotions } = useMemo(() => {
    if (!timeline || timeline.length === 0) {
      return { timelineDates: [], resampledEmotions: {} };
    }

    const sorted = [...timeline].sort((a, b) => (a.date || '').localeCompare(b.date || ''));
    const dataMap = new Map<string, Record<string, any>>();
    sorted.forEach((item) => {
      if (item.date) dataMap.set(item.date, item);
    });

    const minDate = new Date(sorted[0].date);
    const maxDate = new Date(sorted[sorted.length - 1].date);

    const dates: string[] = [];
    const res: Record<string, (number | null)[]> = {};
    Object.keys(EMOTION_COLORS).forEach((k) => { res[k] = []; });

    const curr = new Date(minDate);
    while (curr <= maxDate) {
      const dStr = curr.toISOString().slice(0, 10);
      dates.push(dStr);
      const entry = dataMap.get(dStr);
      Object.keys(EMOTION_COLORS).forEach((emoKey) => {
        res[emoKey].push(entry && entry[emoKey] !== undefined ? entry[emoKey] : null);
      });
      curr.setUTCDate(curr.getUTCDate() + 1);
    }

    return { timelineDates: dates, resampledEmotions: res };
  }, [timeline]);

  const emotionTimelineData: Plotly.Data[] = Object.keys(EMOTION_COLORS).map((emoKey) => ({
    x: timelineDates,
    y: resampledEmotions[emoKey] || [],
    name: emoKey,
    type: 'scatter',
    mode: 'lines',
    connectgaps: false,
    line: { color: EMOTION_COLORS[emoKey], width: 1.8 },
    hovertemplate: `%{x}<br>${emoKey}: %{y:.1f}%<extra></extra>`,
  }));

  // 3. Stance Pie Data
  const stanceKeys = Object.keys(stance_counts || {}).filter((k) => (stance_counts?.[k] || 0) > 0);
  const stancePieData: Plotly.Data[] = [
    {
      labels: stanceKeys,
      values: stanceKeys.map((k) => stance_counts?.[k] || 0),
      type: 'pie',
      hole: 0.4,
      marker: {
        colors: stanceKeys.map((k) => STANCE_COLORS[k] || '#475569'),
        line: { color: '#000000', width: 2 },
      },
      hoverinfo: 'label+value+percent',
    },
  ];

  const timelineLayout = useMemo(() => ({
    height: 480,
    dragmode: 'pan' as const,
    uirevision: 'emotion_timeline_state',
    margin: { l: 55, r: 120, t: 25, b: 50 },
    xaxis: {
      title: { text: 'Date', font: { size: 12, color: '#000000' } },
      type: 'date' as const,
      fixedrange: false,
      showgrid: true,
      gridcolor: '#e5e7eb',
      tickfont: { color: '#000000', size: 10 },
    },
    yaxis: {
      title: { text: 'Percentage', font: { size: 12, color: '#000000' } },
      range: [-2, 48],
      dtick: 10,
      fixedrange: false,
      showgrid: true,
      gridcolor: '#e5e7eb',
      tickfont: { color: '#000000', size: 10 },
    },
    legend: {
      title: { text: 'Emotion', font: { size: 12, color: '#000000' } },
      orientation: 'v' as const,
      x: 1.02,
      y: 0.95,
      bgcolor: '#ffffff',
      bordercolor: '#000000',
      borderwidth: 2,
    },
  }), []);

  return (
    <div className="space-y-6">
      {/* 1. Emotion Analysis Header Row */}
      <div className="rounded-lg border-2 border-black bg-white p-5 shadow-neo">
        <div className="flex items-center justify-between border-b-2 border-black pb-3">
          <h3 className="text-base font-black text-black uppercase tracking-wide">Emotion Analysis</h3>
          <span className="rounded-md border-2 border-black bg-neutral-100 px-2.5 py-0.5 text-[11px] font-black text-black shadow-neo-sm">
            j-hartmann/emotion-distilroberta
          </span>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-6 lg:grid-cols-4">
          {/* Left Column (Sarcasm + Stance Text) */}
          <div className="space-y-4 border-b-2 border-black pb-4 lg:border-b-0 lg:border-r-2 lg:pr-6">
            <div className="rounded-lg border-2 border-black bg-neutral-100 p-3 shadow-neo-sm">
              <span className="text-xs font-black uppercase text-neutral-600">Sarcasm Detected</span>
              <div className="text-2xl font-black text-black mt-0.5">
                {(sarcasm_pct || 0).toFixed(1)}%
              </div>
            </div>

            <div className="space-y-2 pt-2 border-t-2 border-black">
              <span className="text-xs font-black uppercase tracking-wide text-black block">Stance Breakdown</span>
              {Object.entries(stance_counts || {}).map(([stance, count]) => {
                const pct = totalEmotions > 0 ? (count / totalEmotions) * 100 : 0;
                return (
                  <div key={stance} className="text-xs text-black flex justify-between font-bold py-1 border-b border-neutral-200">
                    <span className="capitalize">{stance}:</span>
                    <span className="font-black text-black">
                      {count} ({pct.toFixed(1)}%)
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right Column (Horizontal Bar Chart) */}
          <div className="lg:col-span-3">
            {emotionEntries.length > 0 ? (
              <PlotlyChart
                data={emotionBarData}
                layout={{
                  height: 260,
                  margin: { l: 85, r: 20, t: 20, b: 35 },
                  xaxis: { title: { text: 'Posts', font: { size: 11, color: '#000000' } }, tickfont: { color: '#000000', size: 10 } },
                  yaxis: { title: { text: 'Emotion', standoff: 20, font: { size: 11, color: '#000000' } }, tickfont: { color: '#000000', size: 10 }, dtick: 1, automargin: true },
                }}
                className="h-64 w-full"
              />
            ) : (
              <div className="flex h-64 items-center justify-center text-xs font-bold text-neutral-500">
                No emotion data available
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 2. Emotion Timeline (Interactive Pan/Zoom/Download) */}
      <div className="rounded-lg border-2 border-black bg-white p-5 shadow-neo">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b-2 border-black pb-3">
          <div>
            <h3 className="text-base font-black text-black uppercase tracking-wide">Emotion Timeline</h3>
            <p className="text-xs font-semibold text-neutral-600">
              Daily percentage breakdown across all 7 primary emotions • Zoom, pan, or isolate dimensions
            </p>
          </div>
          <span className="rounded-md border-2 border-black bg-neutral-100 px-2.5 py-0.5 text-[11px] font-black text-black shadow-neo-sm">
            7 Dimensions
          </span>
        </div>

        <div className="mt-4">
          {timelineDates.length > 0 ? (
            <PlotlyChart
              data={emotionTimelineData}
              layout={timelineLayout}
              className="h-[520px] w-full"
            />
          ) : (
            <div className="flex h-64 items-center justify-center text-xs font-bold text-neutral-500">
              Timeline requires posts across multiple dates
            </div>
          )}
        </div>
      </div>

      {/* 3. Stance Analysis */}
      <div className="rounded-lg border-2 border-black bg-white p-5 shadow-neo">
        <div className="flex items-center justify-between border-b-2 border-black pb-3">
          <div>
            <h3 className="text-base font-black text-black uppercase tracking-wide">Stance Analysis</h3>
            <p className="text-xs font-semibold text-neutral-600">Inferred viewpoint orientation (supportive, against, neutral)</p>
          </div>
        </div>

        <div className="mt-4">
          {stanceKeys.length > 0 ? (
            <PlotlyChart
              data={stancePieData}
              layout={{
                height: 280,
                margin: { l: 20, r: 20, t: 10, b: 20 },
                showlegend: true,
                legend: { orientation: 'h', x: 0.25, y: -0.1 },
              }}
              className="h-72 w-full"
            />
          ) : (
            <div className="flex h-64 items-center justify-center text-xs font-bold text-neutral-500">
              No stance data available
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
