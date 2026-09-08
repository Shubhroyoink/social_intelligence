import React from 'react';
import { Cloud } from 'lucide-react';

interface WordCloudViewProps {
  words?: Array<{ text: string; value: number }>;
}

export const WordCloudView: React.FC<WordCloudViewProps> = ({ words = [] }) => {
  const safeWords = words || [];
  const maxVal = safeWords.length > 0 ? Math.max(...safeWords.map((w) => w.value)) : 1;

  const TAG_COLORS = [
    'bg-black text-white',
    'bg-neutral-100 text-black',
    'bg-neutral-800 text-white',
    'bg-neutral-200 text-black',
    'bg-neutral-900 text-white',
    'bg-white text-black',
  ];

  return (
    <div className="rounded-lg border-2 border-black bg-white p-6 shadow-neo">
      <div className="flex items-center justify-between border-b-2 border-black pb-4">
        <div>
          <h3 className="text-base font-black text-black flex items-center gap-2 uppercase tracking-wide">
            <span className="flex h-7 w-7 items-center justify-center rounded-md border-2 border-black bg-black text-white shadow-neo-sm">
              <Cloud className="h-4 w-4 stroke-[2.5]" />
            </span>
            Word Cloud
          </h3>
          <p className="text-xs font-semibold text-neutral-600 mt-1">Tokenized term frequency across normalized social posts</p>
        </div>
        <span className="rounded-md border-2 border-black bg-neutral-100 px-2.5 py-1 text-xs font-black text-black shadow-neo-sm">
          {safeWords.length} Tokens
        </span>
      </div>

      <div className="mt-6 flex flex-wrap gap-3 items-center justify-center p-6 bg-neutral-50 rounded-lg border-2 border-black shadow-neo-sm min-h-[260px]">
        {safeWords.map((item, idx) => {
          const ratio = item.value / maxVal;
          const fontSize = Math.max(12, Math.min(26, 13 + ratio * 14));
          const colorClass = TAG_COLORS[idx % TAG_COLORS.length];

          return (
            <span
              key={idx}
              style={{ fontSize: `${fontSize}px` }}
              className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 font-black border-2 border-black shadow-neo-sm transition-all hover:translate-x-[1px] hover:translate-y-[1px] cursor-pointer ${colorClass}`}
            >
              #{item.text}
              <span className="text-[11px] font-bold opacity-80">({item.value})</span>
            </span>
          );
        })}

        {safeWords.length === 0 && (
          <p className="text-xs font-bold text-neutral-500">No tokenized words available</p>
        )}
      </div>
    </div>
  );
};
