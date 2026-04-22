import React, { useState, useEffect } from 'react';
import { Trash2, MessageSquare, Download, Filter, Search } from 'lucide-react';

/**
 * ResearchLibrary - Display and manage user's research paper library
 */
export default function ResearchLibrary() {
  const [papers, setPapers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filter, setFilter] = useState('all'); // all, favorites, recent
  const [selectedPaper, setSelectedPaper] = useState(null);
  const [qnaQuery, setQnaQuery] = useState('');
  const [qnaResponse, setQnaResponse] = useState('');

  useEffect(() => {
    const fetchLibrary = async () => {
      setLoading(true);
      try {
        const response = await fetch(`/api/papers/library/?filter=${filter}`, {
          headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
        });
        if (!response.ok) throw new Error('Failed to fetch library');
        const data = await response.json();
        setPapers(data.papers || []);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchLibrary();
  }, [filter]);

  const handleDelete = async (paperId) => {
    try {
      const response = await fetch(`/api/papers/${paperId}/`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
      });
      if (!response.ok) throw new Error('Failed to delete');
      setPapers(papers.filter(p => p.id !== paperId));
    } catch (err) {
      console.error(err);
    }
  };

  const handleAskQuestion = async (paperId) => {
    if (!qnaQuery.trim()) return;

    try {
      const response = await fetch(`/api/papers/${paperId}/ask/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({ question: qnaQuery })
      });

      if (!response.ok) throw new Error('Failed to get response');
      const data = await response.json();
      setQnaResponse(data.answer);
    } catch (err) {
      console.error(err);
    }
  };

  const filteredPapers = papers.filter(p =>
    p.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    p.authors?.some(a => a.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Papers List */}
      <div className="lg:col-span-2 space-y-4">
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
          <div className="flex gap-3 mb-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-3 text-slate-500" size={18} />
              <input
                type="text"
                placeholder="Search papers..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-blue-500"
              />
            </div>
            <div className="flex gap-2">
              {['all', 'favorites', 'recent'].map(f => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition ${
                    filter === f
                      ? 'bg-blue-600 text-white'
                      : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                  }`}
                >
                  {f.charAt(0).toUpperCase() + f.slice(1)}
                </button>
              ))}
            </div>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-8 text-slate-400">Loading...</div>
        ) : filteredPapers.length === 0 ? (
          <div className="text-center py-8 text-slate-400">No papers found</div>
        ) : (
          <div className="space-y-3">
            {filteredPapers.map(paper => (
              <div
                key={paper.id}
                onClick={() => setSelectedPaper(paper.id === selectedPaper ? null : paper.id)}
                className={`cursor-pointer p-4 rounded-lg border transition ${
                  selectedPaper === paper.id
                    ? 'bg-slate-700 border-blue-500'
                    : 'bg-slate-800 border-slate-700 hover:border-slate-600'
                }`}
              >
                <h4 className="font-semibold text-white text-sm">{paper.title}</h4>
                <p className="text-xs text-slate-500 mt-1">{paper.authors?.join(', ') || 'Unknown'}</p>
                <div className="flex gap-2 mt-3">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(paper.id);
                    }}
                    className="px-3 py-1 bg-red-900/30 text-red-400 text-xs rounded hover:bg-red-900/50 transition flex items-center gap-1"
                  >
                    <Trash2 size={14} /> Remove
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* QnA Panel */}
      {selectedPaper && (
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4 h-fit sticky top-20">
          <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
            <MessageSquare size={18} />
            Ask About Paper
          </h3>

          <div className="space-y-3">
            <input
              type="text"
              placeholder="Ask a question..."
              value={qnaQuery}
              onChange={(e) => setQnaQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleAskQuestion(selectedPaper)}
              className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-blue-500 text-sm"
            />

            <button
              onClick={() => handleAskQuestion(selectedPaper)}
              className="w-full px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition"
            >
              Ask
            </button>

            {qnaResponse && (
              <div className="bg-slate-700 rounded-lg p-3 max-h-64 overflow-y-auto">
                <p className="text-sm text-slate-200">{qnaResponse}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
