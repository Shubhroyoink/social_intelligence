import React, { useState } from 'react';
import { Database, Search, Filter, ThumbsUp, Share2 } from 'lucide-react';
import type { Post } from '../types';

interface PostsExplorerProps {
  posts: Post[];
  onSearch: (query: string) => void;
  onFilterPlatform: (platform: string) => void;
  onFilterSentiment: (sentiment: string) => void;
  selectedPlatform: string;
  selectedSentiment: string;
}

export const PostsExplorer: React.FC<PostsExplorerProps> = ({
  posts,
  onSearch,
  onFilterPlatform,
  onFilterSentiment,
  selectedPlatform,
  selectedSentiment,
}) => {
  const [searchInput, setSearchInput] = useState('');

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch(searchInput);
  };

  const getSentimentBadge = (sentiment?: string) => {
    if (sentiment === 'positive') {
      return <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-400 border border-emerald-500/20">positive</span>;
    }
    if (sentiment === 'negative') {
      return <span className="rounded-full bg-rose-500/10 px-2 py-0.5 text-[10px] font-semibold text-rose-400 border border-rose-500/20">negative</span>;
    }
    return <span className="rounded-full bg-neutral-800 px-2 py-0.5 text-[10px] font-semibold text-neutral-400 border border-neutral-700">neutral</span>;
  };

  const getPlatformBadge = (platform: string) => {
    const p = platform.toLowerCase();
    if (p === 'youtube') return <span className="text-[10px] font-bold text-red-400 uppercase">YouTube</span>;
    if (p === 'telegram') return <span className="text-[10px] font-bold text-sky-400 uppercase">Telegram</span>;
    return <span className="text-[10px] font-bold text-neutral-300 uppercase">X</span>;
  };

  return (
    <div className="rounded-2xl border border-neutral-800/80 bg-neutral-900/60 p-5 backdrop-blur-sm space-y-4">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-neutral-800 pb-4">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <Database className="h-4 w-4 text-indigo-400" />
            Sample Posts Explorer ({posts.length})
          </h3>
          <p className="text-xs text-neutral-400">View collected and normalized posts stored in SQLite database</p>
        </div>

        {/* Search Bar */}
        <form onSubmit={handleSearchSubmit} className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-neutral-400" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Search post text / author..."
              className="w-48 sm:w-64 rounded-lg border border-neutral-800 bg-neutral-950 py-1.5 pl-8 pr-3 text-xs text-white focus:border-indigo-500 focus:outline-none"
            />
          </div>
          <button
            type="submit"
            className="rounded-lg bg-neutral-800 px-3 py-1.5 text-xs font-semibold text-neutral-200 hover:bg-neutral-700"
          >
            Search
          </button>
        </form>
      </div>

      {/* Filters matching Streamlit sidebar options */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1.5 text-xs text-neutral-400">
          <Filter className="h-3.5 w-3.5" />
          <span>Platform:</span>
          {['All', 'youtube', 'telegram', 'x'].map((plat) => (
            <button
              key={plat}
              onClick={() => onFilterPlatform(plat)}
              className={`rounded-md px-2 py-1 text-[11px] font-semibold transition-all ${
                selectedPlatform === plat
                  ? 'bg-indigo-600 text-white'
                  : 'bg-neutral-800 text-neutral-400 hover:text-white'
              }`}
            >
              {plat.toUpperCase()}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-1.5 text-xs text-neutral-400 ml-auto">
          <span>Sentiment:</span>
          {['All', 'positive', 'neutral', 'negative'].map((sent) => (
            <button
              key={sent}
              onClick={() => onFilterSentiment(sent)}
              className={`rounded-md px-2 py-1 text-[11px] font-semibold transition-all ${
                selectedSentiment === sent
                  ? 'bg-indigo-600 text-white'
                  : 'bg-neutral-800 text-neutral-400 hover:text-white'
              }`}
            >
              {sent.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Posts Table */}
      <div className="overflow-x-auto rounded-xl border border-neutral-800">
        <table className="w-full text-left text-xs text-neutral-300">
          <thead className="border-b border-neutral-800 bg-neutral-950/80 text-[11px] uppercase text-neutral-400">
            <tr>
              <th className="p-3">Platform</th>
              <th className="p-3">Author Handle</th>
              <th className="p-3">Post Content</th>
              <th className="p-3">Sentiment & Stance</th>
              <th className="p-3">Date</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-800/60 bg-neutral-900/30">
            {posts.map((post) => (
              <tr key={post.id} className="hover:bg-neutral-800/30">
                <td className="p-3 whitespace-nowrap align-top">
                  {getPlatformBadge(post.platform)}
                </td>
                <td className="p-3 whitespace-nowrap align-top font-semibold text-white">
                  {post.author_handle || 'Anonymous'}
                </td>
                <td className="p-3 max-w-lg">
                  <p className="line-clamp-3 text-neutral-200">{post.text}</p>
                </td>
                <td className="p-3 whitespace-nowrap align-top">
                  <div className="flex flex-col gap-1">
                    <div>{getSentimentBadge(post.sentiment)}</div>
                    {post.primary_emotion && (
                      <span className="text-[10px] text-neutral-400 capitalize">
                        {post.primary_emotion} {post.sarcasm_flag ? '· Sarcastic' : ''}
                      </span>
                    )}
                  </div>
                </td>
                <td className="p-3 whitespace-nowrap align-top text-neutral-400 text-[11px]">
                  {post.created_at ? post.created_at.slice(0, 10) : 'N/A'}
                </td>
              </tr>
            ))}

            {posts.length === 0 && (
              <tr>
                <td colSpan={5} className="py-8 text-center text-xs text-neutral-500">
                  No posts matching selected criteria
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
