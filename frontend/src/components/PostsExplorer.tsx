import React, { useState, useMemo } from 'react';
import { Database, Search, Filter, ChevronLeft, ChevronRight } from 'lucide-react';
import type { Post } from '../types';

interface PostsExplorerProps {
  posts: Post[];
  onSearch?: (query: string) => void;
  onFilterPlatform?: (platform: string) => void;
  onFilterSentiment?: (sentiment: string) => void;
  selectedPlatform?: string;
  selectedSentiment?: string;
}

export const PostsExplorer: React.FC<PostsExplorerProps> = ({
  posts = [],
}) => {
  // Local state for instant zero-latency client-side filtering and pagination
  const [selectedPlatform, setSelectedPlatform] = useState<string>('All');
  const [selectedSentiment, setSelectedSentiment] = useState<string>('All');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [pageSize, setPageSize] = useState<number | 'all'>(10);
  const [currentPage, setCurrentPage] = useState<number>(1);

  const handlePlatformChange = (plat: string) => {
    setSelectedPlatform(plat);
    setCurrentPage(1);
  };

  const handleSentimentChange = (sent: string) => {
    setSelectedSentiment(sent);
    setCurrentPage(1);
  };

  const handleSearchChange = (val: string) => {
    setSearchQuery(val);
    setCurrentPage(1);
  };

  // Instant in-memory filtering (0ms latency, 100% reliable across all posts)
  const filteredPosts = useMemo(() => {
    if (!Array.isArray(posts)) return [];
    const pFilter = selectedPlatform.toLowerCase().trim();
    const sFilter = selectedSentiment.toLowerCase().trim();
    const qFilter = searchQuery.toLowerCase().trim();

    return posts.filter((post) => {
      if (!post) return false;

      // Platform filter
      if (pFilter !== 'all') {
        const p = (post.platform || '').toLowerCase().trim();
        if (p !== pFilter) return false;
      }

      // Sentiment filter
      if (sFilter !== 'all') {
        const s = (post.sentiment || '').toLowerCase().trim();
        if (s !== sFilter) return false;
      }

      // Text / Author search filter
      if (qFilter) {
        const textMatch = (post.text || '').toLowerCase().includes(qFilter);
        const rawMatch = (post.raw_text || '').toLowerCase().includes(qFilter);
        const authorMatch = (post.author_handle || '').toLowerCase().includes(qFilter);
        if (!textMatch && !rawMatch && !authorMatch) return false;
      }

      return true;
    });
  }, [posts, selectedPlatform, selectedSentiment, searchQuery]);

  // Pagination calculation
  const totalPosts = filteredPosts.length;
  const effectivePageSize = pageSize === 'all' ? (totalPosts || 1) : pageSize;
  const totalPages = Math.max(1, Math.ceil(totalPosts / effectivePageSize));
  const safeCurrentPage = Math.min(Math.max(1, currentPage), totalPages);

  const startIndex = (safeCurrentPage - 1) * effectivePageSize;
  const endIndex = pageSize === 'all' ? totalPosts : Math.min(startIndex + effectivePageSize, totalPosts);
  const paginatedPosts = filteredPosts.slice(startIndex, endIndex);

  const getSentimentBadge = (sentiment?: string) => {
    const s = (sentiment || '').toLowerCase().trim();
    if (s === 'positive' || s === 'pos') {
      return <span className="rounded-md border-2 border-black bg-black px-2 py-0.5 text-[10px] font-black text-white shadow-neo-sm">POSITIVE</span>;
    }
    if (s === 'negative' || s === 'neg') {
      return <span className="rounded-md border-2 border-black bg-neutral-200 px-2 py-0.5 text-[10px] font-black text-black shadow-neo-sm">NEGATIVE</span>;
    }
    return <span className="rounded-md border-2 border-black bg-white px-2 py-0.5 text-[10px] font-black text-black shadow-neo-sm">NEUTRAL</span>;
  };

  const getPlatformBadge = (platform: string) => {
    const p = (platform || '').toLowerCase();
    if (p === 'youtube') return <span className="rounded border-2 border-black bg-neutral-200 px-1.5 py-0.5 text-[10px] font-black text-black uppercase shadow-neo-sm">YouTube</span>;
    if (p === 'telegram') return <span className="rounded border-2 border-black bg-neutral-100 px-1.5 py-0.5 text-[10px] font-black text-black uppercase shadow-neo-sm">Telegram</span>;
    return <span className="rounded border-2 border-black bg-white px-1.5 py-0.5 text-[10px] font-black text-black uppercase shadow-neo-sm">X</span>;
  };

  return (
    <div className="rounded-lg border-2 border-black bg-white p-5 shadow-neo space-y-4">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b-2 border-black pb-4">
        <div>
          <h3 className="text-base font-black text-black flex items-center gap-2 uppercase tracking-wide">
            <span className="flex h-7 w-7 items-center justify-center rounded-md border-2 border-black bg-black text-white shadow-neo-sm">
              <Database className="h-4 w-4 stroke-[2.5]" />
            </span>
            Sample Posts Explorer ({totalPosts})
          </h3>
          <p className="text-xs font-semibold text-neutral-600 mt-1">View collected and normalized posts stored in SQLite database</p>
        </div>

        {/* Search Bar */}
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-neutral-600" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => handleSearchChange(e.target.value)}
              placeholder="Search post text / author..."
              className="w-48 sm:w-64 rounded-lg border-2 border-black bg-white py-1.5 pl-8 pr-3 text-xs font-bold text-black shadow-neo-sm focus:bg-neutral-100 focus:outline-none"
            />
          </div>
          {searchQuery && (
            <button
              onClick={() => handleSearchChange('')}
              className="neo-btn rounded-lg bg-neutral-200 px-3 py-1.5 text-xs font-black text-black hover:bg-neutral-300"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Filters matching Streamlit sidebar options */}
      <div className="flex flex-wrap items-center gap-4 bg-neutral-50 p-3 rounded-lg border-2 border-black">
        <div className="flex items-center gap-1.5 text-xs font-black text-black">
          <Filter className="h-3.5 w-3.5 stroke-[2.5]" />
          <span className="uppercase">Platform:</span>
          {['All', 'youtube', 'telegram', 'x'].map((plat) => (
            <button
              key={plat}
              onClick={() => handlePlatformChange(plat)}
              className={`rounded-md border-2 border-black px-2.5 py-1 text-[11px] font-black transition-all ${
                selectedPlatform.toLowerCase() === plat.toLowerCase()
                  ? 'bg-black text-white shadow-neo-sm translate-x-[1px] translate-y-[1px]'
                  : 'bg-white text-black hover:bg-neutral-100 shadow-neo-sm'
              }`}
            >
              {plat.toUpperCase()}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-1.5 text-xs font-black text-black sm:ml-auto">
          <span className="uppercase">Sentiment:</span>
          {['All', 'positive', 'neutral', 'negative'].map((sent) => (
            <button
              key={sent}
              onClick={() => handleSentimentChange(sent)}
              className={`rounded-md border-2 border-black px-2.5 py-1 text-[11px] font-black transition-all ${
                selectedSentiment.toLowerCase() === sent.toLowerCase()
                  ? 'bg-black text-white shadow-neo-sm translate-x-[1px] translate-y-[1px]'
                  : 'bg-white text-black hover:bg-neutral-100 shadow-neo-sm'
              }`}
            >
              {sent.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Posts Table */}
      <div className="overflow-x-auto rounded-lg border-2 border-black shadow-neo-sm">
        <table className="w-full text-left text-xs text-black">
          <thead className="border-b-2 border-black bg-neutral-100 text-[11px] font-black uppercase text-black">
            <tr>
              <th className="p-3">Platform</th>
              <th className="p-3">Author Handle</th>
              <th className="p-3">Post Content</th>
              <th className="p-3">Sentiment & Stance</th>
              <th className="p-3">Date</th>
            </tr>
          </thead>
          <tbody className="divide-y-2 divide-black bg-white">
            {paginatedPosts.map((post) => {
              const cleanHandle = (post.author_handle || 'Anonymous').replace(/^@+/, '');
              return (
                <tr key={post.id} className="hover:bg-neutral-100">
                  <td className="p-3 whitespace-nowrap align-top">
                    {getPlatformBadge(post.platform)}
                  </td>
                  <td className="p-3 whitespace-nowrap align-top font-black text-black">
                    @{cleanHandle}
                  </td>
                  <td className="p-3 max-w-lg">
                    <p className="line-clamp-3 font-semibold text-neutral-800">{post.text}</p>
                  </td>
                  <td className="p-3 whitespace-nowrap align-top">
                    <div className="flex flex-col gap-1.5">
                      <div>{getSentimentBadge(post.sentiment)}</div>
                      {post.primary_emotion && (
                        <span className="text-[10px] font-bold text-neutral-600 capitalize">
                          {post.primary_emotion} {post.sarcasm_flag ? '· Sarcastic' : ''}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="p-3 whitespace-nowrap align-top text-neutral-600 font-bold text-[11px]">
                    {post.created_at ? post.created_at.slice(0, 10) : 'N/A'}
                  </td>
                </tr>
              );
            })}

            {filteredPosts.length === 0 && (
              <tr>
                <td colSpan={5} className="py-8 text-center text-xs font-bold text-neutral-500">
                  No posts matching selected criteria
                </td>
              </tr>
            )}
          </tbody>
        </table>

        {/* Bottom Choose Section & Pagination Controls */}
        {totalPosts > 0 && (
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 border-t-2 border-black bg-neutral-50 p-3">
            {/* Left: Row range status */}
            <div className="text-xs font-black text-black">
              Showing <span className="underline">{startIndex + 1}–{endIndex}</span> of <span className="font-black">{totalPosts}</span> Sample Posts
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
  );
};
