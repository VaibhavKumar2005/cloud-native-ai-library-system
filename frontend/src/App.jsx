import React, { useState } from 'react';

function App() {
  const [query, setQuery] = useState('');

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col font-sans">
      
      {/* Navbar */}
      <nav className="w-full bg-white border-b border-gray-200 px-8 py-4 flex justify-between items-center sticky top-0 z-50">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold">V</div>
          <span className="text-xl font-semibold text-gray-800 tracking-tight">VeriRag</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
          <span className="text-green-600 text-sm font-medium">System Active</span>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="flex-1 flex flex-col items-center justify-center p-6 text-center mt-10">
        
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 border border-blue-100 text-blue-600 text-xs font-bold uppercase tracking-wider mb-6">
          Project 46: Verified Generation
        </div>

        <h1 className="text-5xl md:text-6xl font-extrabold text-gray-900 mb-6 leading-tight max-w-4xl">
          The Search Engine that <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">
            Checks its Own Homework.
          </span>
        </h1>

        {/* Search Box */}
        <div className="w-full max-w-2xl relative group mt-8">
          <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-2xl blur opacity-25 group-hover:opacity-50 transition duration-200"></div>
          <div className="relative bg-white rounded-xl shadow-xl flex items-center p-2 border border-gray-100">
            <input 
              type="text" 
              className="flex-1 px-4 py-3 text-gray-700 outline-none placeholder-gray-400 text-lg"
              placeholder="Ask a question..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <button className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-lg font-semibold transition-all">
              Verify
            </button>
          </div>
        </div>

      </main>
    </div>
  );
}

export default App;