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
    <div className="rounded-lg border-2 border-black bg-white p-6 shadow-neo">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b-2 border-black pb-4">
        <div>
          <h2 className="text-lg font-black text-black flex items-center gap-2 uppercase tracking-wide">
            <span className="flex h-7 w-7 items-center justify-center rounded-md border-2 border-black bg-black text-white shadow-neo-sm">
              <Sparkles className="h-4 w-4 fill-white" />
            </span>
            Executive Summary / AI Narrative
          </h2>
          <p className="text-xs font-semibold text-neutral-600 mt-1">
            {narrative ? getCaption() : 'No narrative report generated yet'}
          </p>
        </div>

        {reportText && (
          <button
            onClick={handleDownload}
            className="neo-btn flex items-center gap-2 rounded-lg bg-black px-4 py-2 text-xs font-black text-white hover:bg-neutral-800"
          >
            <Download className="h-4 w-4 stroke-[2.5]" />
            <span>Download Report (.md)</span>
          </button>
        )}
      </div>

      {reportText ? (
        <div className="mt-6 prose max-w-none prose-headings:font-black prose-headings:text-black prose-headings:mt-5 prose-headings:mb-2 prose-h3:text-sm prose-h3:uppercase prose-h3:tracking-wider prose-h3:border-b-2 prose-h3:border-black prose-h3:pb-1 prose-p:text-neutral-800 prose-p:text-xs prose-p:leading-relaxed prose-li:text-neutral-800 prose-li:text-xs prose-strong:font-black prose-strong:text-black bg-neutral-50 p-5 rounded-lg border-2 border-black">
          <ReactMarkdown>{reportText}</ReactMarkdown>
        </div>
      ) : (
        <div className="py-10 text-center text-xs font-bold text-neutral-500">
          No narrative reports generated for this topic yet. Click "Run Pipeline" to generate one.
        </div>
      )}
    </div>
  );
};
