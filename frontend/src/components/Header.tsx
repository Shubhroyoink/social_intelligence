import React from 'react';
import { RefreshCw, Play, Sparkles, Activity, Layers } from 'lucide-react';
import type { PipelineStatus } from '../types';

interface HeaderProps {
  topics: string[];
  selectedTopic: string;
  onSelectTopic: (topic: string) => void;
  onOpenPipelineModal: () => void;
  onRefresh: () => void;
  isRefreshing: boolean;
  pipelineStatus: PipelineStatus;
}

export const Header: React.FC<HeaderProps> = ({
  topics,
  selectedTopic,
  onSelectTopic,
  onOpenPipelineModal,
  onRefresh,
  isRefreshing,
  pipelineStatus,
}) => {
  return (
    <header className="sticky top-0 z-40 border-b-[3px] border-black bg-white shadow-[0_4px_0px_0px_#000000]">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
        {/* Brand & Topic Switcher */}
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg border-2 border-black bg-black text-white shadow-neo-sm">
              <Sparkles className="h-5 w-5 fill-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-black tracking-tight text-black sm:text-lg uppercase">
                  Social Intelligence
                </h1>
                <span className="rounded-md border-2 border-black bg-neutral-200 px-2 py-0.5 text-[11px] font-black text-black shadow-neo-sm">
                  OSINT AI
                </span>
              </div>
              <p className="hidden text-[11px] font-semibold text-neutral-600 sm:block">
                Multi-platform analytics & transformer intelligence
              </p>
            </div>
          </div>

          {/* Topic Dropdown */}
          <div className="flex items-center gap-2">
            <Layers className="h-4 w-4 text-black font-bold" />
            <select
              value={selectedTopic}
              onChange={(e) => onSelectTopic(e.target.value)}
              className="rounded-lg border-2 border-black bg-white px-3 py-1.5 text-xs font-bold text-black shadow-neo-sm focus:bg-neutral-100 focus:outline-none cursor-pointer"
            >
              <option value="All">All Topics ({topics.length})</option>
              {topics.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Actions & Pipeline Status */}
        <div className="flex items-center gap-3">
          {/* Status Indicator */}
          {pipelineStatus.is_running ? (
            <div className="flex items-center gap-2 rounded-lg border-2 border-black bg-black px-3 py-1 text-xs font-black text-white shadow-neo-sm">
              <span className="relative flex h-2.5 w-2.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-white opacity-75"></span>
                <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-white"></span>
              </span>
              <span className="truncate max-w-[140px] sm:max-w-none">{pipelineStatus.status_message}</span>
            </div>
          ) : (
            <div className="hidden sm:flex items-center gap-1.5 rounded-lg border-2 border-black bg-neutral-100 px-3 py-1 text-xs font-black text-black shadow-neo-sm">
              <Activity className="h-3.5 w-3.5 text-black stroke-[2.5]" />
              <span>Pipeline Idle</span>
            </div>
          )}

          {/* Refresh Button */}
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="neo-btn flex items-center gap-1.5 rounded-lg bg-white px-3.5 py-1.5 text-xs font-bold text-black hover:bg-neutral-100 disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? "animate-spin text-black" : ""}`} />
            <span className="hidden sm:inline">Refresh</span>
          </button>

          {/* Run Pipeline Button */}
          <button
            onClick={onOpenPipelineModal}
            className="neo-btn flex items-center gap-1.5 rounded-lg bg-black px-4 py-1.5 text-xs font-black text-white hover:bg-neutral-800"
          >
            <Play className="h-3.5 w-3.5 fill-current" />
            <span>Run Pipeline</span>
          </button>
        </div>
      </div>
    </header>
  );
};
