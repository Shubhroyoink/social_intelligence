import React, { useMemo, useState } from 'react';
import { PlotlyChart } from './PlotlyChart';
import type { NetworkData } from '../types';
import { Maximize2, Minimize2, X } from 'lucide-react';

interface NetworkViewProps {
  network?: NetworkData;
}

export const NetworkView: React.FC<NetworkViewProps> = ({
  network = { nodes: [], edges: [], kols: [], node_count: 0, edge_count: 0, kol_count: 0 },
}) => {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const nodes = network?.nodes || [];
  const edges = network?.edges || [];
  const kolsList = useMemo(() => {
    const rawKols = network?.kols || [];
    const nodeMap = new Map<string, any>();
    nodes.forEach((n) => nodeMap.set(n.handle, n));

    if (rawKols.length > 0) {
      if (typeof rawKols[0] === 'object' && rawKols[0] !== null && 'handle' in rawKols[0]) {
        return rawKols as any[];
      }
      if (typeof rawKols[0] === 'string') {
        return (rawKols as unknown as string[]).map(
          (h) =>
            nodeMap.get(h) || {
              handle: h,
              degree_centrality: 0,
              betweenness_centrality: 0,
              eigenvector_centrality: 0,
              community_id: 0,
              is_kol: 1,
            }
        );
      }
    }

    const explicitKols = nodes.filter((n) => n.is_kol === 1);
    if (explicitKols.length > 0) {
      return explicitKols.sort((a, b) => (b.eigenvector_centrality || 0) - (a.eigenvector_centrality || 0));
    }

    return [...nodes]
      .sort((a, b) => (b.eigenvector_centrality || 0) - (a.eigenvector_centrality || 0))
      .slice(0, 15);
  }, [network?.kols, nodes]);

  // Compute 2D Spring / Force layout for Plotly
  const plotData = useMemo(() => {
    if (nodes.length === 0) return [];

    const displayNodes = nodes.slice(0, 150);
    const n = displayNodes.length;
    const nodeIndex = new Map<string, number>();
    displayNodes.forEach((node, idx) => nodeIndex.set(node.handle, idx));

    // Initial circular coordinates
    const positions = displayNodes.map((_, idx) => {
      const angle = (idx / n) * 2 * Math.PI;
      const radius = 200 + Math.sin(idx * 7) * 40;
      return { x: Math.cos(angle) * radius, y: Math.sin(angle) * radius };
    });

    // Spring-electrical iterations
    const k = 180 / Math.sqrt(Math.max(n, 1));
    const iterations = 40;

    for (let iter = 0; iter < iterations; iter++) {
      const disp = positions.map(() => ({ dx: 0, dy: 0 }));

      // Repulsion between all nodes
      for (let i = 0; i < n; i++) {
        for (let j = i + 1; j < n; j++) {
          const dx = positions[i].x - positions[j].x;
          const dy = positions[i].y - positions[j].y;
          const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
          const force = (k * k) / dist;
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;

          disp[i].dx += fx;
          disp[i].dy += fy;
          disp[j].dx -= fx;
          disp[j].dy -= fy;
        }
      }

      // Attraction along edges
      edges.forEach((edge) => {
        const u = nodeIndex.get(edge.source_handle);
        const v = nodeIndex.get(edge.target_handle);
        if (u !== undefined && v !== undefined && u < n && v < n) {
          const dx = positions[u].x - positions[v].x;
          const dy = positions[u].y - positions[v].y;
          const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
          const force = (dist * dist) / k;
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;

          disp[u].dx -= fx;
          disp[u].dy -= fy;
          disp[v].dx += fx;
          disp[v].dy += fy;
        }
      });

      // Update positions
      const step = 0.15;
      for (let i = 0; i < n; i++) {
        positions[i].x += disp[i].dx * step;
        positions[i].y += disp[i].dy * step;
      }
    }

    // Build Edge Scatter trace (disjoint lines with null separators)
    const edgeX: (number | null)[] = [];
    const edgeY: (number | null)[] = [];

    edges.forEach((edge) => {
      const u = nodeIndex.get(edge.source_handle);
      const v = nodeIndex.get(edge.target_handle);
      if (u !== undefined && v !== undefined && u < n && v < n) {
        edgeX.push(positions[u].x, positions[v].x, null);
        edgeY.push(positions[u].y, positions[v].y, null);
      }
    });

    const edgeTrace = {
      x: edgeX,
      y: edgeY,
      mode: 'lines' as const,
      line: { width: 0.8, color: 'rgba(113, 113, 122, 0.4)' },
      hoverinfo: 'none' as const,
      showlegend: false,
      type: 'scatter' as const,
    };

    // Build Node Scatter trace
    const nodeX = positions.map((p) => p.x);
    const nodeY = positions.map((p) => p.y);
    const nodeText = displayNodes.map((d) => (d.is_kol || (d.eigenvector_centrality || 0) > 0.05 ? d.handle : ''));
    const hoverText = displayNodes.map(
      (d) =>
        `<b>@${d.handle}</b><br>Eigenvector: ${(d.eigenvector_centrality || 0).toFixed(4)}<br>Degree: ${(d.degree_centrality || 0).toFixed(4)}<br>Community: #${d.community_id || 0}${d.is_kol ? '<br><b>🌟 Key Opinion Leader</b>' : ''}`
    );
    const nodeSizes = displayNodes.map((d) => Math.max(10, Math.min(36, 12 + (d.eigenvector_centrality || 0) * 160)));
    const nodeColors = displayNodes.map((d) => d.community_id || 0);

    const nodeTrace = {
      x: nodeX,
      y: nodeY,
      mode: 'markers+text' as const,
      text: nodeText,
      textposition: 'top center' as const,
      textfont: { size: 9, color: '#e4e4e7' },
      hoverinfo: 'text' as const,
      hovertext: hoverText,
      marker: {
        size: nodeSizes,
        color: nodeColors,
        colorscale: 'Viridis',
        showscale: true,
        colorbar: {
          title: { text: 'Community', font: { size: 10, color: '#a1a1aa' } },
          tickfont: { size: 9, color: '#a1a1aa' },
          thickness: 12,
          len: 0.7,
        },
        line: {
          width: displayNodes.map((d) => (d.is_kol ? 2 : 1)),
          color: displayNodes.map((d) => (d.is_kol ? '#ffffff' : 'rgba(255,255,255,0.2)')),
        },
      },
      showlegend: false,
      type: 'scatter' as const,
    };

    return [edgeTrace, nodeTrace];
  }, [nodes, edges]);

  return (
    <div className="rounded-2xl border border-neutral-800/80 bg-neutral-900/60 p-5 backdrop-blur-sm space-y-6">
      <div className="flex items-center justify-between border-b border-neutral-800 pb-4">
        <div>
          <h3 className="text-base font-bold text-white">Network & Influence Analysis</h3>
          <p className="text-xs text-neutral-400">Centrality ranking, community clustering, and interaction graphs</p>
        </div>
        <button
          onClick={() => setIsFullscreen(true)}
          className="flex items-center gap-1.5 rounded-lg border border-neutral-700 bg-neutral-800/80 px-3 py-1.5 text-xs font-semibold text-neutral-300 hover:bg-neutral-700 hover:text-white transition-colors"
        >
          <Maximize2 className="h-3.5 w-3.5" /> Fullscreen Graph
        </button>
      </div>

      {/* 3 Metrics */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-neutral-800 bg-neutral-950/60 p-4">
          <span className="text-xs font-semibold text-neutral-400">Network Nodes</span>
          <div className="text-2xl font-bold text-white mt-1">{network?.node_count || nodes.length}</div>
        </div>

        <div className="rounded-xl border border-neutral-800 bg-neutral-950/60 p-4">
          <span className="text-xs font-semibold text-neutral-400">Connections</span>
          <div className="text-2xl font-bold text-white mt-1">{network?.edge_count || edges.length}</div>
        </div>

        <div className="rounded-xl border border-neutral-800 bg-neutral-950/60 p-4">
          <span className="text-xs font-semibold text-neutral-400">Key Opinion Leaders</span>
          <div className="text-2xl font-bold text-white mt-1">{network?.kol_count || kolsList.length}</div>
        </div>
      </div>

      {/* Key Opinion Leaders Table */}
      <div className="space-y-2">
        <h4 className="text-xs font-bold uppercase tracking-wider text-neutral-300">
          Key Opinion Leaders
        </h4>

        <div className="overflow-x-auto rounded-xl border border-neutral-800">
          <table className="w-full text-left text-xs text-neutral-300">
            <thead className="border-b border-neutral-800 bg-neutral-950/80 text-[11px] font-semibold text-neutral-400">
              <tr>
                <th className="p-3">Handle</th>
                <th className="p-3">Degree</th>
                <th className="p-3">Betweenness</th>
                <th className="p-3">Eigenvector</th>
                <th className="p-3">Community</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-800/60 bg-neutral-900/30 font-mono text-[11px]">
              {kolsList.map((kol, idx) => (
                <tr key={idx} className="hover:bg-neutral-800/40">
                  <td className="p-3 font-semibold text-indigo-300 font-sans">@{kol.handle}</td>
                  <td className="p-3 text-neutral-300">{(kol.degree_centrality || 0).toFixed(4)}</td>
                  <td className="p-3 text-neutral-300">{(kol.betweenness_centrality || 0).toFixed(4)}</td>
                  <td className="p-3 text-emerald-400 font-bold">{(kol.eigenvector_centrality || 0).toFixed(4)}</td>
                  <td className="p-3 text-neutral-400">#{kol.community_id || 0}</td>
                </tr>
              ))}

              {kolsList.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-6 text-center text-xs text-neutral-500 font-sans">
                    No KOLs identified yet (need more interaction data)
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Network Graph Visualizer */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-bold uppercase tracking-wider text-neutral-300">
            Interactive Network Graph
          </h4>
          <span className="text-[11px] text-neutral-400">
            Scroll to zoom • Drag to pan • Hover for details • Toolbar top-right
          </span>
        </div>
        <div className="overflow-hidden rounded-xl border border-neutral-800 bg-neutral-950/60 p-2">
          {plotData.length > 0 ? (
            <PlotlyChart
              className="w-full h-[520px]"
              data={plotData as any}
              layout={{
                showlegend: false,
                hovermode: 'closest',
                xaxis: { showgrid: false, zeroline: false, showticklabels: false },
                yaxis: { showgrid: false, zeroline: false, showticklabels: false },
                margin: { l: 10, r: 10, t: 10, b: 10 },
              }}
            />
          ) : (
            <div className="flex h-64 items-center justify-center text-xs text-neutral-500">
              No network nodes available
            </div>
          )}
        </div>
      </div>

      {/* Fullscreen Graph Modal */}
      {isFullscreen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-md">
          <div className="relative flex h-[92vh] w-[95vw] flex-col rounded-2xl border border-neutral-700 bg-neutral-950 p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-neutral-800 pb-4">
              <div>
                <h2 className="text-lg font-bold text-white">Interactive Network Graph (Fullscreen)</h2>
                <p className="text-xs text-neutral-400">
                  Full resolution node-link diagram • Drag to pan, scroll to zoom, hover on nodes for centrality details
                </p>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setIsFullscreen(false)}
                  className="flex items-center gap-1 rounded-lg border border-neutral-700 bg-neutral-850 px-3 py-1.5 text-xs font-semibold text-neutral-300 hover:bg-neutral-700 hover:text-white"
                >
                  <Minimize2 className="h-4 w-4" /> Close Fullscreen
                </button>
                <button
                  onClick={() => setIsFullscreen(false)}
                  className="rounded-lg p-1 text-neutral-400 hover:bg-neutral-800 hover:text-white"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-hidden pt-4">
              <PlotlyChart
                className="w-full h-[78vh]"
                data={plotData as any}
                layout={{
                  showlegend: false,
                  hovermode: 'closest',
                  xaxis: { showgrid: false, zeroline: false, showticklabels: false },
                  yaxis: { showgrid: false, zeroline: false, showticklabels: false },
                  margin: { l: 20, r: 20, t: 20, b: 20 },
                }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
