import React, { useState } from 'react';
import axios from 'axios'; // We use this to talk to Django

function App() {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState(null); // Stores Answer + Score
  const [loading, setLoading] = useState(false); // Controls the "Thinking" state

  const handleVerify = async () => {
    if (!query) return;
    setLoading(true);
    setResult(null);

    try {
      // Connects to your Django URL we set up in views.py
      const response = await axios.post('http://localhost:8000/api/query/', {
        query: query
      });
      setResult(response.data);
    } catch (error) {
      console.error("Error connecting to Brain:", error);
      setResult({
        answer: "Connection failed. Is the Django server running?",
        faithfulness_score: 0
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col font-sans">
      
      {/* Navbar */}
      <nav className="w-full bg-white border-b border-gray-200 px-8 py-4 flex justify-between items-center sticky top-0 z-50">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold shadow-sm">V</div>
          <span className="text-xl font-bold text-gray-800 tracking-tight">VeriRag</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${loading ? 'bg-blue-500 animate-ping' : 'bg-green-500 animate-pulse'}`}></span>
          <span className="text-gray-600 text-sm font-medium">{loading ? 'AI Thinking...' : 'System Active'}</span>
        </div>
      </nav>

      {/* Main Container */}
      <main className="flex-1 max-w-4xl mx-auto w-full p-6 mt-10">
        
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 border border-blue-100 text-blue-600 text-xs font-bold uppercase tracking-wider mb-6">
            Project 46: Verified Generation
          </div>
          <h1 className="text-5xl font-extrabold text-gray-900 mb-4 leading-tight">
            The Search Engine that <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">
              Checks its Own Homework.
            </span>
          </h1>
        </div>

        {/* Search Box */}
        <div className="relative group mb-10">
          <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-2xl blur opacity-25 group-hover:opacity-40 transition duration-300"></div>
          <div className="relative bg-white rounded-xl shadow-xl flex items-center p-2 border border-gray-100">
            <input 
              type="text" 
              className="flex-1 px-4 py-3 text-gray-700 outline-none text-lg"
              placeholder="Ask a question from your books..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleVerify()}
            />
            <button 
              onClick={handleVerify}
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-8 py-3 rounded-lg font-semibold transition-all shadow-md"
            >
              {loading ? 'Processing...' : 'Verify'}
            </button>
          </div>
        </div>

        {/* --- RESULT SECTION --- */}
        {result && (
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
              <span className="font-bold text-gray-800 uppercase text-xs tracking-widest">AI Librarian Response</span>
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-gray-500">Faithfulness:</span>
                <span className={`px-2 py-1 rounded text-xs font-bold ${result.faithfulness_score > 0.8 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                  {(result.faithfulness_score * 100).toFixed(0)}%
                </span>
              </div>
            </div>
            <div className="p-8">
              <p className="text-gray-700 text-lg leading-relaxed mb-6">
                {result.answer}
              </p>
              {result.source_citation && (
                <div className="p-4 bg-blue-50/50 rounded-lg border border-blue-100">
                  <span className="block text-xs font-bold text-blue-600 uppercase mb-2">Source Proof</span>
                  <p className="text-sm text-blue-800 italic">"{result.source_citation}"</p>
                </div>
              )}
            </div>
          </div>
        )}

      </main>
    </div>
  );
}

export default App;