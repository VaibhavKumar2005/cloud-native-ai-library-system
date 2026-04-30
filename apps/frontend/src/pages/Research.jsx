import React, { useCallback, useEffect, useState } from 'react';
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Database,
  FileText,
  FileUp,
  Loader2,
  Search,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { checkBackendHealth, runAgenticQuery, searchAcademicPapers, uploadDocument } from '../api/research';
import AnswerPanel from '../components/AnswerPanel';
import '../styles/Research.css';
import '../styles/Components.css';

const demoPrompts = [
  'What is RAG?',
  'How does RAG improve accuracy?',
  'Why does VeriRAG reject some questions?',
];

const HISTORY_KEY = 'verirag_agentic_history_v1';

export default function Research() {
  const [query, setQuery] = useState('');
  const [answer, setAnswer] = useState(null);
  const [loading, setLoading] = useState(false);
  const [backendHealth, setBackendHealth] = useState({ state: 'checking', label: 'Checking backend' });
  const [uploadState, setUploadState] = useState({ status: 'idle', message: '' });
  const [history, setHistory] = useState([]);
  const [paperCandidates, setPaperCandidates] = useState([]);
  const [selectedPapers, setSelectedPapers] = useState([]);
  const [pendingQuery, setPendingQuery] = useState('');
  const [paperSearchQuery, setPaperSearchQuery] = useState('');
  const [paperSearchResults, setPaperSearchResults] = useState([]);
  const [paperSearchLoading, setPaperSearchLoading] = useState(false);

  const totalQueries = history.length;
  const groundedCount = history.filter((item) => item.status === 'answer').length;
  const rejectedCount = history.filter((item) => item.status === 'rejected').length;
  const groundedRate = totalQueries > 0 ? Math.round((groundedCount / totalQueries) * 100) : 0;

  useEffect(() => {
    let active = true;

    checkBackendHealth()
      .then((health) => {
        if (!active) return;
        setBackendHealth({
          state: health.healthy ? 'healthy' : 'degraded',
          label: health.healthy ? 'Backend connected' : 'Backend degraded',
        });
      })
      .catch(() => {
        if (!active) return;
        setBackendHealth({
          state: 'offline',
          label: 'Backend offline',
        });
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
      if (Array.isArray(saved)) {
        setHistory(saved.slice(0, 12));
      }
    } catch {
      setHistory([]);
    }
  }, []);

  useEffect(() => {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, 12)));
  }, [history]);

  const addHistoryItem = useCallback((entry, limit = 12) => {
    setHistory((items) => [entry, ...items].slice(0, limit));
  }, []);

  const removeHistoryItem = useCallback((indexToRemove) => {
    setHistory((items) => items.filter((_, index) => index !== indexToRemove));
  }, []);

  const clearHistory = useCallback(() => {
    setHistory([]);
  }, []);

  const togglePaperSelection = useCallback((paper, checked) => {
    setSelectedPapers((items) => {
      const alreadySelected = items.some((item) => item.id === paper.id);
      if (checked) {
        return alreadySelected ? items : [...items, paper];
      }
      return items.filter((item) => item.id !== paper.id);
    });
  }, []);

  const handlePaperSearch = useCallback(async () => {
    const cleanSearch = paperSearchQuery.trim();
    if (!cleanSearch) return;

    setPaperSearchLoading(true);
    try {
      const papers = await searchAcademicPapers(cleanSearch, 6);
      setPaperSearchResults(papers);
    } catch (error) {
      setAnswer({
        status: 'rejected',
        message: error.message || 'Paper search failed.',
      });
    } finally {
      setPaperSearchLoading(false);
    }
  }, [paperSearchQuery]);

  const handleAsk = useCallback(async (nextQuery = query) => {
    const cleanQuery = nextQuery.trim();
    if (!cleanQuery) return;

    setQuery(cleanQuery);
    setLoading(true);
    setPaperCandidates([]);

    try {
      const response = await runAgenticQuery(
        cleanQuery,
        selectedPapers,
        selectedPapers[0]?.source || 'semantic-scholar'
      );
      if (response.status === 'needs_selection') {
        setPendingQuery(cleanQuery);
        setPaperCandidates(response.candidates || []);
        setAnswer({
          status: 'selection_required',
          message: response.message || 'Select papers to ground the answer.',
        });
      } else {
        setAnswer(response.result || response);
      }
      addHistoryItem({
        query: cleanQuery,
        status: response.status || response?.result?.status || 'answered',
        time: new Date().toLocaleTimeString(),
      });
    } catch (error) {
      setAnswer({
        status: 'rejected',
        message: error.message || 'Unable to reach the RAG backend. Start Django and try again.',
      });
      setBackendHealth({
        state: 'offline',
        label: 'Backend offline',
      });
    } finally {
      setLoading(false);
    }
  }, [query, selectedPapers]);

  const handleGroundWithSelected = useCallback(async () => {
    if (!pendingQuery || selectedPapers.length === 0) return;
    setLoading(true);
    try {
      const response = await runAgenticQuery(
        pendingQuery,
        selectedPapers,
        selectedPapers[0]?.source || 'semantic-scholar'
      );
      setAnswer(response.result || response);
      setPaperCandidates([]);
      setPendingQuery('');
      addHistoryItem({
        query: `${pendingQuery} (grounded with selected papers)`,
        status: response.status || response?.result?.status || 'answered',
        time: new Date().toLocaleTimeString(),
      });
    } catch (error) {
      setAnswer({
        status: 'rejected',
        message: error.message || 'Failed to ground with selected papers.',
      });
    } finally {
      setLoading(false);
    }
  }, [pendingQuery, selectedPapers]);

  const handleUpload = useCallback(async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploadState({ status: 'uploading', message: `Uploading ${file.name}` });

    try {
      const document = await uploadDocument(file);
      setUploadState({
        status: 'queued',
        message: `${document.title || file.name} queued for indexing`,
      });
      addHistoryItem(
        {
          query: `Uploaded ${file.name}`,
          status: document.status || 'queued',
          time: new Date().toLocaleTimeString(),
        },
        12
      );
    } catch (error) {
      setUploadState({
        status: 'error',
        message: error.message || 'Upload failed',
      });
    } finally {
      event.target.value = '';
    }
  }, [addHistoryItem]);

  const handleKeyDown = (event) => {
    if (event.key === 'Enter') {
      handleAsk();
    }
  };

  const handlePaperSearchKeyDown = (event) => {
    if (event.key === 'Enter') {
      handlePaperSearch();
    }
  };

  return (
    <main className="verirag-page">
      <header className="verirag-nav">
        <a className="brand-lockup" href="#top" aria-label="VeriRAG home">
          <span className="brand-mark"><ShieldCheck size={26} /></span>
          <span>
            <strong>VeriRAG</strong>
            <small>Verified AI Librarian</small>
          </span>
        </a>
        <nav className="nav-actions" aria-label="Demo navigation">
          <a href="#workflow">Workflow</a>
          <a href="#workspace" className="primary-nav">Open Workspace</a>
        </nav>
      </header>

      <section id="top" className="hero-section">
        <div className="hero-grid" />
        <div className="hero-copy">
          <span className="eyebrow"><Sparkles size={16} /> Blueprint phase</span>
          <h1>Verified answers over complex documents.</h1>
          <p>
            VeriRAG combines retrieval, evidence tracking, and strict rejection so the demo
            behaves like a research assistant you can trust.
          </p>
          <div className="hero-actions">
            <a href="#workspace" className="cta-button">
              Enter Workspace <ArrowRight size={18} />
            </a>
            <a href="#workflow" className="ghost-button">View Pipeline</a>
          </div>
        </div>
      </section>

      <section id="workflow" className="workflow-section">
        <div className="section-heading">
          <span className="eyebrow">RAG pipeline</span>
          <h2>Query, retrieve, generate, or reject.</h2>
        </div>
        <div className="workflow-grid">
          <div className="workflow-card">
            <Search size={22} />
            <h3>Query</h3>
            <p>The user asks a research question in plain language.</p>
          </div>
          <div className="workflow-card">
            <Database size={22} />
            <h3>Retrieve</h3>
            <p>The backend retrieves the top three relevant chunks from the vector store.</p>
          </div>
          <div className="workflow-card">
            <Sparkles size={22} />
            <h3>Generate</h3>
            <p>The LLM must answer only from retrieved context and cite sources.</p>
          </div>
          <div className="workflow-card">
            <ShieldCheck size={22} />
            <h3>Return or Reject</h3>
            <p>If reliable evidence is missing, the system rejects the question.</p>
          </div>
        </div>
      </section>

      <section id="workspace" className="workspace-section">
        <div className="workspace-head">
          <div>
            <span className="eyebrow">Live workspace</span>
            <h2>Ask grounded questions, then inspect the evidence.</h2>
          </div>
          <span className={`status-pill ${backendHealth.state}`}>
            {backendHealth.state === 'checking' ? <Loader2 size={16} className="spin" /> : <CheckCircle2 size={16} />}
            {backendHealth.label}
          </span>
        </div>

        <div className="metrics-row">
          <div className="metric-card">
            <span>Queries</span>
            <strong>{totalQueries}</strong>
            <small>Live workspace interactions</small>
          </div>
          <div className="metric-card">
            <span>Grounded Rate</span>
            <strong>{groundedRate}%</strong>
            <small>Answers returned with evidence</small>
          </div>
          <div className="metric-card">
            <span>Rejections</span>
            <strong>{rejectedCount}</strong>
            <small>Insufficient-evidence guardrails</small>
          </div>
        </div>

        <div className="console-grid">
          <aside className="library-panel">
            <div className="panel-title">
              <FileText size={20} />
              <div>
                <h3>Document Library</h3>
                <p>Index PDFs into the retrieval store.</p>
              </div>
            </div>
            <div className="sub-panel">
              <p className="sub-panel-label">Search research papers</p>
              <div className="query-box compact-query-box">
                <Search size={18} />
                <input
                  value={paperSearchQuery}
                  onChange={(event) => setPaperSearchQuery(event.target.value)}
                  onKeyDown={handlePaperSearchKeyDown}
                  placeholder="Find papers about RAG, agents, evals..."
                  aria-label="Search research papers"
                />
                <button onClick={handlePaperSearch} disabled={paperSearchLoading || !paperSearchQuery.trim()}>
                  {paperSearchLoading ? 'Searching...' : 'Search'}
                </button>
              </div>
              {selectedPapers.length > 0 && (
                <div className="selected-papers-summary">
                  <strong>{selectedPapers.length} selected</strong>
                  <button type="button" onClick={() => setSelectedPapers([])}>Clear</button>
                </div>
              )}
              {paperSearchResults.length > 0 && (
                <div className="paper-search-results">
                  {paperSearchResults.map((paper) => {
                    const isSelected = selectedPapers.some((item) => item.id === paper.id);
                    return (
                      <label key={paper.id} className={`paper-card ${isSelected ? 'selected' : ''}`}>
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={(event) => togglePaperSelection(paper, event.target.checked)}
                        />
                        <span>
                          <strong>{paper.title}</strong>
                          <small>{paper.year} · {paper.source}</small>
                        </span>
                      </label>
                    );
                  })}
                </div>
              )}
            </div>
            <label className={`upload-placeholder upload-dropzone ${uploadState.status}`}>
              {uploadState.status === 'uploading' ? <Loader2 size={34} className="spin" /> : <FileUp size={34} />}
              <strong>{uploadState.status === 'idle' ? 'Upload research PDF' : uploadState.message}</strong>
              <span>Files are queued for offline indexing, then become searchable from chat.</span>
              <input type="file" accept="application/pdf,.pdf" onChange={handleUpload} disabled={uploadState.status === 'uploading'} />
            </label>
            <div className="next-actions">
              <p>Demo script</p>
              {demoPrompts.map((prompt) => (
                <button key={prompt} onClick={() => handleAsk(prompt)}>
                  {prompt}
                </button>
              ))}
            </div>
          </aside>

          <section className="chat-panel">
            <div className="panel-title">
              <Sparkles size={20} />
              <div>
                <h3>Verified AI Chat</h3>
                <p>Responses are grounded against retrieved chunks.</p>
              </div>
            </div>

            <div className="query-box">
              <Search size={20} />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask VeriRAG Librarian..."
                aria-label="Research question input"
              />
              <button onClick={() => handleAsk()} disabled={loading || !query.trim()}>
                {loading ? 'Querying...' : 'Query AI'}
              </button>
            </div>

            <div className="answer-region">
              {paperCandidates.length > 0 && (
                <div className="paper-picker" aria-live="polite">
                  <h4>Found papers for grounding. Choose what to use:</h4>
                  {paperCandidates.map((paper) => {
                    const isSelected = selectedPapers.some((item) => item.id === paper.id);
                    return (
                      <label key={paper.id} className="paper-option">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={(event) => togglePaperSelection(paper, event.target.checked)}
                        />
                        <span>
                          <strong>{paper.title}</strong>
                          <small>{paper.year} · {paper.source}</small>
                        </span>
                      </label>
                    );
                  })}
                  <button
                    className="ground-button"
                    onClick={handleGroundWithSelected}
                    disabled={loading || selectedPapers.length === 0}
                  >
                    {loading ? 'Grounding...' : `Ground answer with ${selectedPapers.length} selected`}
                  </button>
                </div>
              )}
              {answer ? (
                <>
                  <AnswerPanel answer={answer} />
                  {answer.status === 'rejected' && (
                    <div className="empty-evidence" style={{ marginTop: '12px' }}>
                      <AlertTriangle size={22} />
                      <h3>Try a More Targeted Query</h3>
                      <p>
                        This rejection is expected when evidence is weak. Search and ingest a relevant paper,
                        then ask again with specific terms (model, dataset, institution, year).
                      </p>
                    </div>
                  )}
                </>
              ) : (
                <div className="empty-evidence">
                  <ShieldCheck size={36} />
                  <h3>Evidence Panel</h3>
                  <p>Run a verified query to inspect the supporting evidence here.</p>
                </div>
              )}
            </div>
          </section>

          <aside className="health-panel">
            <div className="panel-title">
              <ShieldCheck size={20} />
              <div>
                <h3>Reliability</h3>
                <p>Demo posture</p>
              </div>
            </div>
            <div className="health-list">
              <span><CheckCircle2 size={16} /> Backend health checked</span>
              <span><CheckCircle2 size={16} /> Confidence returned</span>
              <span><AlertTriangle size={16} /> Unsupported answers rejected</span>
            </div>
            {history.length > 0 && (
              <div className="query-history">
                <div className="query-history-header">
                  <p>Recent queries</p>
                  <button type="button" onClick={clearHistory}>Clear all</button>
                </div>
                {history.map((item, index) => (
                  <div key={`${item.query}-${index}`} className="query-history-item">
                    <strong>{item.status}</strong>
                    <span>{item.query}</span>
                    <small>{item.time}</small>
                    <button type="button" onClick={() => removeHistoryItem(index)} aria-label={`Delete history item ${item.query}`}>
                      Delete
                    </button>
                  </div>
                ))}
              </div>
            )}
          </aside>
        </div>
      </section>
    </main>
  );
}
