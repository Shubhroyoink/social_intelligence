import React from 'react';
import ReactMarkdown from 'react-markdown';
import { FileText, Download, Sparkles } from 'lucide-react';
import type { Narrative } from '../types';

interface NarrativeViewProps {
  narrative: Narrative | null;
  narratives: Narrative[];
}

export const NarrativeView: React.FC<NarrativeViewProps> = ({ narrative }) => {
  const handleDownload = () => {
    if (!narrative) return;
    const content = narrative.report_markdown || narrative.report_text || '';
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `report_${narrative.topic_query || 'general'}_${narrative.created_at.slice(0, 10)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const getCaption = () => {
    if (!narrative) return '';
    const dateStr = (narrative.created_at || '').slice(0, 19).replace('T', ' ');
    if (narrative.backend === 'gemini') {
      return `Generated ${dateStr} UTC · Gemini (${narrative.model || 'gemini-3.5-flash'})`;
    }
    return `Generated ${dateStr} UTC · Template fallback (no LLM_API_KEY set)`;
  };

  const reportText = narrative?.report_markdown || narrative?.report_text;

  return (
    <div className="rounded-2xl border border-neutral-800/80 bg-neutral-900/60 p-6 backdrop-blur-sm">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-neutral-800 pb-4">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-indigo-400" />
            Executive Summary / AI Narrative
          </h2>
          <p className="text-xs text-neutral-400 mt-1">
            {narrative ? getCaption() : 'No narrative report generated yet'}
          </p>
        </div>

        {reportText && (
          <button
            onClick={handleDownload}
            className="flex items-center gap-2 rounded-lg border border-neutral-800 bg-neutral-800/80 px-3.5 py-1.5 text-xs font-semibold text-neutral-200 transition-colors hover:bg-neutral-700 hover:text-white"
          >
            <Download className="h-4 w-4 text-indigo-400" />
            <span>Download Report (.md)</span>
          </button>
        )}
      </div>

      {reportText ? (
        <div className="mt-6 prose prose-invert max-w-none prose-headings:font-bold prose-headings:text-indigo-400 prose-headings:mt-6 prose-headings:mb-2 prose-h3:text-sm prose-h3:uppercase prose-h3:tracking-wider prose-h3:border-b prose-h3:border-neutral-800/80 prose-h3:pb-1.5 prose-p:text-neutral-300 prose-p:text-xs prose-p:leading-relaxed prose-li:text-neutral-300 prose-li:text-xs prose-strong:text-white">
          <ReactMarkdown>{reportText}</ReactMarkdown>
        </div>
      ) : (
        <div className="py-12 text-center text-xs text-neutral-500">
          No narrative reports generated for this topic yet. Click "Run Pipeline" to generate one.
        </div>
      )}
    </div>
  );
};
