import React from 'react';
import {
  MessageSquare,
  Smile,
  Frown,
  CheckCircle,
} from 'lucide-react';
import type { OverviewStats } from '../types';

interface OverviewCardsProps {
  stats: OverviewStats | null;
}

export const OverviewCards: React.FC<OverviewCardsProps> = ({ stats }) => {
  if (!stats) return null;

  // Exact 4 metric cards matching Streamlit c1, c2, c3, c4
  const cards = [
    {
      title: 'Posts Collected',
      value: stats.total_posts.toLocaleString(),
      icon: MessageSquare,
      color: 'text-indigo-400',
      bg: 'bg-indigo-500/10 border-indigo-500/20',
    },
    {
      title: 'Posts Analyzed',
      value: stats.total_analyzed.toLocaleString(),
      icon: CheckCircle,
      color: 'text-sky-400',
      bg: 'bg-sky-500/10 border-sky-500/20',
    },
    {
      title: 'Positive',
      value: `${stats.positive_pct}%`,
      icon: Smile,
      color: 'text-emerald-400',
      bg: 'bg-emerald-500/10 border-emerald-500/20',
    },
    {
      title: 'Negative',
      value: `${stats.negative_pct}%`,
      icon: Frown,
      color: 'text-rose-400',
      bg: 'bg-rose-500/10 border-rose-500/20',
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {cards.map((c, i) => {
        const Icon = c.icon;
        return (
          <div
            key={i}
            className="flex items-center justify-between rounded-xl border border-neutral-800 bg-neutral-900/60 p-4 backdrop-blur-sm transition-all hover:border-neutral-700"
          >
            <div>
              <span className="text-xs font-semibold text-neutral-400">{c.title}</span>
              <div className="mt-1 text-2xl font-bold tracking-tight text-white">{c.value}</div>
            </div>
            <div className={`rounded-xl border p-2.5 ${c.bg}`}>
              <Icon className={`h-5 w-5 ${c.color}`} />
            </div>
          </div>
        );
      })}
    </div>
  );
};
