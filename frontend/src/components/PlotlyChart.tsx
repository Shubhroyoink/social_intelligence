import React, { useEffect, useRef } from 'react';
import Plotly from 'plotly.js-dist-min';

interface PlotlyChartProps {
  data: Plotly.Data[];
  layout?: Partial<Plotly.Layout>;
  config?: Partial<Plotly.Config>;
  className?: string;
  style?: React.CSSProperties;
}

export const PlotlyChart: React.FC<PlotlyChartProps> = ({
  data,
  layout = {},
  config = {},
  className = 'w-full h-80',
  style,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const userLayoutRef = useRef<{ xaxis?: any; yaxis?: any } | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const el = containerRef.current as any;

    const baseLayout: Partial<Plotly.Layout> = {
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      uirevision: 'user_active_session',
      dragmode: layout.dragmode ?? 'pan',
      font: {
        color: '#a1a1aa',
        family: 'system-ui, -apple-system, sans-serif',
        size: 11,
      },
      margin: { l: 55, r: 25, t: 30, b: 45 },
      autosize: true,
      hovermode: 'closest',
      xaxis: {
        gridcolor: '#27272a',
        linecolor: '#3f3f46',
        tickcolor: '#3f3f46',
        zerolinecolor: '#27272a',
        fixedrange: false,
        uirevision: 'user_active_session',
        ...layout.xaxis,
        ...(userLayoutRef.current?.xaxis ? { range: userLayoutRef.current.xaxis } : {}),
      },
      yaxis: {
        gridcolor: '#27272a',
        linecolor: '#3f3f46',
        tickcolor: '#3f3f46',
        zerolinecolor: '#27272a',
        fixedrange: false,
        uirevision: 'user_active_session',
        ...layout.yaxis,
        ...(userLayoutRef.current?.yaxis ? { range: userLayoutRef.current.yaxis } : {}),
      },
      legend: {
        font: { color: '#e4e4e7', size: 11 },
        bgcolor: 'rgba(24, 24, 27, 0.6)',
        bordercolor: '#27272a',
        borderwidth: 1,
        ...layout.legend,
      },
      ...layout,
    };

    const baseConfig: Partial<Plotly.Config> = {
      responsive: true,
      displayModeBar: true,
      displaylogo: false,
      scrollZoom: true,
      doubleClick: 'reset+autosize',
      modeBarButtonsToRemove: [],
      toImageButtonOptions: {
        format: 'png',
        filename: 'social_intelligence_chart',
        height: 600,
        width: 1000,
        scale: 2,
      },
      ...config,
    };

    Plotly.react(el, data, baseLayout, baseConfig);

    // Track user drag / zoom / pan modifications
    const onRelayout = (eventData: any) => {
      if (!eventData) return;

      // User double clicked / reset to default
      if (
        eventData['xaxis.autorange'] ||
        eventData['yaxis.autorange'] ||
        eventData['autosize'] ||
        eventData['xaxis.showgrid'] !== undefined
      ) {
        if (eventData['xaxis.autorange'] || eventData['yaxis.autorange']) {
          userLayoutRef.current = null;
        }
        return;
      }

      const updated = { ...userLayoutRef.current };

      if (eventData['xaxis.range[0]'] !== undefined && eventData['xaxis.range[1]'] !== undefined) {
        updated.xaxis = [eventData['xaxis.range[0]'], eventData['xaxis.range[1]']];
      } else if (Array.isArray(eventData['xaxis.range'])) {
        updated.xaxis = eventData['xaxis.range'];
      }

      if (eventData['yaxis.range[0]'] !== undefined && eventData['yaxis.range[1]'] !== undefined) {
        updated.yaxis = [eventData['yaxis.range[0]'], eventData['yaxis.range[1]']];
      } else if (Array.isArray(eventData['yaxis.range'])) {
        updated.yaxis = eventData['yaxis.range'];
      }

      userLayoutRef.current = updated;
    };

    el.on('plotly_relayout', onRelayout);

    const handleResize = () => {
      if (containerRef.current) {
        Plotly.Plots.resize(containerRef.current);
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (el && typeof el.removeListener === 'function') {
        el.removeListener('plotly_relayout', onRelayout);
      }
      if (containerRef.current) {
        Plotly.purge(containerRef.current);
      }
    };
  }, [data, layout, config]);

  return <div ref={containerRef} className={className} style={style} />;
};


