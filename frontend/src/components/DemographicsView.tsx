import React, { useState } from 'react';
import { PlotlyChart } from './PlotlyChart';
import type { DemographicsSummary } from '../types';
import { Maximize2, X, Minimize2 } from 'lucide-react';

interface DemographicsViewProps {
  demographics?: DemographicsSummary;
}

// ISO 639-1 Language Code to Full English Name Dictionary
const LANGUAGE_NAMES: Record<string, string> = {
  en: 'English',
  it: 'Italian',
  es: 'Spanish',
  fr: 'French',
  de: 'German',
  hi: 'Hindi',
  zh: 'Chinese',
  ja: 'Japanese',
  ko: 'Korean',
  ar: 'Arabic',
  ru: 'Russian',
  pt: 'Portuguese',
  nl: 'Dutch',
  tr: 'Turkish',
  id: 'Indonesian',
  so: 'Somali',
  af: 'Afrikaans',
  no: 'Norwegian',
  ca: 'Catalan',
  tl: 'Tagalog',
  da: 'Danish',
  et: 'Estonian',
  sw: 'Swahili',
  sq: 'Albanian',
  pl: 'Polish',
  sv: 'Swedish',
  fi: 'Finnish',
  vi: 'Vietnamese',
  th: 'Thai',
  cs: 'Czech',
  el: 'Greek',
  he: 'Hebrew',
  uk: 'Ukrainian',
  ro: 'Romanian',
  hu: 'Hungarian',
  cy: 'Welsh',
  bn: 'Bengali',
  ta: 'Tamil',
  te: 'Telugu',
  mr: 'Marathi',
  ur: 'Urdu',
  gu: 'Gujarati',
  kn: 'Kannada',
  ml: 'Malayalam',
  pa: 'Punjabi',
  unknown: 'Undetected / Unknown',
};

export function formatLanguageLabel(code: string): string {
  const clean = (code || '').toLowerCase().trim();
  const name = LANGUAGE_NAMES[clean];
  if (name) {
    return `${name} (${clean.toUpperCase()})`;
  }
  return clean ? clean.toUpperCase() : 'Unknown';
}

// Streamlit Plotly Express discrete palette
const PIE_COLORS = [
  '#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A',
  '#19D3F3', '#FF6692', '#B6E880', '#FF97FF', '#FECB52'
];

const STREAMLIT_BAR_COLOR = '#7ec8fc'; // Sky blue matching visual stream.png

