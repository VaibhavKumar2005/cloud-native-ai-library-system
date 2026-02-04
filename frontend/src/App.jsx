import React, { useState } from 'react';
import axios from 'axios';

function App() {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleVerify = async () => {
    if (!query) return;
    setLoading(true);
    setResult(null);

    try {
      // UPDATED URL: Using 127.0.0.1 to prevent Windows localhost conflicts
      const response = await axios.post('http://127.0.0.1:8000/api/query/', {
        query: query
      });
      setResult(response.data);
    } catch (error) {
      console.error("Connection Error:", error);
      setResult({
        answer: "Connection failed. Ensure Django is running on Port 8000 and CORS is allowed.",
        faithfulness_score: 0
      });
    } finally {
      setLoading(false);
    }
  };

  return (
  <div className="min-h-screen bg-[#020617] text-slate-200 flex flex-col font-sans selection:bg-blue-500/30">
    
    {/* Animated Background Texture */}
    <div className="fixed inset-0 z-0 overflow-hidden pointer-events-none">
      <div className="absolute -top-[10%] -left-[10%] w-[40%] h-[40%] bg-blue-500/10 blur-[120px] rounded-full"></div>
      <div className="absolute top-[20%] -right-[10%] w-[30%] h-[50%] bg-indigo-500/10 blur-[120px] rounded-full"></div>
    </div>

    {/* Glass Navbar */}
    <nav className="w-full border-b border-slate-800 bg-slate-900/50 backdrop-blur-xl px-8 py-4 flex justify-between items-center sticky top-0 z-50">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 bg-gradient-to-br from-blue-400 to-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/20">
          <span className="text-white font-black">V</span>
        </div>
        <span className="text-xl font-bold tracking-tight text-white">VeriRag</span>
      </div>
      <div className="flex items-center gap-2 px-3 py-1 bg-slate-800/50 rounded-full border border-slate-700">
        <span className={`w-2 h-2 rounded-full ${loading ? 'bg-blue-400 animate-pulse' : 'bg-emerald-400'}`}></span>
        <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
          {loading ? 'Processing' : 'System Live'}
        </span>
      </div>
    </nav>

    {/* Hero Section */}
    <main className="relative z-10 flex-1 max-w-5xl mx-auto w-full p-6 mt-20">
      <div className="text-center mb-16">
        <h1 className="text-6xl md:text-7xl font-extrabold text-white mb-6 tracking-tight leading-[1.1]">
          The Search Engine that <br />
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-indigo-400 to-emerald-400">
            Checks its Own Homework.
          </span>
        </h1>
        <p className="text-slate-400 text-lg max-w-2xl mx-auto leading-relaxed">
          A production-grade RAG architecture for your CS Library. Verified generation with 
          <span className="text-blue-400 font-mono"> Faithfulness Scores</span>.
        </p>
      </div>

      {/* Search Input with Glow */}
      <div className="max-w-3xl mx-auto relative group">
        <div className="absolute -inset-1 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-2xl blur opacity-25 group-focus-within:opacity-50 transition duration-500"></div>
        <div className="relative bg-slate-900 border border-slate-700 rounded-2xl flex items-center p-2 shadow-2xl">
          <input 
            type="text" 
            className="flex-1 bg-transparent px-5 py-4 text-white outline-none text-lg placeholder-slate-500"
            placeholder="Ask a question about Computer Science..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleVerify()}
          />
          <button 
            onClick={handleVerify}
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-500 text-white px-10 py-4 rounded-xl font-bold transition-all active:scale-95 shadow-lg shadow-blue-500/20 disabled:bg-slate-800"
          >
            {loading ? 'Analysing...' : 'Verify'}
          </button>
        </div>
      </div>

      {/* Result Display */}
      {result && (
        <div className="mt-12 max-w-3xl mx-auto animate-in fade-in slide-in-from-bottom-8 duration-700">
          <div className="bg-slate-900/80 border border-slate-700 rounded-3xl overflow-hidden backdrop-blur-sm">
            <div className="px-8 py-5 border-b border-slate-800 flex justify-between items-center bg-slate-800/30">
              <span className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em]">Verified Response</span>
              <div className="flex items-center gap-3">
                <span className="text-xs font-bold text-slate-400">Faithfulness:</span>
                <span className={`text-xs font-mono font-bold px-2 py-1 rounded ${result.faithfulness_score > 0.8 ? 'text-emerald-400 bg-emerald-400/10' : 'text-amber-400 bg-amber-400/10'}`}>
                  {(result.faithfulness_score * 100).toFixed(0)}%
                </span>
              </div>
            </div>
            <div className="p-10">
              <p className="text-xl text-slate-200 leading-relaxed font-light italic">
                "{result.answer}"
              </p>
              {result.source_citation && (
                <div className="mt-8 pt-8 border-t border-slate-800/50">
                  <span className="text-[10px] font-bold text-blue-400 uppercase tracking-widest block mb-3">Context Source</span>
                  <div className="p-4 bg-blue-500/5 rounded-xl border border-blue-500/10 text-sm text-slate-400 font-mono">
                    {result.source_citation}
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