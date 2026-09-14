import React, { useMemo, useState, useRef, useEffect } from 'react';
import { PlotlyChart } from './PlotlyChart';
import type { NetworkData, NetworkNode, NetworkEdge } from '../types';
import {
  Maximize2,
  Minimize2,
  X,
  ChevronLeft,
  ChevronRight,
  Share2,
  Sparkles,
  BookOpen,
  ChevronDown,
  ChevronUp,
  Play,
  Pause,
  ZoomIn,
  ZoomOut,
  RefreshCw,
  Box,
  Layers,
} from 'lucide-react';

interface NetworkViewProps {
  network?: NetworkData;
}

const COMMUNITY_PALETTE = [
  '#00f0ff', // 0: Neon Cyan
  '#10b981', // 1: Emerald Green
  '#f43f5e', // 2: Neon Rose / Magenta
  '#a855f7', // 3: Electric Violet
  '#f59e0b', // 4: Amber Orange
  '#84cc16', // 5: Lime
  '#3b82f6', // 6: Electric Blue
  '#ec4899', // 7: Vivid Pink
];

interface Node3D {
  id: string;
  handle: string;
  x: number;
  y: number;
  z: number;
  radius: number;
  color: string;
  community: number;
  eigenvector: number;
  degree: number;
  is_kol: boolean;
  isHub: boolean;
  projX?: number;
  projY?: number;
  projScale?: number;
}

interface Edge3D {
  source: number;
  target: number;
  weight: number;
  isInterCommunity?: boolean;
}

