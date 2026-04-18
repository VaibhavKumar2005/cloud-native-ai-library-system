import React, { useState, useEffect } from 'react';
import { TrendingUp, Loader, AlertCircle } from 'lucide-react';

/**
 * ResearchGapAnalyzer - Analyze papers for research gaps
 * Uses RAG to identify unexplored areas and trending topics
 */
export default function ResearchGapAnalyzer() {
  const [topic, setTopic] = useState('prompt engineering in large language models');
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleAnalyze = async (e) => {
    e.preventDefault();
    if (!topic.trim()) return;

    setLoading(true);
    setError('');
    setAnalysis(null);

    try {
      const response = await fetch('/api/papers/analyze-gaps/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({ topic })
      });

      if (!response.ok) throw new Error('Analysis failed');
      const data = await response.json();
      setAnalysis(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Analysis Form */}
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Research Gap Analyzer</h2>
        <p className="text-slate-400 text-sm mb-4">
          Analyze your research area to identify gaps, emerging trends, and collaboration opportunities.
        </p>

        <form onSubmit={handleAnalyze} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">Research Topic</label>
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g., 'multi-agent reinforcement learning'"
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-blue-500"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 text-white rounded-lg font-medium transition flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader className="animate-spin" size={18} />
                Analyzing...
              </>
            ) : (
              <>
                <TrendingUp size={18} />
                Analyze Research Gaps
              </>
            )}
          </button>
        </form>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 flex gap-3">
          <AlertCircle className="text-red-400 flex-shrink-0" size={20} />
          <p className="text-red-200">{error}</p>
        </div>
      )}

      {/* Analysis Results */}
      {analysis && (
        <div className="space-y-4">
          {/* Key Gaps */}
          {analysis.gaps && analysis.gaps.length > 0 && (
            <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <span className="w-2 h-2 bg-red-500 rounded-full"></span>
                Identified Research Gaps
              </h3>
              <div className="space-y-3">
                {analysis.gaps.map((gap, idx) => (
                  <div key={idx} className="pl-4 border-l-2 border-red-500">
                    <h4 className="font-medium text-white">{gap.title}</h4>
                    <p className="text-sm text-slate-300 mt-1">{gap.description}</p>
                    {gap.potential_research_directions && (
                      <div className="mt-2 text-sm text-slate-400">
                        <p className="font-medium text-slate-300">Potential directions:</p>
                        <ul className="list-disc list-inside mt-1 space-y-1">
                          {gap.potential_research_directions.map((dir, i) => (
                            <li key={i}>{dir}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Emerging Trends */}
          {analysis.trends && analysis.trends.length > 0 && (
            <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <span className="w-2 h-2 bg-yellow-500 rounded-full"></span>
                Emerging Trends (Last 12 Months)
              </h3>
              <div className="space-y-3">
                {analysis.trends.map((trend, idx) => (
                  <div key={idx} className="p-3 bg-slate-700 rounded-lg">
                    <div className="flex items-center justify-between">
                      <h4 className="font-medium text-white">{trend.name}</h4>
                      <span className="text-sm font-semibold text-yellow-400">
                        ↑ {trend.growth_percentage}%
                      </span>
                    </div>
                    <p className="text-sm text-slate-300 mt-1">{trend.description}</p>
                    <p className="text-xs text-slate-400 mt-2">
                      {trend.paper_count} papers · {trend.avg_citations} avg citations
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Collaboration Opportunities */}
          {analysis.collaboration_opportunities && analysis.collaboration_opportunities.length > 0 && (
            <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                Collaboration Opportunities
              </h3>
              <div className="space-y-3">
                {analysis.collaboration_opportunities.map((collab, idx) => (
                  <div key={idx} className="p-3 bg-slate-700 rounded-lg">
                    <h4 className="font-medium text-white">{collab.topic}</h4>
                    <p className="text-sm text-slate-300 mt-1">{collab.description}</p>
                    {collab.related_fields && (
                      <div className="flex flex-wrap gap-2 mt-2">
                        {collab.related_fields.map((field, i) => (
                          <span key={i} className="px-2 py-1 bg-slate-600 text-slate-300 text-xs rounded">
                            {field}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {!loading && !analysis && !error && (
        <div className="text-center py-12 text-slate-400">
          <p className="text-sm">Run the analysis to discover research gaps in your field</p>
        </div>
      )}
    </div>
  );
}
