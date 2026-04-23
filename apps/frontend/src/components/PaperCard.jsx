import React from 'react';

export default function PaperCard({ paper, isPinned, onPin }) {
  const copyBibTeX = () => {
    const bibtex = `@article{${paper.id},
  title={${paper.title}},
  author={${paper.authors?.join(', ') || 'Unknown'}},
  year={${paper.year || 'n.d.'}},
  url={${paper.url || ''}}
}`;
    navigator.clipboard.writeText(bibtex);
    alert('BibTeX copied to clipboard!');
  };

  return (
    <div className={`paper-card ${isPinned ? 'pinned' : ''}`}>
      <div className="paper-content">
        <div className="paper-title-section">
          <h3 className="paper-title">{paper.title}</h3>
          <button 
            className={`pin-button ${isPinned ? 'pinned' : ''}`}
            onClick={() => onPin(paper)}
            title={isPinned ? 'Unpin paper' : 'Pin paper'}
          >
            {isPinned ? '📌' : '📍'}
          </button>
        </div>

        <p className="paper-meta">
          {paper.authors?.slice(0, 2).join(', ')} 
          {paper.authors?.length > 2 ? ' et al.' : ''} 
          {paper.year && ` • ${paper.year}`}
        </p>

        <p className="paper-abstract">{paper.abstract || 'No abstract available'}</p>

        <div className="paper-badges">
          <span className={`badge source-badge ${paper.source}`}>
            {paper.source === 'local' ? '📁 My Library' : '🌐 ' + (paper.source_name || 'External')}
          </span>
          {paper.year && <span className="badge year-badge">{paper.year}</span>}
          {paper.citation_count && <span className="badge citation-badge">{paper.citation_count} citations</span>}
        </div>

        <div className="paper-actions">
          <button onClick={copyBibTeX} className="action-btn" title="Copy BibTeX">
            📋 Cite
          </button>
          {paper.url && (
            <a href={paper.url} target="_blank" rel="noopener noreferrer" className="action-btn">
              🔗 View
            </a>
          )}
          {paper.pdf_url && (
            <a href={paper.pdf_url} target="_blank" rel="noopener noreferrer" className="action-btn">
              📄 PDF
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
