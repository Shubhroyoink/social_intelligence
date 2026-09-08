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
    <header className="sticky top-0 z-40 border-b border-neutral-800/80 bg-neutral-950/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3.5 sm:px-6 lg:px-8">
        {/* Brand & Topic Switcher */}
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-purple-500 shadow-lg shadow-indigo-500/20">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-bold tracking-tight text-white sm:text-base">
                  Social Intelligence
                </h1>
                <span className="rounded-full bg-indigo-500/10 px-2 py-0.5 text-[10px] font-semibold text-indigo-400 border border-indigo-500/20">
                  AI OSINT
                </span>
              </div>
              <p className="hidden text-[11px] text-neutral-400 sm:block">
                Multi-platform analytics & transformer intelligence
              </p>
            </div>
          </div>

          {/* Topic Dropdown */}
          <div className="flex items-center gap-2">
            <Layers className="h-4 w-4 text-neutral-400" />
            <select
              value={selectedTopic}
              onChange={(e) => onSelectTopic(e.target.value)}
              className="rounded-lg border border-neutral-800 bg-neutral-900 px-3 py-1.5 text-xs font-semibold text-neutral-200 shadow-inner focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
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
            <div className="flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-xs font-medium text-amber-400">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400 opacity-75"></span>
                <span className="relative inline-flex h-2 w-2 rounded-full bg-amber-500"></span>
              </span>
              <span className="truncate max-w-[140px] sm:max-w-none">{pipelineStatus.status_message}</span>
            </div>
          ) : (
            <div className="hidden sm:flex items-center gap-1.5 rounded-full border border-neutral-800 bg-neutral-900/60 px-3 py-1 text-[11px] text-neutral-400">
              <Activity className="h-3 w-3 text-emerald-500" />
              <span>Pipeline Idle</span>
            </div>
          )}

          {/* Refresh Button */}
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-1.5 rounded-lg border border-neutral-800 bg-neutral-900 px-3 py-1.5 text-xs font-medium text-neutral-300 transition-colors hover:bg-neutral-800 hover:text-white disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? "animate-spin text-indigo-400" : ""}`} />
            <span className="hidden sm:inline">Refresh</span>
          </button>

          {/* Run Pipeline Button */}
          <button
            onClick={onOpenPipelineModal}
            className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-md shadow-indigo-600/20 transition-all hover:bg-indigo-500 hover:shadow-indigo-500/30"
          >
            <Play className="h-3.5 w-3.5 fill-current" />
            <span>Run Pipeline</span>
          </button>
        </div>
      </div>
    </header>
  );
};
