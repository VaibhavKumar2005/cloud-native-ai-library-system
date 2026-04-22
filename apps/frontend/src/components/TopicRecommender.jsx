import React, { useState } from 'react';
import { Lightbulb, Loader, AlertCircle } from 'lucide-react';

/**
 * TopicRecommender - AI-powered topic recommendations for PhD students
 * Tailored for AI Engineering research
 */
export default function TopicRecommender() {
  const [interests, setInterests] = useState('machine learning, natural language processing');
  const [recommendations, setRecommendations] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleGetRecommendations = async (e) => {
    e.preventDefault();
    if (!interests.trim()) return;

    setLoading(true);
    setError('');
    setRecommendations(null);

    try {
      const response = await fetch('/api/papers/recommend-topics/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({ 
          interests: interests.split(',').map(i => i.trim()),
          field: 'ai-engineering'
        })
      });

      if (!response.ok) throw new Error('Failed to get recommendations');
      const data = await response.json();
      setRecommendations(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Input Form */}
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-white mb-2">AI Engineering Topic Explorer</h2>
        <p className="text-slate-400 text-sm mb-4">
          Get personalized PhD research topic recommendations based on your interests.
        </p>

        <form onSubmit={handleGetRecommendations} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">Your Interests</label>
            <input
              type="text"
              value={interests}
              onChange={(e) => setInterests(e.target.value)}
              placeholder="e.g., prompt engineering, multi-agent systems, retrieval-augmented generation"
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-blue-500"
            />
            <p className="text-xs text-slate-400 mt-2">Separate interests with commas</p>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 text-white rounded-lg font-medium transition flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader className="animate-spin" size={18} />
                Generating...
              </>
            ) : (
              <>
                <Lightbulb size={18} />
                Get Topic Recommendations
              </>
            )}
          </button>
        </form>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 flex gap-3">
          <AlertCircle className="text-red-400 flex-shrink-0" size={20} />
          <p className="text-red-200">{error}</p>
        </div>
      )}

      {/* Recommendations */}
      {recommendations && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {recommendations.topics?.map((topic, idx) => (
              <div key={idx} className="bg-slate-800 border border-slate-700 rounded-lg p-5 hover:border-slate-600 transition">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center flex-shrink-0">
                    <span className="text-white font-bold text-sm">{idx + 1}</span>
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-white">{topic.title}</h3>
                    <p className="text-sm text-slate-300 mt-2">{topic.description}</p>
                    
                    <div className="mt-3 space-y-2">
                      <div>
                        <p className="text-xs font-semibold text-slate-400 mb-1">Why this topic:</p>
                        <p className="text-sm text-slate-300">{topic.relevance_reason}</p>
                      </div>
                      
                      <div>
                        <p className="text-xs font-semibold text-slate-400 mb-1">Key challenges:</p>
                        <ul className="text-sm text-slate-300 space-y-1">
                          {topic.key_challenges?.map((challenge, i) => (
                            <li key={i} className="flex gap-2">
                              <span className="text-slate-500">•</span>
                              <span>{challenge}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>

                    <div className="mt-4 flex flex-wrap gap-2">
                      {topic.skills_needed?.slice(0, 3).map((skill, i) => (
                        <span key={i} className="px-2 py-1 bg-slate-700 text-slate-300 text-xs rounded">
                          {skill}
                        </span>
                      ))}
                      {topic.skills_needed?.length > 3 && (
                        <span className="px-2 py-1 bg-slate-700 text-slate-300 text-xs rounded">
                          +{topic.skills_needed.length - 3} more
                        </span>
                      )}
                    </div>

                    <div className="mt-4 pt-4 border-t border-slate-700">
                      <p className="text-sm text-slate-400">
                        <span className="font-semibold">{topic.relevance_score}%</span> match with your interests
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* AI Field Insights */}
          {recommendations.field_insights && (
            <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-white mb-4">AI Engineering Landscape</h3>
              <div className="space-y-3 text-slate-300 text-sm">
                <p>{recommendations.field_insights.overview}</p>
                <div className="mt-4">
                  <p className="font-semibold text-white mb-2">Hot trends:</p>
                  <div className="flex flex-wrap gap-2">
                    {recommendations.field_insights.trends?.map((trend, i) => (
                      <span key={i} className="px-3 py-1 bg-blue-900/30 border border-blue-700 text-blue-300 text-xs rounded-full">
                        {trend}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {!loading && !recommendations && !error && (
        <div className="text-center py-12 text-slate-400">
          <p className="text-sm">Enter your interests to get personalized topic recommendations</p>
        </div>
      )}
    </div>
  );
}
