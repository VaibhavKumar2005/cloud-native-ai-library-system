import React from 'react'
import { Button } from '@/components/ui/button'
import { CheckCircle, AlertCircle, FileText } from 'lucide-react'

/**
 * ResearchGradeAnswer
 * 
 * Displays RAG response in academic format.
 * Focus: Citations, confidence, source attribution.
 * 
 * Props:
 *   answer: string - The synthesized answer
 *   citations: Array - [{ source, page, excerpt }]
 *   confidence: number - 0.0 to 1.0
 *   method: 'direct' | 'synthesis' | 'rejected'
 */
export default function ResearchGradeAnswer({
  answer,
  citations = [],
  confidence = 0,
  method,
  onViewPDF = () => { }
}) {
  if (method === 'rejected') {
    return (
      <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-6">
        <div className="flex gap-3 items-start">
          <AlertCircle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="font-semibold text-amber-200 mb-1">No reliable evidence found</h4>
            <p className="text-sm text-slate-400">
              This question is outside your document set. Try uploading papers on this topic,
              or refine your question to match what's in your library.
            </p>
          </div>
        </div>
      </div>
    )
  }

  const confidentHigh = confidence >= 0.80
  const confidentMid = confidence >= 0.65

  return (
    <div className="space-y-6">
      {/* ─── ANSWER SECTION ─── */}
      <div>
        <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-3">
          Answer
        </h3>
        <div className="prose prose-invert max-w-none text-slate-200 text-sm leading-relaxed">
          <p>{answer}</p>
        </div>
      </div>

      {/* ─── EVIDENCE SOURCES ─── */}
      {citations.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-3">
            Evidence Sources ({citations.length})
          </h3>
          <div className="space-y-3">
            {citations.map((cite, i) => (
              <div
                key={i}
                className="rounded-lg border border-slate-700 bg-slate-800/40 p-4 hover:border-slate-600 transition"
              >
                <div className="flex gap-3 items-start">
                  <FileText className="w-4 h-4 text-cyan-400 flex-shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-sm text-slate-100 truncate">
                      {cite.source}
                    </p>
                    <p className="text-xs text-slate-400 mt-1">Page {cite.page}</p>
                    <p className="text-xs text-slate-300 mt-2 italic">
                      "{cite.excerpt}..."
                    </p>
                  </div>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  className="mt-3 h-7 text-xs text-cyan-400 hover:text-cyan-300"
                  onClick={() => onViewPDF(cite)}
                >
                  View in PDF
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ─── CONFIDENCE METER ─── */}
      <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-4">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-xs font-semibold uppercase tracking-widest text-slate-400">
            Confidence
          </h4>
          <span className={`text-sm font-semibold ${confidentHigh ? 'text-emerald-400' : confidentMid ? 'text-amber-400' : 'text-red-400'}`}>
            {(confidence * 100).toFixed(0)}%
          </span>
        </div>

        {/* Bar */}
        <div className="w-full h-1.5 rounded-full bg-slate-700 overflow-hidden">
          <div
            className={`h-full transition-all ${confidentHigh ? 'bg-emerald-500' : confidentMid ? 'bg-amber-500' : 'bg-red-500'}`}
            style={{ width: `${Math.min(confidence * 100, 100)}%` }}
          />
        </div>

        {/* Explanation */}
        <p className="mt-3 text-xs text-slate-400">
          {method === 'direct'
            ? 'Direct match from your documents. High confidence.'
            : method === 'synthesis'
              ? 'Synthesized from multiple sources. Answer grounded in your library.'
              : 'Unable to provide confident answer from your documents.'}
        </p>
      </div>
    </div>
  )
}
