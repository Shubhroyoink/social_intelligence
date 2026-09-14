import React, { useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  Sparkles,
  Download,
  BarChart3,
  BrainCircuit,
  TrendingUp,
  Users,
  Share2,
  CheckCircle2,
  Lightbulb,
  Clock,
  Cpu,
  Copy,
  Check,
  Tag,
  ShieldCheck,
} from 'lucide-react';
import type { Narrative } from '../types';

interface NarrativeViewProps {
  narrative: Narrative | null;
  narratives: Narrative[];
}

interface NarrativeSection {
  title: string;
  content: string;
  iconType: 'summary' | 'sentiment' | 'emotions' | 'trends' | 'demographics' | 'network' | 'bottomline' | 'general';
}

function parseNarrativeSections(text: string): NarrativeSection[] {
  if (!text) return [];

  const knownHeaders = [
    { pattern: /^(?:#{1,3}\s*)?(?:Executive Summary|Overview|Core Summary)/i, title: 'Executive Summary', icon: 'summary' as const },
    { pattern: /^(?:#{1,3}\s*)?(?:Sentiment Analysis|Sentiment)/i, title: 'Sentiment & Platform Dynamics', icon: 'sentiment' as const },
    { pattern: /^(?:#{1,3}\s*)?(?:Emotion & Stance|Emotions & Stance|Emotion Analysis|Emotions)/i, title: 'Emotion & Stance Landscape', icon: 'emotions' as const },
    { pattern: /^(?:#{1,3}\s*)?(?:Trends|Trending Keywords|Trend Analysis|Keyword Trends)/i, title: 'Trending Terms & Discourse', icon: 'trends' as const },
    { pattern: /^(?:#{1,3}\s*)?(?:Demographics|Audience Demographics|Language & Geography)/i, title: 'Demographics & Audience Profile', icon: 'demographics' as const },
    { pattern: /^(?:#{1,3}\s*)?(?:Network & Influence|Key Influencers|Network Analysis)/i, title: 'Network & Key Opinion Leaders', icon: 'network' as const },
    { pattern: /^(?:#{1,3}\s*)?(?:Bottom Line|Strategic Outlook|Key Takeaways|Conclusion)/i, title: 'Strategic Bottom Line', icon: 'bottomline' as const },
  ];

  const lines = text.split('\n');
  const sections: NarrativeSection[] = [];
  let currentTitle = 'Executive Summary';
  let currentIcon: any = 'summary';
  let currentContentLines: string[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    // Check if line matches one of our known headers
    const matchedHeader = knownHeaders.find((h) => h.pattern.test(trimmed) && trimmed.length < 50);

    if (matchedHeader) {
      if (currentContentLines.length > 0) {
        sections.push({
          title: currentTitle,
          content: currentContentLines.join('\n').trim(),
          iconType: currentIcon,
        });
      }
      currentTitle = matchedHeader.title;
      currentIcon = matchedHeader.icon;
      currentContentLines = [];
    } else {
      currentContentLines.push(line);
    }
  }

  if (currentContentLines.length > 0) {
    sections.push({
      title: currentTitle,
      content: currentContentLines.join('\n').trim(),
      iconType: currentIcon,
    });
  }

  if (sections.length === 0 && text.trim()) {
    sections.push({
      title: 'Executive Summary',
      content: text.trim(),
      iconType: 'summary',
    });
  }

  return sections;
}

export const NarrativeView: React.FC<NarrativeViewProps> = ({ narrative }) => {
  const [copiedFull, setCopiedFull] = useState(false);
  const [copiedSectionIndex, setCopiedSectionIndex] = useState<number | null>(null);

  const reportText = narrative?.report_markdown || narrative?.report_text || '';

  const handleDownload = () => {
    if (!narrative) return;
    const blob = new Blob([reportText], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `report_${narrative.topic_query || 'general'}_${(narrative.created_at || '').slice(0, 10)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleCopyFull = async () => {
    if (!reportText) return;
    try {
      await navigator.clipboard.writeText(reportText);
      setCopiedFull(true);
      setTimeout(() => setCopiedFull(false), 2000);
    } catch {
      // fallback if clipboard api fails
    }
  };

  const handleCopySection = async (index: number, content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedSectionIndex(index);
      setTimeout(() => setCopiedSectionIndex(null), 2000);
    } catch {
      // fallback
    }
  };

  const parsedSections = useMemo(() => {
    return parseNarrativeSections(reportText);
  }, [reportText]);

  const summarySection = parsedSections.find((s) => s.iconType === 'summary');
  const otherSections = parsedSections.filter((s) => s.iconType !== 'summary');

  const getSectionIcon = (iconType: string) => {
    switch (iconType) {
      case 'sentiment':
        return <BarChart3 className="h-4 w-4 stroke-[2.5]" />;
      case 'emotions':
        return <BrainCircuit className="h-4 w-4 stroke-[2.5]" />;
      case 'trends':
        return <TrendingUp className="h-4 w-4 stroke-[2.5]" />;
      case 'demographics':
        return <Users className="h-4 w-4 stroke-[2.5]" />;
      case 'network':
        return <Share2 className="h-4 w-4 stroke-[2.5]" />;
      case 'bottomline':
        return <Lightbulb className="h-4 w-4 stroke-[2.5]" />;
      default:
        return <CheckCircle2 className="h-4 w-4 stroke-[2.5]" />;
    }
  };

  const dateFormatted = (narrative?.created_at || '').slice(0, 19).replace('T', ' · ');

  return (
    <div className="rounded-lg border-2 border-black bg-white p-6 shadow-neo space-y-6">
      {/* Section Header */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between border-b-2 border-black pb-5">
        <div className="space-y-2">
          {/* Header Title + Badges */}
          <div className="flex flex-wrap items-center gap-2.5">
            <div className="flex items-center gap-2.5">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg border-2 border-black bg-black text-white shadow-neo-sm">
                <Sparkles className="h-4 w-4 fill-white" />
              </span>
              <h2 className="text-lg font-black text-black uppercase tracking-wide">
                Executive Summary & Intelligence Brief
              </h2>
            </div>
            <span className="rounded-md border-2 border-black bg-black px-2.5 py-0.5 text-[10px] font-black text-white uppercase tracking-wider shadow-neo-sm">
              AI Synthesis
            </span>
          </div>

          {/* Header Metadata Chips (Left Section) */}
          {narrative ? (
            <div className="flex flex-wrap items-center gap-2 pt-1 text-xs">
              {/* Topic Pill */}
              <div className="inline-flex items-center gap-1.5 rounded-md border border-black bg-neutral-100 px-2.5 py-1 font-bold text-black shadow-neo-sm">
                <Tag className="h-3 w-3 stroke-[2.5]" />
                <span className="text-[11px] uppercase tracking-wide">Topic: {narrative.topic_query || 'General'}</span>
              </div>

              {/* Model Pill */}
              <div className="inline-flex items-center gap-1.5 rounded-md border border-black bg-neutral-100 px-2.5 py-1 font-bold text-black shadow-neo-sm">
                <Cpu className="h-3 w-3 stroke-[2.5]" />
                <span className="text-[11px]">
                  {narrative.backend === 'gemini' ? (narrative.model || 'Gemini 3.5 Flash') : 'Template Engine'}
                </span>
              </div>

              {/* Timestamp Pill */}
              <div className="inline-flex items-center gap-1.5 rounded-md border border-black bg-white px-2.5 py-1 font-semibold text-neutral-700 shadow-neo-sm">
                <Clock className="h-3 w-3 text-neutral-600 stroke-[2.5]" />
                <span className="text-[11px]">{dateFormatted} UTC</span>
              </div>

              {/* Verified Badge */}
              <div className="inline-flex items-center gap-1 rounded-md border border-black bg-neutral-50 px-2 py-1 font-bold text-black text-[10px] uppercase shadow-neo-sm">
                <ShieldCheck className="h-3 w-3 text-black stroke-[2.5]" />
                <span>Verified Synthesis</span>
              </div>
            </div>
          ) : (
            <p className="text-xs font-semibold text-neutral-500">
              No narrative report generated yet. Run pipeline to synthesize intelligence.
            </p>
          )}
        </div>

        {/* Action Controls */}
        {reportText && (
          <div className="flex flex-wrap items-center gap-2.5 self-start lg:self-center">
            {/* Copy Full Report Button */}
            <button
              onClick={handleCopyFull}
              className="neo-btn flex items-center gap-1.5 rounded-lg border-2 border-black bg-white px-3.5 py-1.5 text-xs font-black text-black hover:bg-neutral-100"
              title="Copy entire executive summary to clipboard"
            >
              {copiedFull ? (
                <>
                  <Check className="h-3.5 w-3.5 text-black stroke-[3]" />
                  <span>Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="h-3.5 w-3.5 stroke-[2.5]" />
                  <span>Copy Report</span>
                </>
              )}
            </button>

            {/* Download Button */}
            <button
              onClick={handleDownload}
              className="neo-btn flex items-center gap-1.5 rounded-lg bg-black px-4 py-1.5 text-xs font-black text-white hover:bg-neutral-800"
            >
              <Download className="h-3.5 w-3.5 stroke-[2.5]" />
              <span>Export (.md)</span>
            </button>
          </div>
        )}
      </div>

      {/* Content Rendering */}
      {reportText ? (
        <div className="space-y-5">
          {/* 1. Hero Executive Summary Card */}
          {summarySection && (
            <div className="rounded-xl border-2 border-black bg-neutral-50 p-5 shadow-neo border-l-[8px] border-l-black space-y-3 transition-all hover:bg-white">
              <div className="flex items-center justify-between border-b border-black/20 pb-2.5">
                <div className="flex items-center gap-2">
                  <span className="flex h-6 w-6 items-center justify-center rounded border-2 border-black bg-black text-white shadow-neo-sm">
                    <Sparkles className="h-3.5 w-3.5 fill-white" />
                  </span>
                  <h3 className="text-xs font-black uppercase tracking-wider text-black">
                    Core Executive Takeaway
                  </h3>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleCopySection(-1, summarySection.content)}
                    className="flex items-center gap-1 rounded border border-black bg-white px-2 py-0.5 text-[10px] font-black text-black uppercase shadow-neo-sm hover:bg-neutral-100"
                  >
                    {copiedSectionIndex === -1 ? <Check className="h-3 w-3 stroke-[3]" /> : <Copy className="h-3 w-3" />}
                    <span>{copiedSectionIndex === -1 ? 'Copied' : 'Copy'}</span>
                  </button>
                  <span className="rounded border-2 border-black bg-black px-2 py-0.5 text-[10px] font-black text-white uppercase shadow-neo-sm">
                    Overview
                  </span>
                </div>
              </div>
              <div className="prose max-w-none text-xs font-semibold leading-relaxed text-black pt-1 prose-strong:font-black prose-strong:text-black">
                <ReactMarkdown>{summarySection.content}</ReactMarkdown>
              </div>
            </div>
          )}

          {/* 2. Structured Cards Grid (Bottom Section) */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {otherSections.map((sec, idx) => (
              <div
                key={idx}
                className="group flex flex-col justify-between rounded-xl border-2 border-black bg-white p-4 shadow-neo transition-all hover:-translate-y-0.5 hover:shadow-neo-lg"
              >
                <div className="space-y-3">
                  {/* Card Header */}
                  <div className="flex items-center justify-between border-b-2 border-black pb-2.5">
                    <div className="flex items-center gap-2">
                      <span className="flex h-7 w-7 items-center justify-center rounded-lg border-2 border-black bg-neutral-100 text-black shadow-neo-sm group-hover:bg-black group-hover:text-white transition-colors">
                        {getSectionIcon(sec.iconType)}
                      </span>
                      <h4 className="text-xs font-black uppercase tracking-wider text-black">
                        {sec.title}
                      </h4>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={() => handleCopySection(idx, sec.content)}
                        className="rounded border border-black bg-neutral-50 px-1.5 py-0.5 text-[9px] font-bold text-black uppercase shadow-neo-sm hover:bg-black hover:text-white transition-colors"
                        title="Copy section"
                      >
                        {copiedSectionIndex === idx ? <Check className="h-3 w-3 stroke-[3]" /> : <Copy className="h-3 w-3" />}
                      </button>
                      <span className="rounded bg-neutral-100 border border-black px-1.5 py-0.5 text-[9px] font-black text-neutral-800 uppercase">
                        #{idx + 1}
                      </span>
                    </div>
                  </div>

                  {/* Card Body Markdown */}
                  <div className="prose max-w-none text-xs font-semibold text-neutral-800 leading-relaxed prose-p:my-1.5 prose-strong:font-black prose-strong:text-black prose-ul:my-1.5 prose-li:my-0.5">
                    <ReactMarkdown
                      components={{
                        strong: ({ children }) => (
                          <strong className="font-black text-black bg-neutral-100 px-1 py-0.5 rounded border border-neutral-300 mr-1 inline-block">
                            {children}
                          </strong>
                        ),
                        li: ({ children }) => (
                          <li className="flex items-start gap-1.5">
                            <span className="mt-1 h-1.5 w-1.5 flex-shrink-0 rounded-none bg-black"></span>
                            <span>{children}</span>
                          </li>
                        ),
                      }}
                    >
                      {sec.content}
                    </ReactMarkdown>
                  </div>
                </div>

                {/* Card Footer Micro-tag */}
                <div className="mt-4 pt-2.5 border-t border-neutral-200 flex items-center justify-between text-[10px] font-bold text-neutral-600">
                  <span className="flex items-center gap-1 uppercase tracking-wider">
                    <CheckCircle2 className="h-3 w-3 text-black stroke-[2.5]" />
                    <span>Analyzed & Synthesized</span>
                  </span>
                  <span className="uppercase text-[9px] font-black text-black">
                    Section {idx + 1} of {otherSections.length}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="rounded-xl border-2 border-dashed border-black bg-neutral-50 py-12 text-center">
          <Sparkles className="mx-auto h-8 w-8 text-neutral-400 mb-2" />
          <p className="text-xs font-black text-black uppercase">No narrative report generated yet</p>
          <p className="text-xs font-semibold text-neutral-600 mt-1">
            Click "Run Pipeline" to generate an executive intelligence report for this topic.
          </p>
        </div>
      )}
    </div>
  );
};
