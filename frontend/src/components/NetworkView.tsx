import React, { useMemo, useState } from 'react';
import { PlotlyChart } from './PlotlyChart';
import type { NetworkData } from '../types';
import { Maximize2, Minimize2, X, ChevronLeft, ChevronRight } from 'lucide-react';

interface NetworkViewProps {
  network?: NetworkData;
}

export const NetworkView: React.FC<NetworkViewProps> = ({
  network = { nodes: [], edges: [], kols: [], node_count: 0, edge_count: 0, kol_count: 0 },
}) => {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [pageSize, setPageSize] = useState<number | 'all'>(10);
  const [currentPage, setCurrentPage] = useState<number>(1);

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

  const totalKols = kolsList.length;
  const effectivePageSize = pageSize === 'all' ? (totalKols || 1) : pageSize;
  const totalPages = Math.ceil(totalKols / effectivePageSize) || 1;
  const safeCurrentPage = Math.min(Math.max(1, currentPage), totalPages);

  const startIndex = (safeCurrentPage - 1) * effectivePageSize;
  const endIndex = pageSize === 'all' ? totalKols : Math.min(startIndex + effectivePageSize, totalKols);
  const paginatedKols = kolsList.slice(startIndex, endIndex);

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
      line: { width: 1.2, color: 'rgba(0, 0, 0, 0.45)' },
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
      textfont: { size: 10, color: '#000000', family: 'system-ui, sans-serif' },
      hoverinfo: 'text' as const,
      hovertext: hoverText,
      marker: {
        size: nodeSizes,
        color: nodeColors,
        colorscale: 'Viridis',
        showscale: true,
        colorbar: {
          title: { text: 'Community', font: { size: 11, color: '#000000' } },
          tickfont: { size: 10, color: '#000000' },
          thickness: 12,
          len: 0.7,
        },
        line: {
          width: displayNodes.map((d) => (d.is_kol ? 2.5 : 1.5)),
          color: '#000000',
        },
      },
      showlegend: false,
      type: 'scatter' as const,
    };

    return [edgeTrace, nodeTrace];
  }, [nodes, edges]);

  return (
    <div className="rounded-lg border-2 border-black bg-white p-5 shadow-neo space-y-6">
      <div className="flex items-center justify-between border-b-2 border-black pb-4">
        <div>
          <h3 className="text-base font-black text-black uppercase tracking-wide">Network & Influence Analysis</h3>
          <p className="text-xs font-semibold text-neutral-600">Centrality ranking, community clustering, and interaction graphs</p>
        </div>
        <button
          onClick={() => setIsFullscreen(true)}
          className="neo-btn flex items-center gap-1.5 rounded-lg bg-black px-3.5 py-1.5 text-xs font-black text-white hover:bg-neutral-800"
        >
          <Maximize2 className="h-3.5 w-3.5 stroke-[2.5]" /> Fullscreen Graph
        </button>
      </div>

      {/* 3 Metrics */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-lg border-2 border-black bg-neutral-100 p-4 shadow-neo-sm">
          <span className="text-xs font-black uppercase text-neutral-600">Network Nodes</span>
          <div className="text-2xl font-black text-black mt-1">{network?.node_count || nodes.length}</div>
        </div>

        <div className="rounded-lg border-2 border-black bg-neutral-50 p-4 shadow-neo-sm">
          <span className="text-xs font-black uppercase text-neutral-600">Connections</span>
          <div className="text-2xl font-black text-black mt-1">{network?.edge_count || edges.length}</div>
        </div>

        <div className="rounded-lg border-2 border-black bg-neutral-200 p-4 shadow-neo-sm">
          <span className="text-xs font-black uppercase text-neutral-600">Key Opinion Leaders</span>
          <div className="text-2xl font-black text-black mt-1">{network?.kol_count || kolsList.length}</div>
        </div>
      </div>

      {/* Key Opinion Leaders Table */}
      <div className="space-y-2">
        <h4 className="text-xs font-black uppercase tracking-wider text-black">
          Key Opinion Leaders
        </h4>

        <div className="overflow-x-auto rounded-lg border-2 border-black bg-white shadow-neo-sm">
          <table className="w-full text-left text-xs text-black">
            <thead className="border-b-2 border-black bg-neutral-100 text-[11px] font-black uppercase text-black">
              <tr>
                <th className="p-3">Handle</th>
                <th className="p-3">Degree</th>
                <th className="p-3">Betweenness</th>
                <th className="p-3">Eigenvector</th>
                <th className="p-3">Community</th>
              </tr>
            </thead>
            <tbody className="divide-y-2 divide-black font-mono text-[11px]">
              {paginatedKols.map((kol, idx) => {
                const cleanHandle = (kol.handle || '').replace(/^@+/, '');
                return (
                  <tr key={idx} className="hover:bg-neutral-100">
                    <td className="p-3 font-black text-black font-sans">@{cleanHandle}</td>
                    <td className="p-3 font-bold text-black">{(kol.degree_centrality || 0).toFixed(4)}</td>
                    <td className="p-3 font-bold text-black">{(kol.betweenness_centrality || 0).toFixed(4)}</td>
                    <td className="p-3 font-black text-black">{(kol.eigenvector_centrality || 0).toFixed(4)}</td>
                    <td className="p-3 font-bold text-neutral-600">#{kol.community_id || 0}</td>
                  </tr>
                );
              })}

              {kolsList.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-6 text-center text-xs font-bold text-neutral-500 font-sans">
                    No KOLs identified yet (need more interaction data)
                  </td>
                </tr>
              )}
            </tbody>
          </table>

          {/* Bottom Choose Section & Pagination Controls */}
          {totalKols > 0 && (
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3 border-t-2 border-black bg-neutral-50 p-3">
              {/* Left: Row range status */}
              <div className="text-xs font-black text-black">
                Showing <span className="underline">{startIndex + 1}–{endIndex}</span> of <span className="font-black">{totalKols}</span> Key Opinion Leaders
              </div>

              {/* Middle: Rows per page chooser */}
              <div className="flex items-center gap-1.5 text-xs font-black text-black">
                <span className="uppercase text-[11px] text-neutral-600">Show:</span>
                {[5, 10, 20, 50, 'all'].map((size) => {
                  const isSelected = pageSize === size;
                  return (
                    <button
                      key={size}
                      onClick={() => {
                        setPageSize(size as any);
                        setCurrentPage(1);
                      }}
                      className={`rounded-md border-2 border-black px-2.5 py-1 text-[11px] font-black transition-all ${
                        isSelected
                          ? 'bg-black text-white shadow-neo-sm translate-x-[1px] translate-y-[1px]'
                          : 'bg-white text-black hover:bg-neutral-100 shadow-neo-sm'
                      }`}
                    >
                      {size === 'all' ? 'All' : size}
                    </button>
                  );
                })}
              </div>

              {/* Right: Page Navigation buttons */}
              {pageSize !== 'all' && totalPages > 1 && (
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    disabled={safeCurrentPage === 1}
                    className="neo-btn flex items-center gap-1 rounded-md bg-white px-2.5 py-1 text-xs font-black text-black hover:bg-neutral-100 disabled:opacity-40"
                  >
                    <ChevronLeft className="h-3.5 w-3.5 stroke-[2.5]" /> Prev
                  </button>
                  <span className="text-xs font-black text-black">
                    {safeCurrentPage} / {totalPages}
                  </span>
                  <button
                    onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                    disabled={safeCurrentPage === totalPages}
                    className="neo-btn flex items-center gap-1 rounded-md bg-white px-2.5 py-1 text-xs font-black text-black hover:bg-neutral-100 disabled:opacity-40"
                  >
                    Next <ChevronRight className="h-3.5 w-3.5 stroke-[2.5]" />
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Network Graph Visualizer */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-black uppercase tracking-wider text-black">
            Interactive Network Graph
          </h4>
          <span className="text-[11px] font-semibold text-neutral-600">
            Scroll to zoom • Drag to pan • Hover for details • Toolbar top-right
          </span>
        </div>
        <div className="overflow-hidden rounded-lg border-2 border-black bg-white p-2 shadow-neo-sm">
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
            <div className="flex h-64 items-center justify-center text-xs font-bold text-neutral-500">
              No network nodes available
            </div>
          )}
        </div>
      </div>

      {/* Fullscreen Graph Modal */}
      {isFullscreen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="relative flex h-[92vh] w-[95vw] flex-col rounded-lg border-4 border-black bg-white p-6 shadow-neo-xl">
            <div className="flex items-center justify-between border-b-2 border-black pb-4">
              <div>
                <h2 className="text-lg font-black uppercase text-black">Interactive Network Graph (Fullscreen)</h2>
                <p className="text-xs font-semibold text-neutral-600">
                  Full resolution node-link diagram • Drag to pan, scroll to zoom, hover on nodes for centrality details
                </p>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setIsFullscreen(false)}
                  className="neo-btn flex items-center gap-1 rounded-lg bg-black px-3.5 py-1.5 text-xs font-black text-white hover:bg-neutral-800"
                >
                  <Minimize2 className="h-4 w-4" /> Close Fullscreen
                </button>
                <button
                  onClick={() => setIsFullscreen(false)}
                  className="rounded-lg p-1 text-black hover:bg-neutral-100"
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
