import React from 'react';
import { Cloud } from 'lucide-react';

interface WordCloudViewProps {
  words?: Array<{ text: string; value: number }>;
}

export const WordCloudView: React.FC<WordCloudViewProps> = ({ words = [] }) => {
  const safeWords = words || [];
  const maxVal = safeWords.length > 0 ? Math.max(...safeWords.map((w) => w.value)) : 1;

  return (
    <div className="rounded-2xl border border-neutral-800/80 bg-neutral-900/60 p-6 backdrop-blur-sm">
      <div className="flex items-center justify-between border-b border-neutral-800 pb-4">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <Cloud className="h-4 w-4 text-indigo-400" />
            Word Cloud
          </h3>
          <p className="text-xs text-neutral-400">Tokenized term frequency across normalized social posts</p>
        </div>
        <span className="rounded-full bg-neutral-800 px-2.5 py-1 text-xs font-semibold text-neutral-400">
          {safeWords.length} Tokens
        </span>
      </div>

      <div className="mt-6 flex flex-wrap gap-2.5 items-center justify-center p-4 bg-neutral-950/40 rounded-xl border border-neutral-800/60 min-h-[260px]">
        {safeWords.map((item, idx) => {
          const ratio = item.value / maxVal;
          const fontSize = Math.max(11, Math.min(28, 12 + ratio * 16));
          const opacity = Math.max(0.6, Math.min(1, 0.4 + ratio * 0.6));
          const isHigh = ratio > 0.4;

          return (
            <span
              key={idx}
              style={{ fontSize: `${fontSize}px`, opacity }}
              className={`inline-flex items-center gap-1 rounded-lg px-2.5 py-1 font-semibold transition-all hover:scale-110 cursor-pointer ${
                isHigh
                  ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                  : 'bg-neutral-800/60 text-neutral-300 border border-neutral-700/40'
              }`}
            >
              #{item.text}
              <span className="text-[10px] font-normal text-neutral-400">({item.value})</span>
            </span>
          );
        })}

        {safeWords.length === 0 && (
          <p className="text-xs text-neutral-500">No tokenized words available</p>
        )}
      </div>
    </div>
  );
};
