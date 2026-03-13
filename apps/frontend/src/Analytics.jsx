import React, { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  TrendingUp,
  BarChart3,
  PieChart,
  BrainCircuit,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Loader2,
  RefreshCw,
  Download,
} from "lucide-react";
import api from '@/lib/api';
import AppShell from '@/components/AppShell';

const Analytics = () => {
  const [isLoading, setIsLoading] = useState(true);
  const [queryHistory, setQueryHistory] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [systemMetrics, setSystemMetrics] = useState(null);
  const [selectedTimeRange, setSelectedTimeRange] = useState("24h");
  const [lastUpdated, setLastUpdated] = useState(null);

  // Fetch all analytics data
  const fetchAnalytics = useCallback(async () => {
    try {
      // Fetch system insights
      const insightsRes = await api.get('/api/system-insights/');
      setSystemMetrics(insightsRes.data);

      // Fetch documents
      const docsRes = await api.get('/api/documents/');
      setDocuments(docsRes.data);

      // Fetch query history from localStorage (simulated - in production this would be an API)
      const storedHistory = JSON.parse(localStorage.getItem("verirag_query_history") || "[]");
      setQueryHistory(storedHistory);

      setLastUpdated(new Date());
    } catch (err) {
      console.error("Analytics fetch error:", err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAnalytics();
    const interval = setInterval(fetchAnalytics, 30000);
    return () => clearInterval(interval);
  }, [fetchAnalytics]);

  // Calculate analytics metrics
  const calculateMetrics = () => {
    if (queryHistory.length === 0) {
      return {
        totalQueries: 0,
        avgFaithfulness: 0,
        verificationPassRate: 0,
        avgResponseTime: 0,
        highConfidenceQueries: 0,
        lowConfidenceQueries: 0,
        confidenceTrend: []
      };
    }

    const totalQueries = queryHistory.length;
    const scores = queryHistory.map(q => q.faithfulness_score || 0);
    const avgFaithfulness = scores.reduce((a, b) => a + b, 0) / totalQueries;
    const verifiedCount = queryHistory.filter(q => q.verification_passed).length;
    const verificationPassRate = (verifiedCount / totalQueries) * 100;
    const highConfidenceQueries = queryHistory.filter(q => (q.faithfulness_score || 0) >= 0.7).length;
    const lowConfidenceQueries = queryHistory.filter(q => (q.faithfulness_score || 0) < 0.6).length;

    // Calculate trend (last 10 queries)
    const recentQueries = queryHistory.slice(0, 10);
    const confidenceTrend = recentQueries.map((q, i) => ({
      index: i + 1,
      score: q.faithfulness_score || 0,
      passed: q.verification_passed
    })).reverse();

    return {
      totalQueries,
      avgFaithfulness,
      verificationPassRate,
      avgResponseTime: 1.2, // Simulated
      highConfidenceQueries,
      lowConfidenceQueries,
      confidenceTrend
    };
  };

  const metrics = calculateMetrics();

  // Document analytics
  const documentMetrics = {
    total: documents.length,
    processed: documents.filter(d => d.status === 'indexed' || d.processed).length,
    pending: documents.filter(d => d.status !== 'indexed' && !d.processed).length,
    failed: documents.filter(d => d.status === 'failed').length,
    processingRate: documents.length > 0 
      ? (documents.filter(d => d.status === 'indexed' || d.processed).length / documents.length) * 100 
      : 0
  };

  if (isLoading) {
    return (
      <div className="flex h-screen flex-col items-center justify-center bg-slate-950 text-slate-400">
        <Loader2 className="h-10 w-10 animate-spin text-indigo-500" />
        <p className="mt-4 font-mono text-xs uppercase tracking-[0.2em]">Loading Analytics...</p>
      </div>
    );
  }

  return (
    <AppShell
      title="Analytics"
      subtitle="Verification quality, document readiness, and usage trends across the current workspace."
      status={lastUpdated ? `UPDATED ${lastUpdated.toLocaleTimeString()}` : 'SYNCING'}
      headerRight={
        <div className="flex items-center gap-3">
          <div className="flex gap-1 rounded-lg bg-slate-900 p-1">
            {["1h", "24h", "7d", "30d"].map(range => (
              <button
                key={range}
                onClick={() => setSelectedTimeRange(range)}
                className={`px-3 py-1 text-[10px] font-bold rounded transition-all ${
                  selectedTimeRange === range
                    ? "bg-indigo-600 text-white"
                    : "text-slate-500 hover:text-white"
                }`}
              >
                {range.toUpperCase()}
              </button>
            ))}
          </div>
          <button
            onClick={fetchAnalytics}
            className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-slate-800 hover:text-white"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      }
    >
        {/* Key Performance Indicators */}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-4 mb-8">
          <Card className="border-slate-800 bg-gradient-to-br from-emerald-500/10 to-transparent">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[10px] font-mono uppercase text-slate-500 tracking-wider">Avg Faithfulness</p>
                  <p className="text-3xl font-black text-emerald-400 tabular-nums mt-1">
                    {(metrics.avgFaithfulness * 100).toFixed(1)}%
                  </p>
                </div>
                <div className="rounded-full bg-emerald-500/20 p-3">
                  <CheckCircle2 className="h-6 w-6 text-emerald-500" />
                </div>
              </div>
              <div className="mt-4 flex items-center gap-2 text-[10px]">
                <TrendingUp className="h-3 w-3 text-emerald-500" />
                <span className="text-emerald-500">+2.3%</span>
                <span className="text-slate-600">vs last period</span>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-800 bg-gradient-to-br from-blue-500/10 to-transparent">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[10px] font-mono uppercase text-slate-500 tracking-wider">Verification Rate</p>
                  <p className="text-3xl font-black text-blue-400 tabular-nums mt-1">
                    {metrics.verificationPassRate.toFixed(1)}%
                  </p>
                </div>
                <div className="rounded-full bg-blue-500/20 p-3">
                  <BrainCircuit className="h-6 w-6 text-blue-500" />
                </div>
              </div>
              <div className="mt-4 flex items-center gap-2 text-[10px]">
                <span className="text-slate-500">{metrics.highConfidenceQueries} high confidence queries</span>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-800 bg-gradient-to-br from-violet-500/10 to-transparent">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[10px] font-mono uppercase text-slate-500 tracking-wider">Total Queries</p>
                  <p className="text-3xl font-black text-violet-400 tabular-nums mt-1">
                    {systemMetrics?.metrics?.total_queries || metrics.totalQueries}
                  </p>
                </div>
                <div className="rounded-full bg-violet-500/20 p-3">
                  <BarChart3 className="h-6 w-6 text-violet-500" />
                </div>
              </div>
              <div className="mt-4 flex items-center gap-2 text-[10px]">
                <span className="text-slate-500">{systemMetrics?.metrics?.documents_ingested || documentMetrics.total} documents indexed</span>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-800 bg-gradient-to-br from-amber-500/10 to-transparent">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[10px] font-mono uppercase text-slate-500 tracking-wider">Hallucinations Blocked</p>
                  <p className="text-3xl font-black text-amber-400 tabular-nums mt-1">
                    {systemMetrics?.metrics?.hallucinations_prevented || 0}
                  </p>
                </div>
                <div className="rounded-full bg-amber-500/20 p-3">
                  <AlertTriangle className="h-6 w-6 text-amber-500" />
                </div>
              </div>
              <div className="mt-4 flex items-center gap-2 text-[10px]">
                <span className="text-amber-500">{systemMetrics?.metrics?.failover_recoveries || 0}</span>
                <span className="text-slate-600">failover recoveries</span>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 mb-8">
          {/* Confidence Trend Chart */}
          <Card className="border-slate-800 bg-slate-900/50">
            <CardHeader>
              <CardTitle className="text-sm font-mono uppercase tracking-wider text-slate-400 flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-emerald-500" />
                Verification Confidence Trend
              </CardTitle>
            </CardHeader>
            <CardContent>
              {metrics.confidenceTrend.length === 0 ? (
                <div className="h-48 flex items-center justify-center text-slate-600 text-sm">
                  <p>No query data yet. Start asking questions!</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Bar Chart Visualization */}
                  <div className="flex items-end gap-2 h-40 px-4">
                    {metrics.confidenceTrend.map((point, i) => (
                      <div key={i} className="flex-1 flex flex-col items-center gap-1">
                        <div 
                          className={`w-full rounded-t transition-all duration-500 ${
                            point.passed ? "bg-emerald-500" : "bg-amber-500"
                          }`}
                          style={{ height: `${point.score * 100}%`, minHeight: '8px' }}
                        />
                        <span className="text-[9px] text-slate-600">{(point.score * 100).toFixed(0)}%</span>
                      </div>
                    ))}
                  </div>
                  <div className="flex justify-between text-[10px] text-slate-600 px-4">
                    <span>Oldest</span>
                    <span>Most Recent</span>
                  </div>
                  {/* Legend */}
                  <div className="flex gap-4 justify-center text-[10px]">
                    <div className="flex items-center gap-1">
                      <div className="w-3 h-3 rounded bg-emerald-500" />
                      <span className="text-slate-500">Verified</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <div className="w-3 h-3 rounded bg-amber-500" />
                      <span className="text-slate-500">Below Threshold</span>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Document Distribution */}
          <Card className="border-slate-800 bg-slate-900/50">
            <CardHeader>
              <CardTitle className="text-sm font-mono uppercase tracking-wider text-slate-400 flex items-center gap-2">
                <PieChart className="h-4 w-4 text-blue-500" />
                Document Library Status
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-center gap-8">
                {/* Donut Chart Visualization */}
                <div className="relative w-32 h-32">
                  <svg viewBox="0 0 36 36" className="w-full h-full transform -rotate-90">
                    <circle
                      cx="18" cy="18" r="15.9155"
                      fill="none"
                      stroke="#1e293b"
                      strokeWidth="3"
                    />
                    <circle
                      cx="18" cy="18" r="15.9155"
                      fill="none"
                      stroke="#10b981"
                      strokeWidth="3"
                      strokeDasharray={`${documentMetrics.processingRate} ${100 - documentMetrics.processingRate}`}
                      strokeLinecap="round"
                    />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-2xl font-black text-white">{documentMetrics.total}</span>
                    <span className="text-[9px] text-slate-500 uppercase">Total Docs</span>
                  </div>
                </div>
                {/* Stats */}
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 rounded-full bg-emerald-500" />
                    <div>
                      <p className="text-sm font-bold text-white">{documentMetrics.processed}</p>
                      <p className="text-[10px] text-slate-500">Indexed & Ready</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 rounded-full bg-amber-500" />
                    <div>
                      <p className="text-sm font-bold text-white">{documentMetrics.pending}</p>
                      <p className="text-[10px] text-slate-500">Queued / Indexing</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 rounded-full bg-red-500" />
                    <div>
                      <p className="text-sm font-bold text-white">{documentMetrics.failed}</p>
                      <p className="text-[10px] text-slate-500">Failed</p>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Recent Verifications Table */}
        <Card className="border-slate-800 bg-slate-900/50">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-mono uppercase tracking-wider text-slate-400 flex items-center gap-2">
              <Clock className="h-4 w-4 text-indigo-500" />
              Recent Verification History
            </CardTitle>
            <Button 
              variant="outline" 
              size="sm" 
              className="text-xs border-slate-700 text-slate-400 hover:bg-slate-800"
            >
              <Download className="h-3 w-3 mr-2" /> Export
            </Button>
          </CardHeader>
          <CardContent>
            {queryHistory.length === 0 ? (
              <div className="py-12 text-center text-slate-600">
                <BrainCircuit className="h-12 w-12 mx-auto mb-4 opacity-30" />
                <p className="text-sm">No verification history yet.</p>
                <p className="text-xs text-slate-700 mt-1">Query documents to see verification analytics.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-slate-800">
                      <th className="text-left py-3 px-4 text-[10px] font-mono uppercase text-slate-600">Query</th>
                      <th className="text-center py-3 px-4 text-[10px] font-mono uppercase text-slate-600">Confidence</th>
                      <th className="text-center py-3 px-4 text-[10px] font-mono uppercase text-slate-600">Status</th>
                      <th className="text-center py-3 px-4 text-[10px] font-mono uppercase text-slate-600">Model</th>
                      <th className="text-center py-3 px-4 text-[10px] font-mono uppercase text-slate-600">Evidence</th>
                      <th className="text-right py-3 px-4 text-[10px] font-mono uppercase text-slate-600">Chunks</th>
                    </tr>
                  </thead>
                  <tbody>
                    {queryHistory.slice(0, 10).map((query, i) => (
                      <tr key={i} className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors">
                        <td className="py-3 px-4">
                          <p className="text-sm text-slate-300 truncate max-w-xs">{query.question}</p>
                        </td>
                        <td className="py-3 px-4 text-center">
                          <div className="inline-flex items-center gap-2">
                            <Progress value={(query.faithfulness_score || 0) * 100} className="w-16 h-1.5 bg-slate-800" />
                            <span className={`text-xs font-bold tabular-nums ${
                              (query.faithfulness_score || 0) >= 0.7 ? "text-emerald-400" :
                              (query.faithfulness_score || 0) >= 0.5 ? "text-amber-400" : "text-red-400"
                            }`}>
                              {((query.faithfulness_score || 0) * 100).toFixed(0)}%
                            </span>
                          </div>
                        </td>
                        <td className="py-3 px-4 text-center">
                          {query.verification_passed ? (
                            <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-500 bg-emerald-500/10 px-2 py-1 rounded-full">
                              <CheckCircle2 className="h-3 w-3" /> VERIFIED
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-[10px] font-bold text-amber-500 bg-amber-500/10 px-2 py-1 rounded-full">
                              <AlertTriangle className="h-3 w-3" /> FLAGGED
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-center">
                          <span className="text-[10px] font-mono text-slate-500 uppercase">
                            {query.model_used || "gemini"}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-center">
                          <span className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-[10px] font-bold ${
                            (query.evidence_items?.length || 0) > 0
                              ? "bg-cyan-500/10 text-cyan-400"
                              : "bg-slate-800 text-slate-500"
                          }`}>
                            {(query.evidence_items?.length || 0) > 0 ? `${query.evidence_items.length} refs` : "none"}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <span className="text-xs text-slate-500 tabular-nums">
                            {query.context_chunks_used || "—"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Footer */}
        <div className="mt-8 text-center text-[10px] text-slate-700">
          {lastUpdated && (
            <p>Last updated: {lastUpdated.toLocaleString()}</p>
          )}
        </div>
    </AppShell>
  );
};

export default Analytics;
