import React, { useMemo, useState } from 'react';
import { PlotlyChart } from './PlotlyChart';
import { Compass, Sparkles, X, ChevronDown, ChevronUp, PieChart, ShieldCheck } from 'lucide-react';

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
  const [showStanceAnalysis, setShowStanceAnalysis] = useState(false);
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
      labels: stanceKeys.map((k) => k.charAt(0).toUpperCase() + k.slice(1)),
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
      <div className="rounded-lg border-2 border-black bg-white p-5 shadow-neo space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b-2 border-black pb-4">
          <div>
            <h3 className="text-base font-black text-black uppercase tracking-wide flex items-center gap-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-md border-2 border-black bg-black text-white shadow-neo-sm">
                <Sparkles className="h-4 w-4 fill-white" />
              </span>
              Emotion Analysis & Affect Detection
            </h3>
            <p className="text-xs font-semibold text-neutral-600 mt-1">
              7-dimensional affective classification via transformer model
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {/* Model Badge */}
            <span className="rounded-md border-2 border-black bg-neutral-100 px-2.5 py-1 text-[11px] font-black text-black shadow-neo-sm">
              j-hartmann/emotion-distilroberta
            </span>

            {/* View Stance Analysis Feature Button */}
            <button
              onClick={() => setShowStanceAnalysis((prev) => !prev)}
              className={`neo-btn flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-black transition-all ${
                showStanceAnalysis
                  ? 'bg-black text-white shadow-neo-sm translate-x-[1px] translate-y-[1px]'
                  : 'bg-white text-black border-2 border-black hover:bg-neutral-100 shadow-neo-sm'
              }`}
            >
              <Compass className={`h-3.5 w-3.5 stroke-[2.5] ${showStanceAnalysis ? 'text-white' : 'text-black'}`} />
              <span>{showStanceAnalysis ? 'Hide Stance Analysis' : 'View Stance Analysis'}</span>
              {showStanceAnalysis ? (
                <ChevronUp className="h-3.5 w-3.5 stroke-[2.5]" />
              ) : (
                <ChevronDown className="h-3.5 w-3.5 stroke-[2.5]" />
              )}
            </button>
          </div>
        </div>

        {/* Emotion Metrics & Bar Chart */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
          {/* Left Column (Sarcasm & Emotion Distribution) */}
          <div className="space-y-4 border-b-2 border-black pb-4 lg:border-b-0 lg:border-r-2 lg:pr-6">
            <div className="rounded-lg border-2 border-black bg-neutral-100 p-3 shadow-neo-sm">
              <span className="text-xs font-black uppercase text-neutral-600">Sarcasm Detected</span>
              <div className="text-2xl font-black text-black mt-0.5">
                {(sarcasm_pct || 0).toFixed(1)}%
              </div>
              <p className="text-[10px] font-bold text-neutral-500 mt-1">Linguistic irony & figurative tone</p>
            </div>

            <div className="rounded-lg border-2 border-black bg-neutral-50 p-3 shadow-neo-sm">
              <span className="text-xs font-black uppercase text-neutral-600">Total Analyzed</span>
              <div className="text-2xl font-black text-black mt-0.5">
                {totalEmotions.toLocaleString()}
              </div>
              <p className="text-[10px] font-bold text-neutral-500 mt-1">Emotion-tagged posts</p>
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

        {/* Dynamic Embedded Stance Analysis Section (Shown only when toggled) */}
        {showStanceAnalysis && (
          <div className="mt-4 pt-4 border-t-2 border-black space-y-4 bg-neutral-50 p-4 rounded-lg border-2 shadow-neo-sm">
            <div className="flex items-center justify-between border-b-2 border-black pb-2.5">
              <div className="flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center rounded border-2 border-black bg-black text-white shadow-neo-sm">
                  <Compass className="h-3.5 w-3.5" />
                </span>
                <h4 className="text-xs font-black uppercase tracking-wider text-black">
                  Inferred Stance Analysis & Orientation
                </h4>
                <span className="rounded bg-black px-1.5 py-0.5 text-[9px] font-black text-white uppercase">
                  Active View
                </span>
              </div>
              <button
                onClick={() => setShowStanceAnalysis(false)}
                className="rounded border border-black bg-white p-1 hover:bg-neutral-200"
                title="Close Stance Section"
              >
                <X className="h-3.5 w-3.5 text-black stroke-[2.5]" />
              </button>
            </div>

            <p className="text-xs font-semibold text-neutral-700">
              Inferred viewpoint polarity classifying whether post discourse is <strong>Supportive</strong>, <strong>Against</strong>, or <strong>Neutral</strong> towards the topic.
            </p>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-3 items-center">
              {/* Stance Breakdown Cards */}
              <div className="space-y-2">
                {Object.entries(stance_counts || {}).map(([stance, count]) => {
                  const pct = totalEmotions > 0 ? (count / totalEmotions) * 100 : 0;
                  const color = STANCE_COLORS[stance] || '#475569';
                  return (
                    <div
                      key={stance}
                      className="rounded-lg border-2 border-black bg-white p-3 shadow-neo-sm flex items-center justify-between"
                    >
                      <div className="flex items-center gap-2">
                        <span
                          className="h-3 w-3 rounded-full border border-black inline-block"
                          style={{ backgroundColor: color }}
                        ></span>
                        <span className="text-xs font-black uppercase text-black">{stance}</span>
                      </div>
                      <div className="text-right">
                        <span className="text-xs font-mono font-black text-black block">{count} posts</span>
                        <span className="text-[10px] font-bold text-neutral-600">{pct.toFixed(1)}%</span>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Stance Pie Chart */}
              <div className="lg:col-span-2">
                {stanceKeys.length > 0 ? (
                  <PlotlyChart
                    data={stancePieData}
                    layout={{
                      height: 250,
                      margin: { l: 20, r: 20, t: 10, b: 20 },
                      showlegend: true,
                      legend: { orientation: 'h', x: 0.2, y: -0.1 },
                    }}
                    className="h-64 w-full"
                  />
                ) : (
                  <div className="flex h-48 items-center justify-center text-xs font-bold text-neutral-500">
                    No stance data available
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 2. Emotion Timeline (Interactive Pan/Zoom) */}
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
    </div>
  );
};