export const DemographicsView: React.FC<DemographicsViewProps> = ({
  demographics = { languages: {}, geo: {}, interests: {} },
}) => {
  const [fullscreenModal, setFullscreenModal] = useState<null | 'all' | 'language' | 'geo' | 'interests'>(null);

  const languages = demographics?.languages || {};
  const geo = demographics?.geo || {};
  const interests = demographics?.interests || {};

  const langEntries = Object.entries(languages).sort((a, b) => b[1] - a[1]);
  const geoEntries = Object.entries(geo).sort((a, b) => a[1] - b[1]).slice(0, 15);
  const interestEntries = Object.entries(interests).sort((a, b) => a[1] - b[1]);

  // 1. Language Pie Trace (Human-readable language names + clear judge-friendly hover text)
  const langChartData: Plotly.Data[] = [
    {
      labels: langEntries.map(([code]) => formatLanguageLabel(code)),
      values: langEntries.map(([, v]) => v),
      type: 'pie',
      hole: 0.4,
      marker: { colors: PIE_COLORS },
      textinfo: 'percent',
      textposition: 'inside',
      insidetextorientation: 'horizontal',
      hovertemplate: '<b>%{label}</b><br>Volume: <b>%{value} posts</b><br>Share: <b>%{percent}</b><extra></extra>',
    } as any,
  ];

  // 2. Geographic Mentions Bar Trace
  const geoChartData: Plotly.Data[] = [
    {
      x: geoEntries.map(([, v]) => v),
      y: geoEntries.map(([k]) => k),
      type: 'bar',
      orientation: 'h',
      marker: { color: STREAMLIT_BAR_COLOR },
      hovertemplate: '<b>Region: %{y}</b><br>Mentions: <b>%{x} posts</b><extra></extra>',
    } as any,
  ];

  // 3. Professional Interests Bar Trace
  const interestChartData: Plotly.Data[] = [
    {
      x: interestEntries.map(([, v]) => v),
      y: interestEntries.map(([k]) => k),
      type: 'bar',
      orientation: 'h',
      marker: { color: STREAMLIT_BAR_COLOR },
      hovertemplate: '<b>Category: %{y}</b><br>Posts: <b>%{x} posts</b><extra></extra>',
    } as any,
  ];

  return (
    <div className="rounded-2xl border border-neutral-800/80 bg-neutral-900/60 p-5 backdrop-blur-sm space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
        <div>
          <h3 className="text-base font-bold text-white">Demographics</h3>
          <p className="text-xs text-neutral-400">Inferred linguistic, geographic, and domain intelligence</p>
        </div>
        <button
          onClick={() => setFullscreenModal('all')}
          className="flex items-center gap-1.5 rounded-lg border border-neutral-700 bg-neutral-800/80 px-3 py-1.5 text-xs font-semibold text-neutral-300 hover:bg-neutral-700 hover:text-white transition-colors"
          title="Open Fullscreen Demographics View"
        >
          <Maximize2 className="h-3.5 w-3.5" />
          Fullscreen
        </button>
      </div>

      {/* 3 Columns Row matching Streamlit visual stream.png */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Column 1: Language Distribution */}
        <div className="rounded-xl border border-neutral-800 bg-neutral-950/60 p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-xs font-bold uppercase tracking-wider text-neutral-300">
              Language Distribution
            </h4>
            <button
              onClick={() => setFullscreenModal('language')}
              className="text-neutral-500 hover:text-neutral-300 p-1"
              title="Expand chart"
            >
              <Maximize2 className="h-3.5 w-3.5" />
            </button>
          </div>

          <div className="h-[420px] flex items-center justify-center">
            {langEntries.length > 0 ? (
              <PlotlyChart
                className="w-full h-full"
                data={langChartData}
                layout={{
                  height: 420,
                  showlegend: true,
                  legend: {
                    orientation: 'v',
                    x: 1.02,
                    y: 0.95,
                    bgcolor: 'transparent',
                    font: { size: 11, color: '#e4e4e7' },
                  },
                  margin: { l: 10, r: 80, t: 10, b: 10 },
                }}
              />
            ) : (
              <p className="text-xs text-neutral-500">No language data</p>
            )}
          </div>
        </div>

        {/* Column 2: Geographic Mentions */}
        <div className="rounded-xl border border-neutral-800 bg-neutral-950/60 p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-xs font-bold uppercase tracking-wider text-neutral-300">
              Geographic Mentions
            </h4>
            <button
              onClick={() => setFullscreenModal('geo')}
              className="text-neutral-500 hover:text-neutral-300 p-1"
              title="Expand chart"
            >
              <Maximize2 className="h-3.5 w-3.5" />
            </button>
          </div>

          <div className="h-[420px]">
            {geoEntries.length > 0 ? (
              <PlotlyChart
                className="w-full h-full"
                data={geoChartData}
                layout={{
                  height: 420,
                  xaxis: {
                    title: { text: 'Mentions', font: { size: 11, color: '#e4e4e7' } },
                    gridcolor: 'rgba(255, 255, 255, 0.08)',
                  },
                  yaxis: {
                    title: { text: 'Region', font: { size: 11, color: '#e4e4e7' } },
                    automargin: true,
                    categoryorder: 'total ascending',
                    dtick: 1,
                    tickfont: { size: 11, color: '#e4e4e7' },
                  },
                  margin: { l: 90, r: 20, t: 15, b: 45 },
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
        <div className="rounded-xl border border-neutral-800 bg-neutral-950/60 p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-xs font-bold uppercase tracking-wider text-neutral-300">
              Professional Interests
            </h4>
            <button
              onClick={() => setFullscreenModal('interests')}
              className="text-neutral-500 hover:text-neutral-300 p-1"
              title="Expand chart"
            >
              <Maximize2 className="h-3.5 w-3.5" />
            </button>
          </div>

          <div className="h-[420px]">
            {interestEntries.length > 0 ? (
              <PlotlyChart
                className="w-full h-full"
                data={interestChartData}
                layout={{
                  height: 420,
                  xaxis: {
                    title: { text: 'Posts', font: { size: 11, color: '#e4e4e7' } },
                    gridcolor: 'rgba(255, 255, 255, 0.08)',
                  },
                  yaxis: {
                    title: { text: 'Category', font: { size: 11, color: '#e4e4e7' } },
                    automargin: true,
                    categoryorder: 'total ascending',
                    dtick: 1,
                    tickfont: { size: 11, color: '#e4e4e7' },
                  },
                  margin: { l: 110, r: 20, t: 15, b: 45 },
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

      {/* FULLSCREEN MODAL */}
      {fullscreenModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-md">
          <div className="relative flex h-[92vh] w-[95vw] flex-col rounded-2xl border border-neutral-700 bg-neutral-950 p-6 shadow-2xl">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-neutral-800 pb-4">
              <div>
                <h2 className="text-lg font-bold text-white">
                  {fullscreenModal === 'all' && 'Demographics Overview (Fullscreen)'}
                  {fullscreenModal === 'language' && 'Language Distribution (Fullscreen)'}
                  {fullscreenModal === 'geo' && 'Geographic Mentions (Fullscreen)'}
                  {fullscreenModal === 'interests' && 'Professional Interests (Fullscreen)'}
                </h2>
                <p className="text-xs text-neutral-400">
                  Full resolution interactive canvas • Zoom, pan, and inspect data points
                </p>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setFullscreenModal(null)}
                  className="flex items-center gap-1 rounded-lg border border-neutral-700 bg-neutral-850 px-3 py-1.5 text-xs font-semibold text-neutral-300 hover:bg-neutral-700 hover:text-white"
                >
                  <Minimize2 className="h-4 w-4" /> Close Fullscreen
                </button>
                <button
                  onClick={() => setFullscreenModal(null)}
                  className="rounded-lg p-1 text-neutral-400 hover:bg-neutral-800 hover:text-white"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

            {/* Modal Content */}
            <div className="flex-1 overflow-auto pt-4">
              {fullscreenModal === 'all' && (
                <div className="grid h-full grid-cols-1 gap-6 lg:grid-cols-3">
                  <div className="h-[75vh] rounded-xl border border-neutral-800 bg-neutral-900/40 p-4">
                    <h4 className="text-sm font-bold text-white mb-2">Language Distribution</h4>
                    <PlotlyChart
                      className="w-full h-[90%]"
                      data={langChartData}
                      layout={{
                        showlegend: true,
                        legend: { orientation: 'v', x: 1.05, y: 0.95 },
                        margin: { l: 20, r: 90, t: 20, b: 20 },
                      }}
                    />
                  </div>

                  <div className="h-[75vh] rounded-xl border border-neutral-800 bg-neutral-900/40 p-4">
                    <h4 className="text-sm font-bold text-white mb-2">Geographic Mentions</h4>
                    <PlotlyChart
                      className="w-full h-[90%]"
                      data={geoChartData}
                      layout={{
                        xaxis: { title: { text: 'Mentions' }, gridcolor: 'rgba(255,255,255,0.08)' },
                        yaxis: { title: { text: 'Region' }, automargin: true, categoryorder: 'total ascending' },
                        margin: { l: 110, r: 20, t: 20, b: 50 },
                      }}
                    />
                  </div>

                  <div className="h-[75vh] rounded-xl border border-neutral-800 bg-neutral-900/40 p-4">
                    <h4 className="text-sm font-bold text-white mb-2">Professional Interests</h4>
                    <PlotlyChart
                      className="w-full h-[90%]"
                      data={interestChartData}
                      layout={{
                        xaxis: { title: { text: 'Posts' }, gridcolor: 'rgba(255,255,255,0.08)' },
                        yaxis: { title: { text: 'Category' }, automargin: true, categoryorder: 'total ascending' },
                        margin: { l: 130, r: 20, t: 20, b: 50 },
                      }}
                    />
                  </div>
                </div>
              )}

              {fullscreenModal === 'language' && (
                <div className="h-[78vh] w-full p-2">
                  <PlotlyChart
                    className="w-full h-full"
                    data={langChartData}
                    layout={{
                      showlegend: true,
                      legend: { orientation: 'v', x: 1.05, y: 0.95, font: { size: 13 } },
                      margin: { l: 30, r: 120, t: 30, b: 30 },
                    }}
                  />
                </div>
              )}

              {fullscreenModal === 'geo' && (
                <div className="h-[78vh] w-full p-2">
                  <PlotlyChart
                    className="w-full h-full"
                    data={geoChartData}
                    layout={{
                      xaxis: { title: { text: 'Mentions', font: { size: 14 } }, gridcolor: 'rgba(255,255,255,0.08)' },
                      yaxis: { title: { text: 'Region', font: { size: 14 } }, automargin: true, categoryorder: 'total ascending', tickfont: { size: 13 } },
                      margin: { l: 140, r: 30, t: 30, b: 60 },
                    }}
                  />
                </div>
              )}

              {fullscreenModal === 'interests' && (
                <div className="h-[78vh] w-full p-2">
                  <PlotlyChart
                    className="w-full h-full"
                    data={interestChartData}
                    layout={{
                      xaxis: { title: { text: 'Posts', font: { size: 14 } }, gridcolor: 'rgba(255,255,255,0.08)' },
                      yaxis: { title: { text: 'Category', font: { size: 14 } }, automargin: true, categoryorder: 'total ascending', tickfont: { size: 13 } },
                      margin: { l: 150, r: 30, t: 30, b: 60 },
                    }}
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};


