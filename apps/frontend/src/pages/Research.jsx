import React, { useState, useCallback, useEffect } from 'react';
import { searchAcademicPapers, queryAcademicRAG } from '../api/research';
import PaperCard from '../components/PaperCard';
import AnswerPanel from '../components/AnswerPanel';
import SessionBar from '../components/SessionBar';
import '../styles/Research.css';
import '../styles/Components.css';

export default function Research() {
  const [query, setQuery] = useState('');
  const [scope, setScope] = useState('both'); // 'local' | 'all' | 'both'
  const [results, setResults] = useState([]);
  const [pinned, setPinned] = useState([]);
  const [answer, setAnswer] = useState(null);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({ topic: '', year: null });
  const [hasSearched, setHasSearched] = useState(false);

  // Search papers (academic + local)
  const handleSearch = useCallback(async (e) => {
    if (e.key !== 'Enter' || !query.trim()) return;
    
    setLoading(true);
    setHasSearched(true);
    try {
      let papers = [];
      
      if (scope === 'local' || scope === 'both') {
        try {
          const local = await fetch(`http://localhost:8000/api/documents/search/?q=${encodeURIComponent(query)}`).then(r => r.json());
          papers.push(...local.map(p => ({ ...p, source: 'local' })));
        } catch (e) {
          console.warn('Local search failed:', e);
        }
      }
      
      if (scope === 'all' || scope === 'both') {
        try {
          const external = await searchAcademicPapers(query);
          papers.push(...external.map(p => ({ ...p, source: 'external' })));
        } catch (e) {
          console.warn('External search failed:', e);
        }
      }
      
      // Apply filters
      papers = papers.filter(p => {
        if (filters.year && p.year !== filters.year) return false;
        if (filters.topic && !p.abstract?.toLowerCase().includes(filters.topic)) return false;
        return true;
      });
      
      setResults(papers);
      setAnswer(null); // Clear answer on new search
    } finally {
      setLoading(false);
    }
  }, [query, scope, filters]);

  // Ask about pinned papers
  const handleAsk = useCallback(async () => {
    if (!query.trim() || pinned.length === 0) return;
    
    setLoading(true);
    try {
      const response = await queryAcademicRAG(query, pinned.map(p => p.id));
      setAnswer(response);
    } finally {
      setLoading(false);
    }
  }, [query, pinned]);

  const togglePin = (paper) => {
    setPinned(prev =>
      prev.find(p => p.id === paper.id)
        ? prev.filter(p => p.id !== paper.id)
        : [...prev, paper]
    );
  };

  return (
    <div className="research-container">
      {/* Header with search bar */}
      <div className="research-header">
        <div className="research-header-inner">
          <h1 className="research-title">Research Portal</h1>
          <div className="search-section">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleSearch}
              placeholder="What research question are you exploring?"
              className="search-input"
            />
          </div>
          
          <div className="search-controls">
            <div className="scope-buttons">
              {['both', 'local', 'all'].map(opt => (
                <button
                  key={opt}
                  onClick={() => setScope(opt)}
                  className={`scope-btn ${scope === opt ? 'active' : ''}`}
                >
                  {opt === 'both' ? '📚 Both' : opt === 'local' ? '📁 My Papers' : '🌐 Database'}
                </button>
              ))}
            </div>
            
            {/* Simple filters */}
            <input
              type="text"
              placeholder="Filter by topic..."
              value={filters.topic}
              onChange={(e) => setFilters({ ...filters, topic: e.target.value })}
              className="filter-input"
            />
          </div>
        </div>
      </div>

      {/* Main content: 2-column grid */}
      <div className="research-content">
        <div className="results-column">
          {loading && <div className="loading">Searching...</div>}
          
          {!loading && hasSearched && results.length === 0 && (
            <div className="no-results">
              <p className="no-results-text">No papers found for "{query}"</p>
              <p className="no-results-hint">Try broader terms or upload your own paper.</p>
            </div>
          )}
          
          {!hasSearched && !loading && (
            <div className="initial-state">
              <p className="initial-text">Search for papers or upload your own to begin</p>
            </div>
          )}
          
          {results.map(paper => (
            <PaperCard
              key={`${paper.source}-${paper.id}`}
              paper={paper}
              isPinned={pinned.some(p => p.id === paper.id)}
              onPin={togglePin}
            />
          ))}
        </div>

        {/* Right: Answer panel */}
        <div className="answer-column">
          {pinned.length === 0 ? (
            <div className="empty-answer-panel">
              <p className="empty-text">📌 Pin papers to ask questions</p>
              <p className="empty-hint">
                Click the pin icon on papers you want to cite in your answer.
              </p>
            </div>
          ) : (
            <>
              <button
                onClick={handleAsk}
                disabled={loading || !query.trim()}
                className="ask-button"
              >
                {loading ? '⏳ Thinking...' : '✨ Ask about pinned papers'}
              </button>
              
              {answer ? (
                <AnswerPanel answer={answer} />
              ) : (
                <div className="empty-answer">
                  <p>Ask a question about your pinned papers.</p>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Bottom: Session bar */}
      {pinned.length > 0 && (
        <SessionBar papers={pinned} onRemove={togglePin} />
      )}
    </div>
  );
}
