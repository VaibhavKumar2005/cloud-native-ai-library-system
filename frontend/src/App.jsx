// FILE: frontend/src/App.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = 'http://127.0.0.1:8000/api';

function App() {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [showUpload, setShowUpload] = useState(false);

  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      const response = await axios.get(`${API_BASE}/documents/`);
      setDocuments(response.data);
    } catch (error) {
      console.error("Failed to fetch documents:", error);
    }
  };

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', file.name);

    setUploading(true);
    try {
      await axios.post(`${API_BASE}/upload/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      fetchDocuments();
      setShowUpload(false);
      alert('Document uploaded and processed successfully!');
    } catch (error) {
      console.error("Upload failed:", error);
      alert('Upload failed: ' + (error.response?.data?.error || error.message));
    } finally {
      setUploading(false);
    }
  };

  const handleVerify = async () => {
    if (!query) return;
    setLoading(true);
    setResult(null);

    try {
      const response = await axios.post(`${API_BASE}/query/`, {
        query: query
      });
      setResult(response.data);
    } catch (error) {
      console.error("Query failed:", error);
      setResult({
        answer: "Connection failed. Is the Django server running?",
        faithfulness_score: 0,
        explanation: error.message,
        source_citation: "System Error"
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#020617] text-slate-200 selection:bg-blue-500/30">
      
      {/* Ambient Background Glow */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-blue-500/10 blur-[120px] rounded-full"></div>
        <div className="absolute bottom-[10%] right-[-5%] w-[40%] h-[40%] bg-indigo-600/10 blur-[100px] rounded-full"></div>
      </div>

      {/* Navbar */}
      <nav className="sticky top-0 z-50 w-full border-b border-slate-800 bg-slate-950/70 backdrop-blur-md px-6 py-4 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gradient-to-tr from-blue-500 to-indigo-600 rounded-lg shadow-lg shadow-blue-500/20 flex items-center justify-center font-black text-white">V</div>
          <span className="text-lg font-bold tracking-tight text-white">VeriRag</span>
        </div>
        <div className="hidden md:flex items-center gap-6 text-sm font-medium text-slate-400">
          <span className="hover:text-white cursor-pointer transition-colors" onClick={() => setShowUpload(!showUpload)}>
            📄 Upload PDF
          </span>
          <span className="hover:text-white cursor-pointer transition-colors">
            {documents.length} Documents
          </span>
          <div className={`px-3 py-1 rounded-full border border-slate-800 flex items-center gap-2 ${loading ? 'bg-blue-500/10' : 'bg-emerald-500/10'}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${loading ? 'bg-blue-400 animate-pulse' : 'bg-emerald-400'}`}></span>
            <span className="text-[10px] uppercase tracking-widest font-bold text-slate-300">
              {loading ? 'Analyzing' : 'Ready'}
            </span>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="relative z-10 max-w-5xl mx-auto px-6 pt-24 pb-20">
        
        {/* Upload Section */}
        {showUpload && (
          <div className="mb-12 max-w-3xl mx-auto">
            <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-8 backdrop-blur-sm">
              <h3 className="text-2xl font-bold text-white mb-4">Upload PDF Document</h3>
              <input 
                type="file" 
                accept=".pdf"
                onChange={handleUpload}
                disabled={uploading}
                className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-xl text-white file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-blue-600 file:text-white hover:file:bg-blue-500 disabled:opacity-50"
              />
              {uploading && <p className="mt-3 text-blue-400 text-sm">Processing document...</p>}
            </div>
          </div>
        )}

        <div className="text-center mb-16">
          <h1 className="text-5xl md:text-7xl font-extrabold text-white tracking-tight mb-6">
            RAG that doesn't <br />
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-indigo-400 to-cyan-400">
              make things up.
            </span>
          </h1>
          <p className="text-slate-400 text-lg md:text-xl max-w-2xl mx-auto font-light leading-relaxed">
            Verify the faithfulness of your AI Librarian. Built for high-stakes 
            Computer Science research and verified generation.
          </p>
        </div>

        {/* Search Input */}
        <div className="max-w-3xl mx-auto relative group">
          <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-cyan-500 rounded-2xl blur opacity-20 group-focus-within:opacity-40 transition duration-500"></div>
          <div className="relative bg-slate-900 border border-slate-700 rounded-2xl flex items-center p-2 shadow-2xl">
            <input 
              type="text" 
              className="flex-1 bg-transparent px-5 py-4 text-white outline-none text-lg placeholder-slate-500"
              placeholder="Ask your library a question..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleVerify()}
            />
            <button 
              onClick={handleVerify}
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-500 text-white px-10 py-4 rounded-xl font-bold transition-all active:scale-95 shadow-lg shadow-blue-500/20 disabled:bg-slate-800"
            >
              {loading ? 'Thinking...' : 'Verify'}
            </button>
          </div>
        </div>

        {/* Results */}
        {result && (
          <div className="mt-12 max-w-3xl mx-auto animate-in fade-in slide-in-from-bottom-8 duration-700">
            <div className="bg-slate-900/50 border border-slate-800 rounded-3xl overflow-hidden backdrop-blur-sm">
              <div className="px-8 py-5 border-b border-slate-800/50 flex justify-between items-center bg-slate-800/20">
                <span className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em]">Verified Response</span>
                <div className="flex items-center gap-3">
                  <span className="text-xs font-bold text-slate-400">Faithfulness:</span>
                  <span className={`text-xs font-mono font-bold px-2 py-1 rounded ${result.faithfulness_score > 0.8 ? 'text-emerald-400 bg-emerald-400/10 border border-emerald-500/20' : 'text-amber-400 bg-amber-400/10 border border-amber-500/20'}`}>
                    {(result.faithfulness_score * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
              <div className="p-10">
                <p className="text-xl text-slate-200 leading-relaxed font-light">
                  {result.answer}
                </p>
                
                {/* Explanation */}
                {result.explanation && (
                  <div className="mt-6 p-4 bg-slate-800/50 rounded-xl border border-slate-700/50">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block mb-2">Verification Details</span>
                    <p className="text-sm text-slate-300">{result.explanation}</p>
                  </div>
                )}
                
                {/* Source Citation */}
                {result.source_citation && result.source_citation !== "None" && result.source_citation !== "System Error" && (
                  <div className="mt-8 pt-8 border-t border-slate-800/50">
                    <span className="text-[10px] font-bold text-blue-400 uppercase tracking-widest block mb-3">Librarian's Proof</span>
                    <div className="p-5 bg-blue-500/5 rounded-2xl border border-blue-500/10 text-sm text-slate-400 font-mono leading-relaxed">
                      "{result.source_citation}"
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;