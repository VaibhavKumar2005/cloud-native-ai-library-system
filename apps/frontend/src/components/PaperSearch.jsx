import React, { useState } from 'react';
import { Search, ExternalLink, BookmarkPlus, Copy, AlertCircle } from 'lucide-react';

/**
 * PaperSearch - Search academic papers from multiple sources
 * 
 * Supported sources:
 * - Semantic Scholar
 * - arXiv
 * - CrossRef
 */
export default function PaperSearch() {
  const [query, setQuery] = useState('');
  const [source, setSource] = useState('semantic-scholar');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedPapers, setSelectedPapers] = useState(new Set());

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError('');
    setResults([]);

    try {
      const response = await fetch('/api/papers/search/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({ query, source })
      });

      if (!response.ok) throw new Error('Search failed');
      const data = await response.json();
      setResults(data.papers || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAddToLibrary = async () => {
    if (selectedPapers.size === 0) return;

    try {
      const response = await fetch('/api/papers/ingest/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({
          paper_ids: Array.from(selectedPapers),
          source
        })
      });

      if (!response.ok) throw new Error('Failed to add papers');
      alert(`${selectedPapers.size} papers added to your library!`);
      setSelectedPapers(new Set());
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="space-y-6">
      {/* Search Form */}
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Search Academic Papers</h2>
        
        <form onSubmit={handleSearch} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <input
              type="text"
              placeholder="e.g., 'prompt engineering in LLMs'"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="col-span-1 md:col-span-3 px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-blue-500"
            />
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 text-white rounded-lg font-medium transition flex items-center justify-center gap-2"
            >
              <Search size={18} />
              {loading ? 'Searching...' : 'Search'}
            </button>
          </div>

          <div className="flex items-center gap-4">
            <label className="text-slate-300 text-sm font-medium">Source:</label>
            <div className="flex gap-3">
              {['semantic-scholar', 'arxiv', 'crossref'].map(src => (
                <label key={src} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="source"
                    value={src}
                    checked={source === src}
                    onChange={(e) => setSource(e.target.value)}
                    className="w-4 h-4 accent-blue-500"
                  />
                  <span className="text-sm text-slate-300 capitalize">{src.replace('-', ' ')}</span>
                </label>
              ))}
            </div>
          </div>
        </form>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 flex gap-3">
          <AlertCircle className="text-red-400 flex-shrink-0" size={20} />
          <p className="text-red-200">{error}</p>
        </div>
      )}

      {/* Results */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-white">
            Results {results.length > 0 && `(${results.length})`}
          </h3>
          {selectedPapers.size > 0 && (
            <button
              onClick={handleAddToLibrary}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition flex items-center gap-2"
            >
              <BookmarkPlus size={18} />
              Add {selectedPapers.size} to Library
            </button>
          )}
        </div>

        {results.map((paper) => (
          <div key={paper.id} className="bg-slate-800 border border-slate-700 rounded-lg p-4 hover:border-slate-600 transition">
            <div className="flex gap-4">
              <input
                type="checkbox"
                checked={selectedPapers.has(paper.id)}
                onChange={(e) => {
                  const newSet = new Set(selectedPapers);
                  if (e.target.checked) newSet.add(paper.id);
                  else newSet.delete(paper.id);
                  setSelectedPapers(newSet);
                }}
                className="w-5 h-5 accent-blue-500 rounded mt-1 flex-shrink-0"
              />
              
              <div className="flex-1 min-w-0">
                <h4 className="text-white font-semibold hover:text-blue-400 truncate">
                  <a href={paper.url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2">
                    {paper.title}
                    <ExternalLink size={16} />
                  </a>
                </h4>
                
                <p className="text-sm text-slate-400 mt-1">
                  {paper.authors?.join(', ') || 'Unknown authors'}
                </p>
                
                {paper.abstract && (
                  <p className="text-sm text-slate-300 mt-2 line-clamp-2">
                    {paper.abstract}
                  </p>
                )}
                
                <div className="flex flex-wrap gap-2 mt-3">
                  {paper.year && (
                    <span className="px-2 py-1 bg-slate-700 text-slate-300 text-xs rounded">
                      {paper.year}
                    </span>
                  )}
                  {paper.citations && (
                    <span className="px-2 py-1 bg-slate-700 text-slate-300 text-xs rounded">
                      {paper.citations} citations
                    </span>
                  )}
                  {paper.venue && (
                    <span className="px-2 py-1 bg-slate-700 text-slate-300 text-xs rounded">
                      {paper.venue}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        ))}

        {!loading && results.length === 0 && query && (
          <div className="text-center py-8 text-slate-400">
            <p>No papers found. Try a different search query.</p>
          </div>
        )}
      </div>
    </div>
  );
}
