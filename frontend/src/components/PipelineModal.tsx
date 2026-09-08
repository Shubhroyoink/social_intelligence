import React, { useState } from 'react';
import { X, Play, Settings, AlertCircle, CheckCircle2 } from 'lucide-react';
import { triggerPipeline } from '../api';

interface PipelineModalProps {
  isOpen: boolean;
  onClose: () => void;
  onTriggerSuccess: () => void;
}

export const PipelineModal: React.FC<PipelineModalProps> = ({ isOpen, onClose, onTriggerSuccess }) => {
  const [topic, setTopic] = useState('Gen AI');
  const [channels, setChannels] = useState('@aipost, @KDnuggets, @theaiexecutive');
  const [xQueries, setXQueries] = useState('Gen AI, LLM');
  const [youtubeSearch, setYoutubeSearch] = useState(true);
  const [ytMaxVideos, setYtMaxVideos] = useState(5);
  const [ytComments, setYtComments] = useState(100);

  const [isLoading, setIsLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setStatusMessage(null);

    try {
      const channelList = channels
        .split(',')
        .map((c) => c.trim())
        .filter(Boolean);

      const xQueryList = xQueries
        .split(',')
        .map((q) => q.trim())
        .filter(Boolean);

      const res = await triggerPipeline({
        topic: topic.trim() || 'Gen AI',
        channels: channelList.length > 0 ? channelList : undefined,
        x_queries: xQueryList.length > 0 ? xQueryList : undefined,
        youtube_search: youtubeSearch,
        yt_max_videos: Number(ytMaxVideos),
        yt_comments: Number(ytComments),
      });

      setStatusMessage(res.message);
      onTriggerSuccess();
      setTimeout(() => {
        onClose();
      }, 1500);
    } catch (err: any) {
      setError(err.message || 'Failed to trigger pipeline');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
      <div className="relative w-full max-w-lg rounded-2xl border border-neutral-800 bg-neutral-900 p-6 shadow-2xl">
        <div className="flex items-center justify-between border-b border-neutral-800 pb-4">
          <div className="flex items-center gap-2">
            <div className="rounded-lg bg-indigo-500/20 p-2 text-indigo-400">
              <Settings className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Execute Social Analytics Pipeline</h3>
              <p className="text-xs text-neutral-400">Run multi-platform collectors & ML transformers</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-800 hover:text-white"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleRun} className="mt-4 space-y-4">
          {/* Topic */}
          <div>
            <label className="block text-xs font-semibold text-neutral-300">
              Topic Query <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              required
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g. Gen AI, AI Agents, Cybersecurity"
              className="mt-1 w-full rounded-lg border border-neutral-800 bg-neutral-950 px-3 py-2 text-xs text-white focus:border-indigo-500 focus:outline-none"
            />
          </div>

          {/* Telegram Channels */}
          <div>
            <label className="block text-xs font-semibold text-neutral-300">
              Telegram Channels (comma-separated)
            </label>
            <input
              type="text"
              value={channels}
              onChange={(e) => setChannels(e.target.value)}
              placeholder="@aipost, @KDnuggets, @theaiexecutive"
              className="mt-1 w-full rounded-lg border border-neutral-800 bg-neutral-950 px-3 py-2 text-xs text-white focus:border-indigo-500 focus:outline-none"
            />
          </div>

          {/* X Queries */}
          <div>
            <label className="block text-xs font-semibold text-neutral-300">
              X (Twitter) Search Queries (comma-separated)
            </label>
            <input
              type="text"
              value={xQueries}
              onChange={(e) => setXQueries(e.target.value)}
              placeholder="Gen AI, LLM"
              className="mt-1 w-full rounded-lg border border-neutral-800 bg-neutral-950 px-3 py-2 text-xs text-white focus:border-indigo-500 focus:outline-none"
            />
          </div>

          {/* YouTube Settings */}
          <div className="rounded-xl border border-neutral-800 bg-neutral-950/60 p-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-neutral-300">YouTube Data API v3</span>
              <label className="flex items-center gap-1.5 text-xs text-neutral-400 cursor-pointer">
                <input
                  type="checkbox"
                  checked={youtubeSearch}
                  onChange={(e) => setYoutubeSearch(e.target.checked)}
                  className="rounded border-neutral-700 bg-neutral-800 text-indigo-600 focus:ring-indigo-500"
                />
                <span>Auto-Discover Videos</span>
              </label>
            </div>
            {youtubeSearch && (
              <div className="mt-3 grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] text-neutral-400">Max Videos</label>
                  <input
                    type="number"
                    min={1}
                    max={20}
                    value={ytMaxVideos}
                    onChange={(e) => setYtMaxVideos(Number(e.target.value))}
                    className="mt-1 w-full rounded-lg border border-neutral-800 bg-neutral-900 px-2.5 py-1.5 text-xs text-white"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-neutral-400">Comments / Video</label>
                  <input
                    type="number"
                    min={10}
                    max={500}
                    value={ytComments}
                    onChange={(e) => setYtComments(Number(e.target.value))}
                    className="mt-1 w-full rounded-lg border border-neutral-800 bg-neutral-900 px-2.5 py-1.5 text-xs text-white"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Status feedback */}
          {statusMessage && (
            <div className="flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-2.5 text-xs text-emerald-400">
              <CheckCircle2 className="h-4 w-4 shrink-0" />
              <span>{statusMessage}</span>
            </div>
          )}

          {error && (
            <div className="flex items-center gap-2 rounded-lg border border-rose-500/30 bg-rose-500/10 p-2.5 text-xs text-rose-400">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Modal Footer */}
          <div className="flex items-center justify-end gap-2 border-t border-neutral-800 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-neutral-800 px-4 py-2 text-xs font-semibold text-neutral-300 hover:bg-neutral-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-md hover:bg-indigo-500 disabled:opacity-50"
            >
              <Play className="h-3.5 w-3.5 fill-current" />
              <span>{isLoading ? 'Starting...' : 'Run Analysis Pipeline'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
