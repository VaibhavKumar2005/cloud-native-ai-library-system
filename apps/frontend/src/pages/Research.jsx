import React, { useCallback, useState } from 'react';
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Database,
  FileText,
  FileUp,
  Search,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { queryAcademicRAG } from '../api/research';
import AnswerPanel from '../components/AnswerPanel';
import '../styles/Research.css';
import '../styles/Components.css';

const demoPrompts = [
  'What is RAG?',
  'How does RAG improve accuracy?',
  'Explain quantum computing',
];

export default function Research() {
  const [query, setQuery] = useState('');
  const [answer, setAnswer] = useState(null);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState([]);

  const handleAsk = useCallback(async (nextQuery = query) => {
    const cleanQuery = nextQuery.trim();
    if (!cleanQuery) return;

    setQuery(cleanQuery);
    setLoading(true);

    try {
      const response = await queryAcademicRAG(cleanQuery);
      setAnswer(response);
      setHistory((items) => [
        { query: cleanQuery, status: response.status, time: new Date().toLocaleTimeString() },
        ...items,
      ].slice(0, 4));
    } catch (error) {
      setAnswer({
        status: 'rejected',
        message: 'Unable to reach the RAG backend. Start Django and try again.',
      });
    } finally {
      setLoading(false);
    }
  }, [query]);

  const handleKeyDown = (event) => {
    if (event.key === 'Enter') {
      handleAsk();
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
          <span className="status-pill">
            <CheckCircle2 size={16} /> Public demo mode
          </span>
        </div>

        <div className="metrics-row">
          <div className="metric-card">
            <span>Documents</span>
            <strong>Vector DB</strong>
            <small>Top 3 chunks retrieved</small>
          </div>
          <div className="metric-card">
            <span>Verification</span>
            <strong>Strict</strong>
            <small>No evidence means rejection</small>
          </div>
          <div className="metric-card">
            <span>Auth</span>
            <strong>Disabled</strong>
            <small>Demo opens instantly</small>
          </div>
        </div>

        <div className="console-grid">
          <aside className="library-panel">
            <div className="panel-title">
              <FileText size={20} />
              <div>
                <h3>Document Library</h3>
                <p>Upload flow can return after the demo.</p>
              </div>
            </div>
            <div className="upload-placeholder">
              <FileUp size={34} />
              <strong>Ready for indexed PDFs</strong>
              <span>For now, query the existing vector store directly.</span>
            </div>
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
              />
              <button onClick={() => handleAsk()} disabled={loading || !query.trim()}>
                {loading ? 'Querying...' : 'Query AI'}
              </button>
            </div>

            <div className="answer-region">
              {answer ? (
                <AnswerPanel answer={answer} />
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
              <span><CheckCircle2 size={16} /> Retrieval active</span>
              <span><CheckCircle2 size={16} /> Sources returned</span>
              <span><AlertTriangle size={16} /> Unsupported answers rejected</span>
            </div>
            {history.length > 0 && (
              <div className="query-history">
                <p>Recent queries</p>
                {history.map((item, index) => (
                  <div key={`${item.query}-${index}`}>
                    <strong>{item.status}</strong>
                    <span>{item.query}</span>
                    <small>{item.time}</small>
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
