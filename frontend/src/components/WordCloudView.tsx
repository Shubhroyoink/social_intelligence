import React, { useState, useMemo } from 'react';
import { Cloud, ListOrdered, Search, X, Hash } from 'lucide-react';

interface WordCloudViewProps {
  words?: Array<{ text: string; value: number }>;
}

export const WordCloudView: React.FC<WordCloudViewProps> = ({ words = [] }) => {
  const [selectedLimit, setSelectedLimit] = useState<number | 'all'>(20);
  const [searchFilter, setSearchFilter] = useState('');
  const [viewMode, setViewMode] = useState<'cloud' | 'list'>('cloud');

  const safeWords = useMemo(() => {
    return [...(words || [])].sort((a, b) => b.value - a.value);
  }, [words]);

  const filteredWords = useMemo(() => {
    let list = safeWords;
    if (searchFilter.trim()) {
      const q = searchFilter.toLowerCase().trim();
      list = list.filter((w) => w.text.toLowerCase().includes(q));
    }
    if (selectedLimit === 'all') return list;
    return list.slice(0, selectedLimit);
  }, [safeWords, searchFilter, selectedLimit]);

  const totalTokens = safeWords.length;
  const totalOccurrences = useMemo(() => {
    return safeWords.reduce((sum, w) => sum + w.value, 0);
  }, [safeWords]);

  const maxVal = filteredWords.length > 0 ? Math.max(...filteredWords.map((w) => w.value)) : 1;
  const minVal = filteredWords.length > 0 ? Math.min(...filteredWords.map((w) => w.value)) : 1;

  const TAG_COLORS = [
    'bg-black text-white border-black',
    'bg-neutral-100 text-black border-black',
    'bg-neutral-900 text-white border-black',
    'bg-neutral-200 text-black border-black',
    'bg-neutral-800 text-white border-black',
    'bg-white text-black border-black',
  ];

  return (
    <div className="rounded-lg border-2 border-black bg-white p-5 shadow-neo space-y-5">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b-2 border-black pb-4">
        <div>
          <h3 className="text-base font-black text-black flex items-center gap-2 uppercase tracking-wide">
            <span className="flex h-7 w-7 items-center justify-center rounded-md border-2 border-black bg-black text-white shadow-neo-sm">
              <Cloud className="h-4 w-4 stroke-[2.5]" />
            </span>
            Word Cloud & Keyword Frequency
          </h3>
          <p className="text-xs font-semibold text-neutral-600 mt-1">
            Tokenized term frequency across normalized social posts & conversations
          </p>
        </div>

        {/* View Mode Toggle: Cloud vs List */}
        <div className="flex rounded-lg border-2 border-black bg-neutral-100 p-0.5 shadow-neo-sm self-start sm:self-auto">
          <button
            onClick={() => setViewMode('cloud')}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-black transition-all ${
              viewMode === 'cloud'
                ? 'bg-black text-white shadow-neo-sm'
                : 'text-black hover:bg-neutral-200'
            }`}
          >
            <Cloud className="h-3.5 w-3.5 stroke-[2.5]" />
            <span>Cloud</span>
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-black transition-all ${
              viewMode === 'list'
                ? 'bg-black text-white shadow-neo-sm'
                : 'text-black hover:bg-neutral-200'
            }`}
          >
            <ListOrdered className="h-3.5 w-3.5 stroke-[2.5]" />
            <span>Ranked List</span>
          </button>
        </div>
      </div>

      {/* Controls Bar: Top N Limit Selector + Search Filter */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-neutral-50 p-3 rounded-lg border-2 border-black shadow-neo-sm">
        {/* Top N Preset Buttons */}
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs font-black uppercase text-neutral-700 mr-1 flex items-center gap-1">
            <Hash className="h-3.5 w-3.5" /> Show Top:
          </span>
          {[10, 20, 30, 50, 'all'].map((limit) => {
            const isSelected = selectedLimit === limit;
            return (
              <button
                key={limit}
                onClick={() => setSelectedLimit(limit as any)}
                className={`rounded-md border-2 border-black px-2.5 py-1 text-xs font-black transition-all ${
                  isSelected
                    ? 'bg-black text-white shadow-neo-sm translate-x-[1px] translate-y-[1px]'
                    : 'bg-white text-black hover:bg-neutral-200 shadow-neo-sm'
                }`}
              >
                {limit === 'all' ? 'All' : `Top ${limit}`}
              </button>
            );
          })}
        </div>

        {/* Search Keyword Filter */}
        <div className="flex items-center gap-2">
          <div className="relative flex items-center">
            <Search className="absolute left-2.5 h-3.5 w-3.5 text-neutral-500" />
            <input
              type="text"
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              placeholder="Filter keyword..."
              className="h-8 rounded-md border-2 border-black bg-white pl-8 pr-7 text-xs font-bold text-black placeholder-neutral-500 shadow-neo-sm focus:outline-none focus:ring-2 focus:ring-black w-36 sm:w-44"
            />
            {searchFilter && (
              <button
                onClick={() => setSearchFilter('')}
                className="absolute right-2 text-xs text-neutral-500 hover:text-black"
                title="Clear search"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          <span className="rounded-md border-2 border-black bg-white px-2.5 py-1 text-[11px] font-black text-black shadow-neo-sm whitespace-nowrap">
            {filteredWords.length} / {totalTokens} Tokens
          </span>
        </div>
      </div>

      {/* Main Content Area */}
      {viewMode === 'cloud' ? (
        /* Cloud View */
        <div className="flex flex-wrap gap-2.5 sm:gap-3 items-center justify-center p-6 bg-neutral-50 rounded-lg border-2 border-black shadow-neo-sm min-h-[280px]">
          {filteredWords.map((item, idx) => {
            const range = maxVal - minVal || 1;
            const ratio = (item.value - minVal) / range;
            
            // Dynamic font sizing depending on slice size
            const minFont = selectedLimit === 10 ? 16 : 12;
            const maxFont = selectedLimit === 10 ? 34 : selectedLimit === 20 ? 28 : 24;
            const fontSize = Math.max(minFont, Math.min(maxFont, minFont + ratio * (maxFont - minFont)));
            
            const colorClass = TAG_COLORS[idx % TAG_COLORS.length];
            const isTop3 = idx < 3 && !searchFilter;

            return (
              <span
                key={idx}
                style={{ fontSize: `${fontSize}px` }}
                title={`Rank #${idx + 1} • Keyword: "${item.text}" • Mentioned ${item.value} times (${((item.value / (totalOccurrences || 1)) * 100).toFixed(1)}%)`}
                className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 font-black border-2 shadow-neo-sm transition-all hover:-translate-y-0.5 hover:shadow-neo cursor-default select-none ${colorClass}`}
              >
                {isTop3 && (
                  <span className="rounded bg-yellow-400 border border-black px-1 py-0.2 text-[9px] font-black text-black shadow-neo-xs">
                    #{idx + 1}
                  </span>
                )}
                <span>#{item.text}</span>
                <span className="text-[11px] font-bold opacity-75">({item.value})</span>
              </span>
            );
          })}

          {filteredWords.length === 0 && (
            <div className="flex flex-col items-center justify-center py-10 text-center">
              <Cloud className="h-8 w-8 text-neutral-400 mb-2" />
              <p className="text-xs font-bold text-neutral-500">
                {searchFilter ? `No keywords match "${searchFilter}"` : 'No tokenized words available'}
              </p>
            </div>
          )}
        </div>
      ) : (
        /* Ranked List View with Frequency Bars */
        <div className="rounded-lg border-2 border-black bg-white overflow-hidden shadow-neo-sm">
          <table className="w-full text-left text-xs text-black">
            <thead className="border-b-2 border-black bg-neutral-100 text-[11px] font-black uppercase text-black">
              <tr>
                <th className="p-3 w-16 text-center">Rank</th>
                <th className="p-3">Keyword</th>
                <th className="p-3 w-28 text-right">Frequency</th>
                <th className="p-3 w-44">Relative Volume</th>
              </tr>
            </thead>
            <tbody className="divide-y-2 divide-black">
              {filteredWords.map((item, idx) => {
                const pct = maxVal > 0 ? (item.value / maxVal) * 100 : 0;
                return (
                  <tr key={idx} className="hover:bg-neutral-50">
                    <td className="p-3 font-mono font-black text-center text-neutral-700">
                      {idx < 3 ? (
                        <span className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-black bg-black text-white text-[10px] font-black">
                          {idx + 1}
                        </span>
                      ) : (
                        `#${idx + 1}`
                      )}
                    </td>
                    <td className="p-3 font-black text-black font-mono">
                      #{item.text}
                    </td>
                    <td className="p-3 font-mono font-bold text-right text-black">
                      {item.value}
                    </td>
                    <td className="p-3">
                      <div className="flex items-center gap-2">
                        <div className="h-3 flex-1 rounded-full border border-black bg-neutral-100 overflow-hidden">
                          <div
                            className="h-full bg-black rounded-full transition-all duration-300"
                            style={{ width: `${pct}%` }}
                          ></div>
                        </div>
                        <span className="font-mono text-[10px] font-bold text-neutral-600 w-8 text-right">
                          {pct.toFixed(0)}%
                        </span>
                      </div>
                    </td>
                  </tr>
                );
              })}

              {filteredWords.length === 0 && (
                <tr>
                  <td colSpan={4} className="py-8 text-center text-xs font-bold text-neutral-500">
                    {searchFilter ? `No keywords match "${searchFilter}"` : 'No tokenized words available'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
