import React, { useEffect, useRef } from 'react';
import type { NetworkData } from '../types';

interface NetworkViewProps {
  network?: NetworkData;
}

const COMMUNITY_PALETTE = [
  '#6366f1', '#ec4899', '#10b981', '#f59e0b', '#06b6d4',
  '#8b5cf6', '#3b82f6', '#f43f5e', '#84cc16', '#14b8a6'
];

export const NetworkView: React.FC<NetworkViewProps> = ({
  network = { nodes: [], edges: [], kols: [], node_count: 0, edge_count: 0, kol_count: 0 },
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const nodes = network?.nodes || [];
  const edges = network?.edges || [];
  const kols = network?.kols || [];

  // Render network graph canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = canvas.parentElement?.clientWidth || 800;
    canvas.height = 480;

    const width = canvas.width;
    const height = canvas.height;

    // Background
    ctx.fillStyle = '#09090b';
    ctx.fillRect(0, 0, width, height);

    if (nodes.length === 0) {
      ctx.fillStyle = '#71717a';
      ctx.font = '12px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('No network nodes available', width / 2, height / 2);
      return;
    }

    // Force/Spring 2D layout approximation
    const displayNodes = nodes.slice(0, 100);
    const nodePositions = new Map<string, { x: number; y: number; r: number; color: string; handle: string; is_kol: boolean }>();

    displayNodes.forEach((n, idx) => {
      const angle = (idx / displayNodes.length) * Math.PI * 2;
      const eig = n.eigenvector_centrality || 0;
      const radius = 120 + Math.sin(idx * 7) * 60;
      const isKol = n.is_kol === 1;
      const r = Math.max(5, Math.min(18, 5 + eig * 80));
      const color = COMMUNITY_PALETTE[(n.community_id || 0) % COMMUNITY_PALETTE.length];

      nodePositions.set(n.handle, {
        x: width / 2 + Math.cos(angle) * radius,
        y: height / 2 + Math.sin(angle) * radius,
        r,
        color,
        handle: n.handle,
        is_kol: isKol,
      });
    });

    // Draw Edges
    ctx.strokeStyle = 'rgba(113, 113, 122, 0.4)';
    ctx.lineWidth = 0.8;
    edges.forEach((edge) => {
      const src = nodePositions.get(edge.source_handle);
      const tgt = nodePositions.get(edge.target_handle);
      if (src && tgt) {
        ctx.beginPath();
        ctx.moveTo(src.x, src.y);
        ctx.lineTo(tgt.x, tgt.y);
        ctx.stroke();
      }
    });

    // Draw Nodes
    nodePositions.forEach((node) => {
      ctx.beginPath();
      ctx.arc(node.x, node.y, node.r, 0, Math.PI * 2);
      ctx.fillStyle = node.color;
      ctx.fill();
      ctx.strokeStyle = node.is_kol ? '#ffffff' : 'rgba(255,255,255,0.2)';
      ctx.lineWidth = node.is_kol ? 2 : 1;
      ctx.stroke();

      // Node text label
      if (node.is_kol || node.r > 8) {
        ctx.fillStyle = '#e4e4e7';
        ctx.font = '9px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(node.handle, node.x, node.y - node.r - 3);
      }
    });
  }, [network, nodes, edges]);

  return (
    <div className="rounded-2xl border border-neutral-800/80 bg-neutral-900/60 p-5 backdrop-blur-sm space-y-6">
      <div className="border-b border-neutral-800 pb-4">
        <h3 className="text-base font-bold text-white">Network & Influence Analysis</h3>
        <p className="text-xs text-neutral-400">Centrality ranking, community clustering, and interaction graphs</p>
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
          <div className="text-2xl font-bold text-white mt-1">{network?.kol_count || kols.length}</div>
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
              {kols.map((kol, idx) => (
                <tr key={idx} className="hover:bg-neutral-800/40">
                  <td className="p-3 font-semibold text-indigo-300 font-sans">{kol.handle}</td>
                  <td className="p-3 text-neutral-300">{(kol.degree_centrality || 0).toFixed(4)}</td>
                  <td className="p-3 text-neutral-300">{(kol.betweenness_centrality || 0).toFixed(4)}</td>
                  <td className="p-3 text-emerald-400 font-bold">{(kol.eigenvector_centrality || 0).toFixed(4)}</td>
                  <td className="p-3 text-neutral-400">#{kol.community_id || 0}</td>
                </tr>
              ))}

              {kols.length === 0 && (
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
        <h4 className="text-xs font-bold uppercase tracking-wider text-neutral-300">
          Network Graph
        </h4>
        <div className="overflow-hidden rounded-xl border border-neutral-800">
          <canvas ref={canvasRef} className="w-full" />
        </div>
      </div>
    </div>
  );
};
