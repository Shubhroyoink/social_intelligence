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
        <div className="flex flex-wrap items-center gap-4 sm:gap-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg border-2 border-black bg-black text-white shadow-neo-sm">
              <Sparkles className="h-5 w-5 fill-white" />
            </div>
            <div>
              <h1 className="text-xl font-black tracking-tight text-black sm:text-2xl uppercase leading-none">
                Social Intelligence
              </h1>
              <p className="hidden text-[11px] font-bold text-neutral-600 sm:block mt-0.5">
                Multi-platform analytics & transformer intelligence
              </p>
            </div>
          </div>

          {/* Topic Dropdown with Executive Pill Styling */}
          <div className="flex items-center">
            <div className="flex items-center rounded-lg border-2 border-black bg-neutral-100 p-1 shadow-neo-sm">
              <div className="flex items-center gap-1.5 px-2 text-[11px] font-black text-black uppercase tracking-wider">
                <Layers className="h-3.5 w-3.5 stroke-[2.5]" />
                <span className="hidden md:inline text-neutral-600">Topic:</span>
              </div>
              <div className="relative">
                <select
                  value={selectedTopic}
                  onChange={(e) => onSelectTopic(e.target.value)}
                  className="appearance-none rounded-md border-2 border-black bg-white py-1 pl-2.5 pr-7 text-xs font-black text-black shadow-neo-sm hover:bg-neutral-50 focus:bg-white focus:outline-none cursor-pointer transition-all"
                >
                  <option value="All">All Topics ({topics.length})</option>
                  {topics.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
                <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2 text-black">
                  <svg className="h-3.5 w-3.5 fill-current" viewBox="0 0 20 20">
                    <path d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" />
                  </svg>
                </div>
              </div>
            </div>
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
