import React, { useMemo } from 'react';
import { PlotlyChart } from './PlotlyChart';

interface SentimentViewProps {
  distribution?: Record<string, number>;
  by_platform?: Record<string, Record<string, number>>;
  platform_percentages?: Array<{ platform: string; positive: number; neutral: number; negative: number; total_count: number }>;
  timeline?: Array<{ date: string; positive: number; neutral: number; negative: number; count: number }>;
}

// High-contrast colors with clear visibility on white/light backgrounds
const STREAMLIT_COLORS = {
  positive: '#0284c7', // Rich vibrant blue
  neutral: '#475569',  // Solid slate / dark gray
  negative: '#dc2626', // Crimson red
};

export const SentimentView: React.FC<SentimentViewProps> = ({
  distribution = {},
  by_platform = {},
  platform_percentages = [],
  timeline = [],
}) => {
  // 1. Sentiment Distribution Pie Data
  const pieLabels = ['positive', 'neutral', 'negative'].filter(
    (k) => (distribution?.[k] || 0) > 0
  );
  const pieValues = pieLabels.map((k) => distribution?.[k] || 0);
  const pieColors = pieLabels.map((k) => STREAMLIT_COLORS[k as keyof typeof STREAMLIT_COLORS]);

  const pieChartData: Plotly.Data[] = [
    {
      labels: pieLabels,
      values: pieValues,
      type: 'pie',
      hole: 0.4,
      textinfo: 'label+percent',
      hoverinfo: 'label+value+percent',
      marker: {
        colors: pieColors,
        line: { color: '#000000', width: 2 },
      },
    },
  ];

  // 2. Exact Streamlit daily resampled Sentiment Timeline
  const { timelineDates, positiveVals, neutralVals, negativeVals, initialXRange } = useMemo(() => {
    if (!timeline || timeline.length === 0) {
      return { timelineDates: [], positiveVals: [], neutralVals: [], negativeVals: [], initialXRange: undefined };
    }

    const sorted = [...timeline].sort((a, b) => a.date.localeCompare(b.date));
    const dataMap = new Map<string, { positive: number; neutral: number; negative: number }>();
    sorted.forEach((item) => {
      dataMap.set(item.date, {
        positive: item.positive,
        neutral: item.neutral,
        negative: item.negative,
      });
    });

    const minDate = new Date(sorted[0].date);
    const maxDate = new Date(sorted[sorted.length - 1].date);

    const dates: string[] = [];
    const pos: (number | null)[] = [];
    const neu: (number | null)[] = [];
    const neg: (number | null)[] = [];

    // Daily resample from minDate to maxDate
    const curr = new Date(minDate);
    while (curr <= maxDate) {
      const dStr = curr.toISOString().slice(0, 10);
      dates.push(dStr);
      const entry = dataMap.get(dStr);
      if (entry) {
        pos.push(entry.positive);
        neu.push(entry.neutral);
        neg.push(entry.negative);
      } else {
        pos.push(null);
        neu.push(null);
        neg.push(null);
      }
      curr.setUTCDate(curr.getUTCDate() + 1);
    }

    // Default initial X view range: last ~3 years (e.g. Jul 2023 to Jul 2027) matching Streamlit view
    const xEnd = new Date(maxDate);
    xEnd.setMonth(xEnd.getMonth() + 6);
    const xStart = new Date(maxDate);
    xStart.setFullYear(xStart.getFullYear() - 3);

    return {
      timelineDates: dates,
      positiveVals: pos,
      neutralVals: neu,
      negativeVals: neg,
      initialXRange: [xStart.toISOString().slice(0, 10), xEnd.toISOString().slice(0, 10)] as [string, string],
    };
  }, [timeline]);

  const timelineChartData: Plotly.Data[] = [
    {
      x: timelineDates,
      y: positiveVals,
      name: 'positive',
      type: 'scatter',
      mode: 'lines',
      connectgaps: false,
      line: { color: STREAMLIT_COLORS.positive, width: 2 },
      hovertemplate: '%{x}<br>positive: %{y:.1f}%<extra></extra>',
    },
    {
      x: timelineDates,
      y: neutralVals,
      name: 'neutral',
      type: 'scatter',
      mode: 'lines',
      connectgaps: false,
      line: { color: STREAMLIT_COLORS.neutral, width: 2 },
      hovertemplate: '%{x}<br>neutral: %{y:.1f}%<extra></extra>',
    },
    {
      x: timelineDates,
      y: negativeVals,
      name: 'negative',
      type: 'scatter',
      mode: 'lines',
      connectgaps: false,
      line: { color: STREAMLIT_COLORS.negative, width: 2 },
      hovertemplate: '%{x}<br>negative: %{y:.1f}%<extra></extra>',
    },
  ];

  // 3. Sentiment by Platform Data
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

  const platforms = computedPlatformData.map((p) => p.platform);
  const platformChartData: Plotly.Data[] = [
    {
      x: platforms,
      y: computedPlatformData.map((p) => p.positive),
      name: 'positive',
      type: 'bar',
      marker: {
        color: STREAMLIT_COLORS.positive,
        line: { color: '#000000', width: 1.5 },
      },
      hovertemplate: '%{y:.1f}%<extra>positive</extra>',
    },
    {
      x: platforms,
      y: computedPlatformData.map((p) => p.neutral),
      name: 'neutral',
      type: 'bar',
      marker: {
        color: STREAMLIT_COLORS.neutral,
        line: { color: '#000000', width: 1.5 },
      },
      hovertemplate: '%{y:.1f}%<extra>neutral</extra>',
    },
    {
      x: platforms,
      y: computedPlatformData.map((p) => p.negative),
      name: 'negative',
      type: 'bar',
      marker: {
        color: STREAMLIT_COLORS.negative,
        line: { color: '#000000', width: 1.5 },
      },
      hovertemplate: '%{y:.1f}%<extra>negative</extra>',
    },
  ];

  const timelineLayout = useMemo(() => ({
    height: 480,
    dragmode: 'pan' as const,
    uirevision: 'sentiment_timeline_state',
    margin: { l: 55, r: 120, t: 25, b: 50 },
    xaxis: {
      title: { text: 'Date', font: { size: 12, color: '#000000' } },
      type: 'date' as const,
      range: initialXRange,
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
      title: { text: 'Sentiment', font: { size: 12, color: '#000000' } },
      orientation: 'v' as const,
      x: 1.02,
      y: 0.95,
      bgcolor: '#ffffff',
      bordercolor: '#000000',
      borderwidth: 2,
    },
  }), [initialXRange]);

  return (
    <div className="space-y-6">
      {/* 1. Sentiment Distribution */}
      <div className="rounded-lg border-2 border-black bg-white p-5 shadow-neo">
        <div className="flex items-center justify-between border-b-2 border-black pb-3">
          <div>
            <h3 className="text-base font-black text-black uppercase tracking-wide">Sentiment Distribution</h3>
            <p className="text-xs font-semibold text-neutral-600">Classified using Cardiff NLP Twitter-RoBERTa</p>
          </div>
          <span className="rounded-md border-2 border-black bg-neutral-100 px-2.5 py-0.5 text-[11px] font-black text-black shadow-neo-sm">
            Interactive Plotly
          </span>
        </div>

        <div className="mt-4">
          {pieValues.length > 0 ? (
            <PlotlyChart
              data={pieChartData}
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
              No sentiment data available
            </div>
          )}
        </div>
      </div>

      {/* 2. Sentiment Timeline (Exact Full Interactive Plotly with Pan/Zoom/Download) */}
      <div className="rounded-lg border-2 border-black bg-white p-5 shadow-neo">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b-2 border-black pb-3">
          <div>
            <h3 className="text-base font-black text-black uppercase tracking-wide">Sentiment Timeline</h3>
            <p className="text-xs font-semibold text-neutral-600">
              Daily percentage of positive, neutral, and negative posts • Drag to pan in any direction, scroll to zoom
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="rounded-md border-2 border-black bg-black px-2.5 py-0.5 text-[11px] font-black text-white shadow-neo-sm">
              Pan & Scroll Zoom Active
            </span>
          </div>
        </div>

        <div className="mt-4">
          {timelineDates.length > 0 ? (
            <PlotlyChart
              data={timelineChartData}
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

      {/* 3. Sentiment by Platform */}
      <div className="rounded-lg border-2 border-black bg-white p-5 shadow-neo">
        <div className="flex items-center justify-between border-b-2 border-black pb-3">
          <div>
            <h3 className="text-base font-black text-black uppercase tracking-wide">Sentiment by Platform</h3>
            <p className="text-xs font-semibold text-neutral-600">
              Percentage distribution normalized per platform (YouTube, Telegram, X)
            </p>
          </div>
        </div>

        <div className="mt-4">
          {computedPlatformData.length > 0 ? (
            <PlotlyChart
              data={platformChartData}
              layout={{
                barmode: 'group',
                height: 320,
                margin: { l: 55, r: 25, t: 25, b: 45 },
                dragmode: false,
                xaxis: {
                  title: { text: 'Platform', font: { size: 12, color: '#000000' } },
                  tickfont: { color: '#000000', size: 11 },
                  fixedrange: true,
                },
                yaxis: {
                  title: { text: 'Percentage', font: { size: 12, color: '#000000' } },
                  tickfont: { color: '#000000', size: 11 },
                  range: [0, 100],
                  ticksuffix: '%',
                  fixedrange: true,
                  showgrid: true,
                  gridcolor: '#e5e7eb',
                },
                legend: {
                  orientation: 'h',
                  x: 0.3,
                  y: 1.15,
                  font: { size: 11, color: '#000000' },
                },
              }}
              className="h-80 w-full"
            />
          ) : (
            <div className="flex h-64 items-center justify-center text-xs font-bold text-neutral-500">
              No platform breakdown data available
            </div>
          )}
        </div>
      </div>
    </div>
  );
};


