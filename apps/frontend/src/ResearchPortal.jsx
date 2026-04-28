import React, { useState, useCallback } from 'react';
import { searchAcademicPapers, queryAcademicRAG } from '../api/research';
import '../styles/ResearchPortal.css';

export default function ResearchPortal({ onLogout }) {
  const [query, setQuery] = useState('');
  const [answer, setAnswer] = useState(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [activeTab, setActiveTab] = useState('ask'); // 'ask' | 'search'
  const [error, setError] = useState('');

  // Submit question to RAG
  const handleAsk = useCallback(async () => {
    if (!query.trim()) return;
    setError('');
    setLoading(true);
    try {
      const response = await queryAcademicRAG(query);
      if (response.status === 'success') {
        setAnswer(response);
        setResults([]);
      } else {
        setError(response.message || 'Unable to generate answer');
        setAnswer(null);
      }
    } catch (err) {
      setError('Failed to query RAG. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [query]);

  // Search papers
  const handleSearch = useCallback(async () => {
    if (!query.trim()) return;
    setError('');
    setLoading(true);
    try {
      const papers = await searchAcademicPapers(query);
      setResults(papers || []);
      setAnswer(null);
    } catch (err) {
      setError('Search failed. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [query]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      activeTab === 'ask' ? handleAsk() : handleSearch();
    }
  };

  return (
    <div className="research-portal">
      {/* Header */}
      <header className="portal-header">
        <div className="header-content">
          <div className="logo-section">
            <span className="logo">📚</span>
            <h1>VeriRAG</h1>
          </div>
          <button onClick={onLogout} className="logout-btn">
            Logout
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="portal-main">
        <div className="portal-container">
          {/* Hero Section */}
          <div className="hero-section">
            <h2>Ask Research Questions</h2>
            <p>Powered by AI and your document library</p>
          </div>

          {/* Tabs */}
          <div className="tab-switcher">
            <button
              className={`tab-btn ${activeTab === 'ask' ? 'active' : ''}`}
              onClick={() => setActiveTab('ask')}
            >
              🤖 Ask AI
            </button>
            <button
              className={`tab-btn ${activeTab === 'search' ? 'active' : ''}`}
              onClick={() => setActiveTab('search')}
            >
              🔍 Search Papers
            </button>
          </div>

          {/* Search Bar */}
          <div className="search-box">
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                activeTab === 'ask'
                  ? 'Ask a research question... (e.g., "What are the latest advances in LLMs?")'
                  : 'Search for papers... (e.g., "machine learning")'
              }
              className="search-input"
              rows={3}
            />
            <div className="search-actions">
              <button
                onClick={activeTab === 'ask' ? handleAsk : handleSearch}
                disabled={!query.trim() || loading}
                className={`submit-btn ${loading ? 'loading' : ''}`}
              >
                {loading ? (
                  <>
                    <span className="spinner"></span> Processing...
                  </>
                ) : activeTab === 'ask' ? (
                  '✨ Ask'
                ) : (
                  '🔎 Search'
                )}
              </button>
              <p className="hint">Press Enter + Shift for new line</p>
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <div className="error-box">
              <span>⚠️</span>
              <p>{error}</p>
              <button onClick={() => setError('')}>×</button>
            </div>
          )}

          {/* Results Area */}
          <div className="results-section">
            {answer && (
              <div className="answer-card">
                <div className="card-header">
                  <h3>AI Answer</h3>
                  <span className="badge">Verified</span>
                </div>
                <div className="answer-content">
                  <p className="answer-text">{answer.answer}</p>
                  
                  {answer.sources && answer.sources.length > 0 && (
                    <div className="sources-section">
                      <h4>Sources</h4>
                      <div className="sources-list">
                        {answer.sources.map((source, idx) => (
                          <div key={idx} className="source-item">
                            <span className="source-badge">[{source.source_index}]</span>
                            <div className="source-content">
                              <p className="source-title">{source.title}</p>
                              {source.page && <p className="source-page">Page {source.page}</p>}
                              <p className="source-excerpt">{source.excerpt}...</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
                <button onClick={() => setAnswer(null)} className="clear-btn">
                  Clear Answer
                </button>
              </div>
            )}

            {results.length > 0 && (
              <div className="papers-grid">
                {results.map((paper, idx) => (
                  <div key={idx} className="paper-card">
                    <div className="paper-header">
                      <h4>{paper.title || 'Untitled'}</h4>
                      {paper.year && <span className="year-badge">{paper.year}</span>}
                    </div>
                    <p className="paper-authors">{paper.authors?.join(', ') || 'Unknown authors'}</p>
                    <p className="paper-abstract">{paper.abstract?.substring(0, 150)}...</p>
                    <div className="paper-footer">
                      <a href={paper.url} target="_blank" rel="noopener noreferrer" className="read-link">
                        Read Full Paper →
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {!answer && results.length === 0 && !loading && (
              <div className="empty-state">
                <span className="empty-icon">🎯</span>
                <h3>Ready to explore?</h3>
                <p>Ask a question or search for papers to get started</p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
