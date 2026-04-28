import React from 'react';

export default function AnswerPanel({ answer }) {
  if (!answer.answer) {
    return (
      <div className="answer-panel error">
        <div className="answer-header">
          <h4>⚠️ No Answer Found</h4>
        </div>
        <p className="answer-text">{answer.message || 'Unable to find relevant information in your papers.'}</p>
        
        {answer.suggested_papers?.length > 0 && (
          <div className="suggested-papers">
            <p className="suggested-label">💡 Suggested papers:</p>
            <div className="suggested-list">
              {answer.suggested_papers.map((p, idx) => (
                <a 
                  key={idx}
                  href={p.url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="suggested-paper-link"
                >
                  {p.title} ({p.year})
                </a>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="answer-panel success">
      <div className="answer-header">
        <h4>Answer</h4>
        <div className="answer-meta">
          <span className="confidence">
            {typeof answer.confidence === 'number'
              ? `${Math.round(answer.confidence * 100)}% ${answer.confidence_label || 'confidence'}`
              : answer.confidence_label || 'confidence pending'}
          </span>
          {answer.retrieval?.chunks_returned > 0 && (
            <span className="source-count">
              {answer.retrieval.chunks_returned}/{answer.retrieval.top_k} chunks used
            </span>
          )}
          {answer.sources?.length > 0 && (
            <span className="source-count">
              Based on {answer.sources.length} source{answer.sources.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      </div>
      
      <div className="answer-body">
        <p className="answer-text">{answer.answer}</p>
      </div>

      {answer.sources && answer.sources.length > 0 && (
        <div className="answer-sources">
          <p className="sources-label">Sources cited</p>
          <div className="sources-list">
            {answer.sources.map((src, idx) => (
              <div key={idx} className="source-item">
                <a 
                  href={src.metadata_url || '#'} 
                  className="source-title"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {src.title}
                </a>
                <div className="source-info">
                  <span className="source-type">{src.source}</span>
                  {typeof src.relevance === 'number' && <span className="source-score">{Math.round(src.relevance * 100)}% match</span>}
                </div>
                {src.excerpt && <p className="source-excerpt">"{src.excerpt}"</p>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
