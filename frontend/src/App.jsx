import { useState, useEffect } from 'react';

function App() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Connect to the Flask Backend
    fetch('http://localhost:5000/health/db')
      .then((res) => res.json())
      .then((data) => {
        setStatus(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to fetch backend status:", err);
        setLoading(false);
      });
  }, []);

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      <div className="bg-slate-800 p-8 rounded-xl shadow-2xl max-w-md w-full border border-slate-700">
        <h1 className="text-3xl font-bold text-white mb-6 text-center">
          System Architecture
        </h1>

        {loading ? (
          <p className="text-slate-400 text-center animate-pulse">Ping network...</p>
        ) : (
          <div className="space-y-4">
            
            {/* Status Item: MongoDB */}
            <div className="flex items-center justify-between p-4 bg-slate-900 rounded-lg">
              <div className="flex items-center space-x-3">
                <span className="text-2xl">🍃</span>
                <span className="text-slate-200 font-medium">MongoDB (Logs)</span>
              </div>
              <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                status?.mongo === 'connected' 
                  ? 'bg-green-500/20 text-green-400' 
                  : 'bg-red-500/20 text-red-400'
              }`}>
                {status?.mongo?.toUpperCase() || 'OFFLINE'}
              </span>
            </div>

            {/* Status Item: PostgreSQL */}
            <div className="flex items-center justify-between p-4 bg-slate-900 rounded-lg">
              <div className="flex items-center space-x-3">
                <span className="text-2xl">🐘</span>
                <span className="text-slate-200 font-medium">Postgres (Users)</span>
              </div>
              <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                status?.postgres === 'connected' 
                  ? 'bg-green-500/20 text-green-400' 
                  : 'bg-red-500/20 text-red-400'
              }`}>
                {status?.postgres?.toUpperCase() || 'OFFLINE'}
              </span>
            </div>

          </div>
        )}

        <div className="mt-8 text-center">
          <p className="text-slate-500 text-xs">
            Powered by Azure Kubernetes Service & HashiCorp Vault
          </p>
        </div>
      </div>
    </div>
  );
}

export default App;