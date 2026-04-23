import React from 'react';

export default function SessionBar({ papers, onRemove }) {
  return (
    <div className="session-bar">
      <div className="session-bar-inner">
        <span className="session-label">📌 Your Session</span>
        <div className="session-papers">
          {papers.map(paper => (
            <div key={paper.id} className="session-paper">
              <span className="session-paper-title">{paper.title}</span>
              <button
                className="remove-btn"
                onClick={() => onRemove(paper)}
                title="Remove from session"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