export const NetworkView: React.FC<NetworkViewProps> = ({
  network = { nodes: [], edges: [], kols: [], node_count: 0, edge_count: 0, kol_count: 0 },
}) => {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [pageSize, setPageSize] = useState<number | 'all'>(10);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [showGlossary, setShowGlossary] = useState<boolean>(false);
  const [graphMode, setGraphMode] = useState<'3d' | '2d'>('3d');

  // 3D Orbit States
  const [autoRotate, setAutoRotate] = useState(true);
  const [zoom3D, setZoom3D] = useState(1);
  const [hoveredNode3D, setHoveredNode3D] = useState<Node3D | null>(null);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const animRef = useRef<number | null>(null);

  const rotRef = useRef<{ rotX: number; rotY: number; targetRotX: number; targetRotY: number }>({
    rotX: 0.18,
    rotY: 0.35,
    targetRotX: 0.18,
    targetRotY: 0.35,
  });
  const zoom3DRef = useRef<number>(1);
  const autoRotateRef = useRef<boolean>(true);
  const isDraggingRef = useRef(false);
  const lastMousePosRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const mousePosRef = useRef<{ x: number; y: number } | null>(null);
  const nodes3DRef = useRef<Node3D[]>([]);
  const edges3DRef = useRef<Edge3D[]>([]);

  useEffect(() => {
    zoom3DRef.current = zoom3D;
  }, [zoom3D]);

  useEffect(() => {
    autoRotateRef.current = autoRotate;
  }, [autoRotate]);

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
      .slice(0, 20);
  }, [network?.kols, nodes]);

  const totalKols = kolsList.length;
  const effectivePageSize = pageSize === 'all' ? (totalKols || 1) : pageSize;
  const totalPages = Math.max(1, Math.ceil(totalKols / effectivePageSize));
  const safeCurrentPage = Math.min(Math.max(1, currentPage), totalPages);

  const startIndex = (safeCurrentPage - 1) * effectivePageSize;
  const endIndex = pageSize === 'all' ? totalKols : Math.min(startIndex + effectivePageSize, totalKols);
  const paginatedKols = kolsList.slice(startIndex, endIndex);

  // Setup Constellation Topology matching reference image
  useEffect(() => {
    if (nodes.length === 0) {
      nodes3DRef.current = [];
      edges3DRef.current = [];
      return;
    }

    // Select top 60-90 most authoritative nodes for clean constellation layout
    const displayNodes = [...nodes]
      .sort((a, b) => (b.eigenvector_centrality || 0) - (a.eigenvector_centrality || 0))
      .slice(0, 85);

    const n = displayNodes.length;

    // 7 Spatial Constellation Cluster Centers matching reference geometry
    const clusterAnchorPoints = [
      { x: 120, y: -130, z: 40 },   // 0: Cyan (top-right)
      { x: 0, y: -170, z: -20 },    // 1: Green (top-center)
      { x: -170, y: -110, z: 30 },  // 2: Rose/Magenta (top-left)
      { x: -140, y: 10, z: -60 },   // 3: Violet (mid-left)
      { x: -20, y: 140, z: 40 },    // 4: Amber/Orange (bottom-center)
      { x: -130, y: 120, z: -30 },  // 5: Lime (bottom-left)
      { x: 160, y: 70, z: -40 },    // 6: Deep Blue (bottom-right)
      { x: 150, y: -40, z: 90 },    // 7: Pink (mid-right)
    ];

    const commCounts: { [key: number]: number } = {};
    const commNodes: { [key: number]: number[] } = {};

    const initialNodes: Node3D[] = displayNodes.map((node, i) => {
      const comm = Number(node.community_id || 0) % COMMUNITY_PALETTE.length;
      const rank = (commCounts[comm] || 0) + 1;
      commCounts[comm] = rank;

      if (!commNodes[comm]) commNodes[comm] = [];
      commNodes[comm].push(i);

      const center = clusterAnchorPoints[comm] || { x: 0, y: 0, z: 0 };
      const spread = 45 + Math.sqrt(rank) * 28;
      const angle = rank * 2.39996 + i * 0.15;
      const elev = ((rank % 4) - 1.5) * 28;

      const x = center.x + Math.cos(angle) * spread + Math.sin(i * 4.1) * 15;
      const y = center.y + Math.sin(angle) * spread * 0.75 + elev;
      const z = center.z + Math.sin(angle * 1.4) * spread * 0.8 + Math.cos(i * 3.3) * 15;

      const eigen = node.eigenvector_centrality || 0;
      const isHub = rank === 1 || (rank === 2 && eigen > 0.05) || eigen > 0.12;
      const isKol = node.is_kol === 1 || isHub;

      // Sizing matching reference: Key hubs 8-12px, peripheral nodes 4-6px
      const r = isHub ? 9.5 : isKol ? 7.5 : 4.5;

      return {
        id: node.handle,
        handle: node.handle.replace(/^@+/, ''),
        x,
        y,
        z,
        radius: r,
        color: COMMUNITY_PALETTE[comm],
        community: comm,
        eigenvector: eigen,
        degree: node.degree_centrality || 0,
        is_kol: isKol,
        isHub,
      };
    });

    // Generate clean laser edges matching reference
    const nodeHandleMap = new Map<string, number>();
    initialNodes.forEach((node, idx) => nodeHandleMap.set(node.id, idx));

    const edgeSet = new Set<string>();
    const graphEdges: Edge3D[] = [];

    const addEdge = (u: number, v: number, weight = 1, isInter = false) => {
      if (u === v || u < 0 || v < 0 || u >= n || v >= n) return;
      const key = u < v ? `${u}-${v}` : `${v}-${u}`;
      if (!edgeSet.has(key)) {
        edgeSet.add(key);
        graphEdges.push({ source: u, target: v, weight, isInterCommunity: isInter });
      }
    };

    // 1. Real edges from backend data
    edges.forEach((edge) => {
      const u = nodeHandleMap.get(edge.source_handle);
      const v = nodeHandleMap.get(edge.target_handle);
      if (u !== undefined && v !== undefined) {
        addEdge(u, v, 1, initialNodes[u].community !== initialNodes[v].community);
      }
    });

    // 2. Intra-community constellation linkages (connect nodes within each community so it forms clean celestial web)
    Object.values(commNodes).forEach((indices) => {
      if (indices.length === 0) return;
      const hub = indices[0];
      for (let i = 1; i < indices.length; i++) {
        // Connect to hub or previous node
        if (i <= 3) {
          addEdge(hub, indices[i], 1, false);
        } else {
          addEdge(indices[i - 1], indices[i], 0.8, false);
          if (i % 3 === 0) addEdge(hub, indices[i], 0.8, false);
        }
      }
    });

    // 3. Inter-community bridge laser filaments
    const commKeys = Object.keys(commNodes).map(Number);
    for (let c = 0; c < commKeys.length; c++) {
      const nextC = (c + 1) % commKeys.length;
      const uList = commNodes[commKeys[c]];
      const vList = commNodes[commKeys[nextC]];
      if (uList && vList && uList.length > 0 && vList.length > 0) {
        addEdge(uList[0], vList[0], 0.7, true);
      }
    }

    // Force relaxation for smooth organic distribution
    const iterations = 35;
    for (let iter = 0; iter < iterations; iter++) {
      for (let i = 0; i < n; i++) {
        for (let j = i + 1; j < n; j++) {
          const dx = initialNodes[i].x - initialNodes[j].x;
          const dy = initialNodes[i].y - initialNodes[j].y;
          const dz = initialNodes[i].z - initialNodes[j].z;
          const dist = Math.max(Math.sqrt(dx * dx + dy * dy + dz * dz), 1);
          const minDist = (initialNodes[i].radius + initialNodes[j].radius) * 4;

          if (dist < minDist) {
            const force = ((minDist - dist) / dist) * 0.12;
            initialNodes[i].x += dx * force;
            initialNodes[i].y += dy * force;
            initialNodes[i].z += dz * force;
            initialNodes[j].x -= dx * force;
            initialNodes[j].y -= dy * force;
            initialNodes[j].z -= dz * force;
          }
        }
      }

      graphEdges.forEach((e) => {
        const u = initialNodes[e.source];
        const v = initialNodes[e.target];
        const dx = u.x - v.x;
        const dy = u.y - v.y;
        const dz = u.z - v.z;
        const dist = Math.max(Math.sqrt(dx * dx + dy * dy + dz * dz), 1);
        const targetDist = e.isInterCommunity ? 160 : 70;
        const force = (dist - targetDist) * 0.004;

        u.x -= (dx / dist) * force;
        u.y -= (dy / dist) * force;
        u.z -= (dz / dist) * force;
        v.x += (dx / dist) * force;
        v.y += (dy / dist) * force;
        v.z += (dz / dist) * force;
      });
    }

    nodes3DRef.current = initialNodes;
    edges3DRef.current = graphEdges;
  }, [nodes, edges]);

  // High-Fidelity Canvas Render Loop
  useEffect(() => {
    if (graphMode !== '3d') return;

    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const rect = entry.contentRect;
        const dpr = window.devicePixelRatio || 1;
        if (rect.width > 0 && rect.height > 0) {
          canvas.width = rect.width * dpr;
          canvas.height = rect.height * dpr;
        }
      }
    });

    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }

    const render = () => {
      const dpr = window.devicePixelRatio || 1;
      const currentWidth = canvas.width;
      const currentHeight = canvas.height;
      if (currentWidth === 0 || currentHeight === 0) {
        animRef.current = requestAnimationFrame(render);
        return;
      }

      const centerX = currentWidth / 2;
      const centerY = currentHeight / 2;

      if (autoRotateRef.current && !isDraggingRef.current) {
        rotRef.current.targetRotY += 0.0022;
      }

      rotRef.current.rotX += (rotRef.current.targetRotX - rotRef.current.rotX) * 0.1;
      rotRef.current.rotY += (rotRef.current.targetRotY - rotRef.current.rotY) * 0.1;

      const cosX = Math.cos(rotRef.current.rotX);
      const sinX = Math.sin(rotRef.current.rotX);
      const cosY = Math.cos(rotRef.current.rotY);
      const sinY = Math.sin(rotRef.current.rotY);

      // PURE PITCH BLACK DEEP SPACE
      ctx.fillStyle = '#000000';
      ctx.fillRect(0, 0, currentWidth, currentHeight);

      const currentNodes = nodes3DRef.current;
      const currentEdges = edges3DRef.current;

      const fov = 540 * zoom3DRef.current * dpr;
      const cameraDistance = 620;

      const projected = currentNodes.map((node) => {
        const x1 = node.x * cosY + node.z * sinY;
        const z1 = -node.x * sinY + node.z * cosY;

        const y2 = node.y * cosX - z1 * sinX;
        const z2 = node.y * sinX + z1 * cosX;

        const scale = fov / (z2 + cameraDistance);
        const screenX = centerX + x1 * scale;
        const screenY = centerY + y2 * scale;

        node.projX = screenX;
        node.projY = screenY;
        node.projScale = scale;

        return { node, x: screenX, y: screenY, z: z2, scale };
      });

      projected.sort((a, b) => b.z - a.z);

      // Hover hit detection
      let nearestNode: Node3D | null = null;
      let minDistance = 20 * dpr;

      if (mousePosRef.current) {
        const mx = mousePosRef.current.x * dpr;
        const my = mousePosRef.current.y * dpr;

        for (const item of projected) {
          const dx = item.x - mx;
          const dy = item.y - my;
          const dist = Math.sqrt(dx * dx + dy * dy);
          const hitRadius = Math.max(item.node.radius * item.scale * 1.8, 16 * dpr);

          if (dist < hitRadius && dist < minDistance) {
            minDistance = dist;
            nearestNode = item.node;
          }
        }
      }

      setHoveredNode3D(nearestNode);

      // 1. RENDER LASER FILAMENT EDGES (Matching reference image)
      currentEdges.forEach((edge) => {
        const u = currentNodes[edge.source];
        const v = currentNodes[edge.target];

        if (u && v && u.projX !== undefined && u.projY !== undefined && v.projX !== undefined && v.projY !== undefined) {
          const isHoverEdge = nearestNode && (nearestNode.id === u.id || nearestNode.id === v.id);

          const avgZ = (u.z + v.z) / 2;
          const depthAlpha = Math.max(0.12, Math.min(0.7, (avgZ + 320) / 640));

          ctx.beginPath();
          ctx.moveTo(u.projX, u.projY);
          ctx.lineTo(v.projX, v.projY);

          if (isHoverEdge) {
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 1.8 * dpr;
            ctx.shadowColor = u.color;
            ctx.shadowBlur = 8 * dpr;
            ctx.globalAlpha = 1;
          } else {
            const grad = ctx.createLinearGradient(u.projX, u.projY, v.projX, v.projY);
            grad.addColorStop(0, u.color);
            grad.addColorStop(1, v.color);
            ctx.strokeStyle = grad;
            ctx.lineWidth = (edge.isInterCommunity ? 0.7 : 0.9) * dpr;
            ctx.globalAlpha = depthAlpha * (edge.isInterCommunity ? 0.35 : 0.55);
            ctx.shadowBlur = 0;
          }

          ctx.stroke();
          ctx.globalAlpha = 1;
          ctx.shadowBlur = 0;
        }
      });

      // 2. RENDER NODES & OUTER HALO RINGS (Matching reference image)
      projected.forEach(({ node, x, y, scale }) => {
        const isHovered = nearestNode && nearestNode.id === node.id;
        const radius = Math.max(3.0, node.radius * scale * dpr);

        // A. Delicate Outer Orbit Ring
        const ringRadius = radius * (isHovered ? 1.9 : 1.55);
        ctx.beginPath();
        ctx.arc(x, y, ringRadius, 0, Math.PI * 2);
        ctx.strokeStyle = isHovered ? '#ffffff' : node.color;
        ctx.lineWidth = (isHovered ? 1.5 : 0.9) * dpr;
        ctx.globalAlpha = isHovered ? 1 : 0.75;
        ctx.stroke();

        // B. Translucent Glow Disc between ring and core
        if (node.isHub || isHovered) {
          ctx.beginPath();
          ctx.arc(x, y, ringRadius, 0, Math.PI * 2);
          ctx.fillStyle = `${node.color}22`;
          ctx.fill();
        }

        // C. Solid Colored Core Disc
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.fillStyle = node.color;
        ctx.shadowColor = node.color;
        ctx.shadowBlur = isHovered ? 14 * dpr : node.isHub ? 8 * dpr : 3 * dpr;
        ctx.globalAlpha = 1;
        ctx.fill();
        ctx.shadowBlur = 0;

        // D. Bright Center Pinpoint Dot (pure white)
        const dotRadius = Math.max(1.2, radius * 0.38);
        ctx.beginPath();
        ctx.arc(x, y, dotRadius, 0, Math.PI * 2);
        ctx.fillStyle = '#ffffff';
        ctx.fill();

        // 3. SLEEK MINIMAL LABELS (Pure floating text with soft glow, matching reference!)
        const isSelectedForLabel = isHovered || (node.isHub && scale > 0.78);

        if (isSelectedForLabel) {
          const fontSize = Math.max(9.5, Math.min(13, 11 * scale * dpr));
          ctx.font = `500 ${fontSize}px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`;
          ctx.textAlign = 'left';
          ctx.textBaseline = 'middle';

          const labelText = node.handle;
          const labelX = x + ringRadius + 6 * dpr;
          const labelY = y;

          // Soft drop shadow for legibility over lines
          ctx.shadowColor = '#000000';
          ctx.shadowBlur = 5 * dpr;
          ctx.shadowOffsetX = 1;
          ctx.shadowOffsetY = 1;

          ctx.fillStyle = isHovered ? '#ffffff' : 'rgba(215, 225, 235, 0.88)';
          ctx.fillText(labelText, labelX, labelY);
          ctx.shadowBlur = 0;
          ctx.shadowOffsetX = 0;
          ctx.shadowOffsetY = 0;
        }
      });

      animRef.current = requestAnimationFrame(render);
    };

    animRef.current = requestAnimationFrame(render);

    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
      resizeObserver.disconnect();
    };
  }, [edges, graphMode]);

  // Mouse Handlers for 3D Orbit
  const handleMouseDown3D = (e: React.MouseEvent) => {
    isDraggingRef.current = true;
    lastMousePosRef.current = { x: e.clientX, y: e.clientY };
  };

  const handleMouseMove3D = (e: React.MouseEvent) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    mousePosRef.current = {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };

    if (isDraggingRef.current) {
      const dx = e.clientX - lastMousePosRef.current.x;
      const dy = e.clientY - lastMousePosRef.current.y;

      rotRef.current.targetRotY += dx * 0.007;
      rotRef.current.targetRotX += dy * 0.007;

      lastMousePosRef.current = { x: e.clientX, y: e.clientY };
    }
  };

  const handleMouseUp3D = () => {
    isDraggingRef.current = false;
  };

  const handleMouseLeave3D = () => {
    isDraggingRef.current = false;
    mousePosRef.current = null;
    setHoveredNode3D(null);
  };

  const handleWheel3D = (e: React.WheelEvent) => {
    e.preventDefault();
    setZoom3D((prev) => Math.max(0.4, Math.min(2.5, prev - e.deltaY * 0.0012)));
  };

  const resetCamera3D = () => {
    rotRef.current.targetRotX = 0.2;
    rotRef.current.targetRotY = 0.4;
    setZoom3D(1);
  };

  // 2D Plotly Fallback Graph Data
  const plotData2D = useMemo(() => {
    if (nodes.length === 0) return [];
    const displayNodes = nodes.slice(0, 150);
    const n = displayNodes.length;
    const nodeIndex = new Map<string, number>();
    displayNodes.forEach((node, idx) => nodeIndex.set(node.handle, idx));

    const positions = displayNodes.map((_, idx) => {
      const angle = (idx / n) * 2 * Math.PI;
      const radius = 200 + Math.sin(idx * 7) * 40;
      return { x: Math.cos(angle) * radius, y: Math.sin(angle) * radius };
    });

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

    const nodeX = positions.map((p) => p.x);
    const nodeY = positions.map((p) => p.y);
    const nodeText = displayNodes.map((d) => (d.is_kol || (d.eigenvector_centrality || 0) > 0.05 ? `@${d.handle.replace(/^@+/, '')}` : ''));
    const hoverText = displayNodes.map(
      (d) =>
        `<b>@${d.handle.replace(/^@+/, '')}</b><br>Eigenvector: ${(d.eigenvector_centrality || 0).toFixed(4)}<br>Degree: ${(d.degree_centrality || 0).toFixed(4)}<br>Community: #${d.community_id || 0}${d.is_kol ? '<br><b>🌟 Key Opinion Leader</b>' : ''}`
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
      {/* Top Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b-2 border-black pb-4">
        <div>
          <h3 className="text-base font-black text-black flex items-center gap-2 uppercase tracking-wide">
            <span className="flex h-7 w-7 items-center justify-center rounded-md border-2 border-black bg-black text-white shadow-neo-sm">
              <Share2 className="h-4 w-4 stroke-[2.5]" />
            </span>
            Network & Influence Analysis
          </h3>
          <p className="text-xs font-semibold text-neutral-600 mt-1">
            3D Force-Directed Constellation, Key Opinion Leaders (KOLs), and Community Clusters
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {/* 3D / 2D Mode Switcher */}
          <div className="flex rounded-lg border-2 border-black bg-neutral-100 p-0.5 shadow-neo-sm">
            <button
              onClick={() => setGraphMode('3d')}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-black transition-all ${
                graphMode === '3d'
                  ? 'bg-black text-white shadow-neo-sm'
                  : 'text-black hover:bg-neutral-200'
              }`}
            >
              <Box className="h-3.5 w-3.5 stroke-[2.5]" />
              <span>3D Orbit</span>
            </button>
            <button
              onClick={() => setGraphMode('2d')}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-black transition-all ${
                graphMode === '2d'
                  ? 'bg-black text-white shadow-neo-sm'
                  : 'text-black hover:bg-neutral-200'
              }`}
            >
              <Layers className="h-3.5 w-3.5 stroke-[2.5]" />
              <span>2D Plot</span>
            </button>
          </div>

          <button
            onClick={() => setIsFullscreen(true)}
            className="neo-btn flex items-center gap-1.5 rounded-lg bg-black px-3.5 py-1.5 text-xs font-black text-white hover:bg-neutral-800"
          >
            <Maximize2 className="h-3.5 w-3.5 stroke-[2.5]" /> Fullscreen
          </button>
        </div>
      </div>

      {/* 3 Metrics Row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-lg border-2 border-black bg-neutral-100 p-4 shadow-neo-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-black uppercase text-neutral-700">Network Nodes</span>
            <span className="rounded bg-black px-1.5 py-0.5 text-[9px] font-black text-white uppercase">Accounts</span>
          </div>
          <div className="text-2xl font-black text-black mt-1">{network?.node_count || nodes.length}</div>
          <p className="text-[11px] font-semibold text-neutral-600 mt-1">Unique accounts & channels participating in conversations</p>
        </div>

        <div className="rounded-lg border-2 border-black bg-neutral-50 p-4 shadow-neo-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-black uppercase text-neutral-700">Connections</span>
            <span className="rounded bg-black px-1.5 py-0.5 text-[9px] font-black text-white uppercase">Edges</span>
          </div>
          <div className="text-2xl font-black text-black mt-1">{network?.edge_count || edges.length}</div>
          <p className="text-[11px] font-semibold text-neutral-600 mt-1">Direct @mentions, retweets, and conversational interactions</p>
        </div>

        <div className="rounded-lg border-2 border-black bg-neutral-200 p-4 shadow-neo-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-black uppercase text-neutral-700">Key Opinion Leaders</span>
            <span className="rounded bg-black px-1.5 py-0.5 text-[9px] font-black text-white uppercase">KOLs</span>
          </div>
          <div className="text-2xl font-black text-black mt-1">{network?.kol_count || kolsList.length}</div>
          <p className="text-[11px] font-semibold text-neutral-600 mt-1">High-impact accounts ranked by graph centrality algorithms</p>
        </div>
      </div>

      {/* Collapsible Network Terminology & Reviewer Glossary Card */}
      <div className="rounded-lg border-2 border-black bg-neutral-50 shadow-neo-sm overflow-hidden">
        <button
          onClick={() => setShowGlossary((prev) => !prev)}
          className="w-full flex items-center justify-between p-3.5 bg-neutral-100 hover:bg-neutral-200 transition-colors border-b-2 border-black/80 text-left"
        >
          <div className="flex items-center gap-2">
            <span className="flex h-5 w-5 items-center justify-center rounded bg-black text-white">
              <BookOpen className="h-3 w-3" />
            </span>
            <span className="text-xs font-black uppercase tracking-wider text-black">
              Network Metrics & Centrality Guide (What Do These Scores Mean?)
            </span>
            <span className="rounded border border-black bg-white px-2 py-0.5 text-[9px] font-black uppercase text-black">
              Reviewer Reference
            </span>
          </div>
          <div className="flex items-center gap-1 text-xs font-black text-black">
            <span>{showGlossary ? 'Hide Guide' : 'Show Guide'}</span>
            {showGlossary ? <ChevronUp className="h-4 w-4 stroke-[2.5]" /> : <ChevronDown className="h-4 w-4 stroke-[2.5]" />}
          </div>
        </button>

        {showGlossary && (
          <div className="p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 bg-white">
            <div className="rounded-md border-2 border-black bg-neutral-50 p-3 space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-black uppercase text-black">Degree Centrality</span>
                <span className="rounded bg-black px-1.5 py-0.5 text-[9px] font-black text-white">Direct Reach</span>
              </div>
              <p className="text-[11px] font-semibold text-neutral-700 leading-relaxed">
                <strong>What it is:</strong> Counts direct mentions and replies an account receives or sends.
              </p>
              <p className="text-[10px] font-bold text-black border-t border-neutral-200 pt-1">
                ➔ High score = High direct interaction volume.
              </p>
            </div>

            <div className="rounded-md border-2 border-black bg-neutral-50 p-3 space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-black uppercase text-black">Betweenness</span>
                <span className="rounded bg-black px-1.5 py-0.5 text-[9px] font-black text-white">Bridge Score</span>
              </div>
              <p className="text-[11px] font-semibold text-neutral-700 leading-relaxed">
                <strong>What it is:</strong> Measures how often a user sits on the shortest path between other people.
              </p>
              <p className="text-[10px] font-bold text-black border-t border-neutral-200 pt-1">
                ➔ High score = Information broker connecting separate groups.
              </p>
            </div>

            <div className="rounded-md border-2 border-black bg-neutral-50 p-3 space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-black uppercase text-black">Eigenvector</span>
                <span className="rounded bg-black px-1.5 py-0.5 text-[9px] font-black text-white">Authority Rank</span>
              </div>
              <p className="text-[11px] font-semibold text-neutral-700 leading-relaxed">
                <strong>What it is:</strong> Google PageRank-style score: connections to high-influence users count more.
              </p>
              <p className="text-[10px] font-bold text-black border-t border-neutral-200 pt-1">
                ➔ High score = Highest true network authority.
              </p>
            </div>

            <div className="rounded-md border-2 border-black bg-neutral-50 p-3 space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-black uppercase text-black">Community ID</span>
                <span className="rounded bg-black px-1.5 py-0.5 text-[9px] font-black text-white">Topic Cluster</span>
              </div>
              <p className="text-[11px] font-semibold text-neutral-700 leading-relaxed">
                <strong>What it is:</strong> Louvain algorithm clustering accounts discussing related topics.
              </p>
              <p className="text-[10px] font-bold text-black border-t border-neutral-200 pt-1">
                ➔ Same # = Same topic circle / community.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Key Opinion Leaders Table */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-black uppercase tracking-wider text-black flex items-center gap-1.5">
            <Sparkles className="h-3.5 w-3.5 fill-black" />
            Key Opinion Leaders Ranking Table
          </h4>
          <span className="text-[11px] font-bold text-neutral-600">
            Sorted by Eigenvector (Network Authority)
          </span>
        </div>

        <div className="overflow-x-auto rounded-lg border-2 border-black bg-white shadow-neo-sm">
          <table className="w-full text-left text-xs text-black">
            <thead className="border-b-2 border-black bg-neutral-100 text-[11px] font-black uppercase text-black">
              <tr>
                <th className="p-3">
                  <div>Handle</div>
                  <div className="text-[9px] font-bold text-neutral-500 normal-case">Account / Channel</div>
                </th>
                <th className="p-3">
                  <div className="flex items-center gap-1">
                    <span>Degree Centrality</span>
                    <span title="Direct Reach: fraction of direct connections & mentions" className="cursor-help text-neutral-600">ⓘ</span>
                  </div>
                  <div className="text-[9px] font-bold text-neutral-500 normal-case">Direct Activity & Mentions</div>
                </th>
                <th className="p-3">
                  <div className="flex items-center gap-1">
                    <span>Betweenness</span>
                    <span title="Bridge Score: gatekeeper score connecting different groups" className="cursor-help text-neutral-600">ⓘ</span>
                  </div>
                  <div className="text-[9px] font-bold text-neutral-500 normal-case">Community Bridge Score</div>
                </th>
                <th className="p-3">
                  <div className="flex items-center gap-1">
                    <span>Eigenvector</span>
                    <span title="Authority Score: influence weighted by connections to other influential nodes" className="cursor-help text-neutral-600">ⓘ</span>
                  </div>
                  <div className="text-[9px] font-bold text-neutral-500 normal-case">True Network Authority</div>
                </th>
                <th className="p-3">
                  <div className="flex items-center gap-1">
                    <span>Community</span>
                    <span title="Discussion Cluster: Louvain algorithm community group" className="cursor-help text-neutral-600">ⓘ</span>
                  </div>
                  <div className="text-[9px] font-bold text-neutral-500 normal-case">Sub-Group Cluster #</div>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y-2 divide-black font-mono text-[11px]">
              {paginatedKols.map((kol, idx) => {
                const cleanHandle = (kol.handle || '').replace(/^@+/, '');
                return (
                  <tr key={idx} className="hover:bg-neutral-100 font-sans">
                    <td className="p-3 font-black text-black">
                      <div className="flex items-center gap-1.5">
                        <span>@{cleanHandle}</span>
                        {idx === 0 && safeCurrentPage === 1 && (
                          <span className="rounded bg-black px-1.5 py-0.2 text-[9px] font-black text-white uppercase">#1 Lead</span>
                        )}
                      </div>
                    </td>
                    <td className="p-3 font-mono font-bold text-black">{(kol.degree_centrality || 0).toFixed(4)}</td>
                    <td className="p-3 font-mono font-bold text-black">{(kol.betweenness_centrality || 0).toFixed(4)}</td>
                    <td className="p-3 font-mono font-black text-black">{(kol.eigenvector_centrality || 0).toFixed(4)}</td>
                    <td className="p-3 font-bold text-neutral-700">
                      <span className="rounded border border-black bg-neutral-100 px-1.5 py-0.5 text-[10px] font-black">
                        Group #{kol.community_id || 0}
                      </span>
                    </td>
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
              <div className="text-xs font-black text-black">
                Showing <span className="underline">{startIndex + 1}–{endIndex}</span> of <span className="font-black">{totalKols}</span> Key Opinion Leaders
              </div>

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

      {/* Network Graph Visualizer (3D Animated Canvas / 2D Plotly) */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-black uppercase tracking-wider text-black flex items-center gap-1.5">
            <Box className="h-3.5 w-3.5 text-black" />
            {graphMode === '3d' ? '3D Interactive Orbit Constellation' : '2D Force Graph Plot'}
          </h4>
          <span className="text-[11px] font-semibold text-neutral-600">
            {graphMode === '3d'
              ? 'Click & drag to rotate in 3D • Scroll to zoom • Hover node to inspect cluster'
              : 'Scroll to zoom • Drag to pan • Hover for details'}
          </span>
        </div>

        {graphMode === '3d' ? (
          /* 3D Hardware-Accelerated Animated Canvas Graph Container */
          <div
            ref={containerRef}
            className={`relative w-full overflow-hidden rounded-xl border-2 border-black bg-black shadow-neo select-none transition-all ${
              isFullscreen ? 'fixed inset-0 z-50 h-screen w-screen rounded-none border-0 p-4' : 'h-[560px]'
            }`}
          >
            <canvas
              ref={canvasRef}
              onMouseDown={handleMouseDown3D}
              onMouseMove={handleMouseMove3D}
              onMouseUp={handleMouseUp3D}
              onMouseLeave={handleMouseLeave3D}
              onWheel={handleWheel3D}
              className="h-full w-full cursor-grab active:cursor-grabbing block"
            />

            {/* Top Right Sleek Glass Controls Bar */}
            <div className="absolute top-3 right-3 flex items-center gap-1.5 rounded-lg border border-white/10 bg-black/70 p-1 backdrop-blur-md shadow-lg pointer-events-auto">
              <button
                onClick={() => setAutoRotate((prev) => !prev)}
                className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-bold transition-all ${
                  autoRotate ? 'bg-white/20 text-white' : 'text-neutral-400 hover:text-white hover:bg-white/10'
                }`}
                title="Toggle Auto Orbit"
              >
                {autoRotate ? <Pause className="h-3 w-3 fill-current" /> : <Play className="h-3 w-3 fill-current" />}
                <span className="text-[11px]">{autoRotate ? 'Orbiting' : 'Paused'}</span>
              </button>

              <div className="h-3 w-[1px] bg-white/20 mx-0.5"></div>

              <button
                onClick={() => setZoom3D((z) => Math.min(2.5, z + 0.2))}
                className="rounded p-1 text-neutral-400 hover:bg-white/10 hover:text-white transition-colors"
                title="Zoom In"
              >
                <ZoomIn className="h-3.5 w-3.5" />
              </button>
              <button
                onClick={() => setZoom3D((z) => Math.max(0.4, z - 0.2))}
                className="rounded p-1 text-neutral-400 hover:bg-white/10 hover:text-white transition-colors"
                title="Zoom Out"
              >
                <ZoomOut className="h-3.5 w-3.5" />
              </button>
              <button
                onClick={resetCamera3D}
                className="rounded p-1 text-neutral-400 hover:bg-white/10 hover:text-white transition-colors"
                title="Reset Camera"
              >
                <RefreshCw className="h-3.5 w-3.5" />
              </button>
              <button
                onClick={() => setIsFullscreen((f) => !f)}
                className="rounded p-1 text-neutral-400 hover:bg-white/10 hover:text-white transition-colors"
                title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
              >
                {isFullscreen ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
              </button>
            </div>

            {/* Hover Node HUD Card */}
            {hoveredNode3D && (
              <div className="absolute bottom-3 left-3 z-20 pointer-events-none max-w-xs rounded-lg border border-white/15 bg-black/85 p-3 backdrop-blur-md shadow-2xl text-white space-y-1.5 transition-all">
                <div className="flex items-center justify-between border-b border-neutral-800 pb-1.5">
                  <div className="flex items-center gap-2">
                    <span
                      className="h-2.5 w-2.5 rounded-full border border-white/60 shadow-sm"
                      style={{ backgroundColor: hoveredNode3D.color }}
                    ></span>
                    <span className="text-xs font-bold text-white tracking-wide">
                      @{hoveredNode3D.handle}
                    </span>
                  </div>
                  {hoveredNode3D.is_kol && (
                    <span className="rounded bg-yellow-400/20 text-yellow-300 border border-yellow-400/40 px-1.5 py-0.2 text-[8px] font-bold uppercase tracking-wider">
                      Key Node
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-2 text-[10px] font-mono pt-0.5">
                  <div>
                    <span className="text-neutral-400 block text-[8px] uppercase">Eigenvector</span>
                    <span className="font-bold text-cyan-300">{hoveredNode3D.eigenvector.toFixed(4)}</span>
                  </div>
                  <div>
                    <span className="text-neutral-400 block text-[8px] uppercase">Degree</span>
                    <span className="font-bold text-white">{hoveredNode3D.degree.toFixed(4)}</span>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-1 border-t border-neutral-800 text-[9px] text-neutral-400">
                  <span>Community Cluster</span>
                  <span className="font-bold text-white flex items-center gap-1">
                    <span className="h-2 w-2 rounded-full inline-block" style={{ backgroundColor: hoveredNode3D.color }}></span>
                    Cluster #{hoveredNode3D.community}
                  </span>
                </div>
              </div>
            )}

            <div className="absolute bottom-2.5 right-3 pointer-events-none text-[10px] font-mono text-neutral-500">
              Drag to rotate • Scroll to zoom
            </div>
          </div>
        ) : (
          /* 2D Plotly Chart View */
          <div className="overflow-hidden rounded-lg border-2 border-black bg-white p-2 shadow-neo-sm">
            {plotData2D.length > 0 ? (
              <PlotlyChart
                className="w-full h-[520px]"
                data={plotData2D as any}
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
        )}
      </div>
    </div>
  );
};
