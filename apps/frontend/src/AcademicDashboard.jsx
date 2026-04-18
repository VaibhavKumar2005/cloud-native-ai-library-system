import React, { useState, useEffect } from 'react';
import { Search, BookOpen, Lightbulb, TrendingUp, Download, Plus } from 'lucide-react';
import PaperSearch from './components/PaperSearch';
import ResearchGapAnalyzer from './components/ResearchGapAnalyzer';
import TopicRecommender from './components/TopicRecommender';
import ResearchLibrary from './components/ResearchLibrary';

/**
 * AcademicDashboard - AI-Powered Research Discovery for PhD Students
 * 
 * Features:
 * - Search & ingest papers from Semantic Scholar, arXiv, CrossRef
 * - Analyze papers for research gaps and trends
 * - AI-powered topic recommendations in AI Engineering
 * - RAG-based Q&A on ingested papers
 */
export default function AcademicDashboard({ onLogout }) {
  const [activeTab, setActiveTab] = useState('search');
  const [libraryCount, setLibraryCount] = useState(0);
  const [loadingStats, setLoadingStats] = useState(true);

  useEffect(() => {
    // Fetch library stats
    const fetchStats = async () => {
      try {
        const response = await fetch('/api/papers/library-stats/', {
          headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
        });
        const data = await response.json();
        setLibraryCount(data.total_papers || 0);
      } catch (err) {
        console.error('Failed to fetch stats:', err);
      } finally {
        setLoadingStats(false);
      }
    };
    fetchStats();
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-slate-700 bg-slate-900/80 backdrop-blur">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                <BookOpen className="text-white" size={24} />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">VeriRAG Academic</h1>
                <p className="text-sm text-slate-400">AI-Powered Research Discovery for PhD Students</p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="hidden sm:flex items-center gap-2 px-4 py-2 bg-slate-800 rounded-lg border border-slate-700">
                <BookOpen size={16} className="text-slate-400" />
                <span className="text-sm text-slate-300">
                  {loadingStats ? 'Loading...' : `${libraryCount} papers`}
                </span>
              </div>
              <button
                onClick={onLogout}
                className="px-4 py-2 text-sm font-medium text-slate-300 hover:text-white transition"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <div className="border-b border-slate-700 bg-slate-900/40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex gap-1 overflow-x-auto">
            {[
              { id: 'search', label: 'Search Papers', icon: Search },
              { id: 'library', label: 'My Library', icon: BookOpen },
              { id: 'gaps', label: 'Research Gaps', icon: TrendingUp },
              { id: 'topics', label: 'Topic Explorer', icon: Lightbulb }
            ].map(tab => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-4 py-3 text-sm font-medium border-b-2 transition ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-400'
                      : 'border-transparent text-slate-400 hover:text-slate-300'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <Icon size={16} />
                    {tab.label}
                  </div>
                </button>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {activeTab === 'search' && <PaperSearch />}
        {activeTab === 'library' && <ResearchLibrary />}
        {activeTab === 'gaps' && <ResearchGapAnalyzer />}
        {activeTab === 'topics' && <TopicRecommender />}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-700 bg-slate-900/40 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-center text-sm text-slate-400">
            Powered by AI-driven academic research discovery | Built for PhD students exploring AI Engineering
          </p>
        </div>
      </footer>
    </div>
  );
}
