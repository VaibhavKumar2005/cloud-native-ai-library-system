import React, { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  DollarSign,
  CheckCircle,
  TrendingUp,
  AlertCircle,
  Zap,
  Database,
  Lock,
  Container,
  Terminal,
  Loader2,
  WifiOff,
  AlertTriangle,
  Clock,
  BarChart3
} from "lucide-react";
import { Progress } from "@/components/ui/progress";
import api from '@/lib/api';
import AppShell from '@/components/AppShell';

const POLL_INTERVAL_MS = 30000; // 30 seconds for ops data

const Monitoring = () => {
  const navigate = useNavigate();
  const [opsDashboard, setOpsDashboard] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [logs, setLogs] = useState([]);
  const [costHistory, setCostHistory] = useState([]);
  const [qualityHistory, setQualityHistory] = useState([]);
  const [sessionStart] = useState(new Date());
  const logEndRef = useRef(null);

  // ── Ops Dashboard Fetch ──────────────────────────────────────────────
  const fetchOpsDashboard = useCallback(async (isInitial = false) => {
    try {
      const res = await api.get('/api/ai/ops/dashboard/');
      const data = res.data;
      setOpsDashboard(data);
      setFetchError(null);
      setLastUpdated(new Date());

      // Log ops event
      const costAlert = data.cost.alert ? "⚠️ BUDGET ALERT" : "✅ Budget OK";
      const qualityStatus = data.quality.week.trending;
      const newLog = {
        ts: new Date().toISOString(),
        level: data.health.overall_status === "healthy" ? "INFO" : "WARN",
        msg: `[ops] Cost: $${data.cost.today.total_cost.toFixed(2)} (${data.cost.today.budget_utilization.toFixed(1)}%) | Quality: ${data.quality.week.average_score.toFixed(2)} (${qualityStatus}) | ${costAlert}`
      };
      setLogs(prev => [newLog, ...prev].slice(0, 50));

      // Track cost history
      setCostHistory(prev => [
        ...prev,
        {
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          cost: data.cost.today.total_cost,
          budget_pct: data.cost.today.budget_utilization,
          requests: data.cost.today.requests
        }
      ].slice(-20));

      // Track quality history
      setQualityHistory(prev => [
        ...prev,
        {
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          score: data.quality.week.average_score,
          components_passing: data.quality.week.components_passing,
          trending: data.quality.week.trending
        }
      ].slice(-20));

    } catch (err) {
      console.error("Ops Dashboard Fetch Error:", err);
      setFetchError("network");
    } finally {
      if (isInitial) setIsLoading(false);
    }
  }, [navigate]);

  useEffect(() => {
    fetchOpsDashboard(true);
    const interval = setInterval(() => fetchOpsDashboard(false), POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchOpsDashboard]);

  // ── Render Helpers ──────────────────────────────────────────────────
  if (fetchError === "auth") {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-950 px-6">
        <Card className="w-full max-w-md border-red-900/50 bg-slate-900/50 backdrop-blur-xl">
          <CardContent className="pt-6 text-center">
            <AlertTriangle className="mx-auto mb-4 h-12 w-12 text-red-500" />
            <h2 className="text-xl font-bold text-slate-100">Access Denied</h2>
            <p className="mt-2 text-sm text-slate-400">Your session has expired or is invalid. Secure re-authorization required.</p>
            <button 
              onClick={() => navigate("/login")}
              className="mt-6 w-full rounded-lg bg-indigo-600 py-2 text-sm font-semibold text-white transition-hover hover:bg-indigo-500"
            >
              Return to Login
            </button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex h-screen flex-col items-center justify-center bg-slate-950 text-slate-400">
        <Loader2 className="h-10 w-10 animate-spin text-indigo-500" />
        <p className="mt-4 font-mono text-xs uppercase tracking-[0.2em]">Synchronizing Ops Dashboard...</p>
      </div>
    );
  }

  const budgetAlert = opsDashboard?.cost.alert;
  const qualityIssues = opsDashboard?.quality.critical_issues || [];
  const overallHealth = opsDashboard?.health.overall_status;

  return (
    <AppShell
      title="Operations Control"
      subtitle="CostOps, QualityOps, and infrastructure health at a glance."
      status={overallHealth?.toUpperCase() || 'CONNECTING'}
      headerRight={
        fetchError === "network" ? (
          <span className="flex items-center gap-2 rounded-full bg-amber-500/10 px-3 py-1 text-[10px] font-bold text-amber-500 border border-amber-500/20">
            <WifiOff className="h-3 w-3" /> LINK INTERRUPTED
          </span>
        ) : budgetAlert ? (
          <span className="flex items-center gap-2 rounded-full bg-red-500/10 px-3 py-1 text-[10px] font-bold text-red-500 border border-red-500/20">
            <AlertCircle className="h-3 w-3" /> BUDGET ALERT
          </span>
        ) : null
      }
    >
        {/* Cost Operations Row */}
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          {/* Daily Cost */}
          <Card className="border-slate-800 bg-slate-900/50 hover:border-cyan-500/30 transition-all">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-xs font-mono uppercase tracking-wider text-slate-500">Daily Spend</CardTitle>
              <DollarSign className="h-4 w-4 text-cyan-500" />
            </CardHeader>
            <CardContent>
              <div className="text-4xl font-black text-cyan-400 tabular-nums">
                ${opsDashboard?.cost.today.total_cost.toFixed(2)}
              </div>
              <p className="mt-1 text-[10px] uppercase text-slate-500 tracking-wide">{opsDashboard?.cost.today.requests} Requests</p>
              <Progress 
                value={opsDashboard?.cost.today.budget_utilization || 0} 
                className="mt-4 h-1 bg-slate-800" 
              />
              <p className="mt-2 text-[9px] text-slate-600">{opsDashboard?.cost.today.budget_utilization.toFixed(1)}% of daily budget</p>
            </CardContent>
          </Card>

          {/* Quality Score */}
          <Card className="border-slate-800 bg-slate-900/50 hover:border-emerald-500/30 transition-all">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-xs font-mono uppercase tracking-wider text-slate-500">Quality Score</CardTitle>
              <CheckCircle className="h-4 w-4 text-emerald-500" />
            </CardHeader>
            <CardContent>
              <div className="text-4xl font-black text-emerald-400 tabular-nums">
                {(opsDashboard?.quality.week.average_score * 100).toFixed(0)}%
              </div>
              <p className="mt-1 text-[10px] uppercase text-slate-500 tracking-wide">{opsDashboard?.quality.week.evaluations} Evaluated</p>
              <Progress 
                value={opsDashboard?.quality.week.average_score * 100 || 0} 
                className="mt-4 h-1 bg-slate-800" 
              />
              <p className="mt-2 text-[9px] text-slate-600">Components: {opsDashboard?.quality.week.components_passing.toFixed(1)}% passing</p>
            </CardContent>
          </Card>

          {/* Quality Trend */}
          <Card className="border-slate-800 bg-slate-900/50 hover:border-violet-500/30 transition-all">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-xs font-mono uppercase tracking-wider text-slate-500">Trend</CardTitle>
              <TrendingUp className="h-4 w-4 text-violet-500" />
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold uppercase tracking-wide ${
                opsDashboard?.quality.week.trending === 'improving' ? 'text-emerald-400' :
                opsDashboard?.quality.week.trending === 'degrading' ? 'text-red-400' :
                'text-amber-400'
              }`}>
                {opsDashboard?.quality.week.trending}
              </div>
              <p className="mt-1 text-[10px] uppercase text-slate-500 tracking-wide">Quality Direction</p>
              <div className="mt-5 flex gap-1">
                {[...Array(6)].map((_, i) => (
                  <div 
                    key={i} 
                    className={`h-1 w-full rounded-full ${
                      opsDashboard?.quality.week.trending === 'improving' ? 'bg-emerald-500/40' :
                      opsDashboard?.quality.week.trending === 'degrading' ? 'bg-red-500/40' :
                      'bg-amber-500/40'
                    }`} 
                  />
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Alerts Row */}
        {(budgetAlert || qualityIssues.length > 0) && (
          <div className="mt-10 grid grid-cols-1 gap-4 md:grid-cols-2">
            {budgetAlert && (
              <Card className="border-red-900/50 bg-red-950/30">
                <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
                  <CardTitle className="text-xs font-mono uppercase tracking-wider text-red-400">Budget Alert</CardTitle>
                  <AlertCircle className="h-4 w-4 text-red-500" />
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-red-300">{budgetAlert.message}</p>
                  <p className="mt-2 text-xs text-red-400">Remaining: ${budgetAlert.remaining.toFixed(2)}</p>
                </CardContent>
              </Card>
            )}
            {qualityIssues.length > 0 && (
              <Card className="border-amber-900/50 bg-amber-950/30">
                <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
                  <CardTitle className="text-xs font-mono uppercase tracking-wider text-amber-400">Quality Issues</CardTitle>
                  <AlertCircle className="h-4 w-4 text-amber-500" />
                </CardHeader>
                <CardContent>
                  <div className="space-y-1">
                    {qualityIssues.slice(0, 2).map((issue, i) => (
                      <p key={i} className="text-xs text-amber-300">• {issue}</p>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {/* Cost & Quality Trends Row */}
        <div className="mt-10 grid grid-cols-1 gap-6 md:grid-cols-2">
          {/* Cost Trend */}
          <Card className="border-slate-800 bg-slate-900/50">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-xs font-mono uppercase tracking-wider text-slate-500 flex items-center gap-2">
                <BarChart3 className="h-3 w-3" /> Cost Trend
              </CardTitle>
              <span className="text-[9px] text-slate-600 font-mono">{costHistory.length} SAMPLES</span>
            </CardHeader>
            <CardContent>
              {costHistory.length < 2 ? (
                <p className="text-xs text-slate-600 italic py-4 text-center">Collecting data points...</p>
              ) : (
                <div className="space-y-3">
                  <div className="flex items-end gap-[3px] h-16">
                    {costHistory.map((point, i) => {
                      const maxCost = Math.max(...costHistory.map(p => p.cost), 1);
                      const height = Math.max((point.cost / maxCost) * 100, 8);
                      return (
                        <div
                          key={i}
                          className={`flex-1 rounded-t transition-all duration-500 ${
                            point.budget_pct > 80 ? "bg-red-500/60" : point.budget_pct > 50 ? "bg-amber-500/60" : "bg-cyan-500/60"
                          }`}
                          style={{ height: `${height}%` }}
                          title={`${point.time}: $${point.cost.toFixed(2)} (${point.budget_pct.toFixed(1)}%)`}
                        />
                      );
                    })}
                  </div>
                  <div className="flex justify-between text-[9px] text-slate-700 font-mono">
                    <span>{costHistory[0]?.time}</span>
                    <span>{costHistory[costHistory.length - 1]?.time}</span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Quality Trend */}
          <Card className="border-slate-800 bg-slate-900/50">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-xs font-mono uppercase tracking-wider text-slate-500 flex items-center gap-2">
                <TrendingUp className="h-3 w-3" /> Quality Trend
              </CardTitle>
              <span className="text-[9px] text-slate-600 font-mono">{qualityHistory.length} SAMPLES</span>
            </CardHeader>
            <CardContent>
              {qualityHistory.length < 2 ? (
                <p className="text-xs text-slate-600 italic py-4 text-center">Collecting data points...</p>
              ) : (
                <div className="space-y-3">
                  <div className="flex items-end gap-[3px] h-16">
                    {qualityHistory.map((point, i) => {
                      const height = Math.max(point.score * 100, 8);
                      return (
                        <div
                          key={i}
                          className={`flex-1 rounded-t transition-all duration-500 ${
                            point.score >= 0.85 ? "bg-emerald-500/60" : point.score >= 0.75 ? "bg-cyan-500/60" : "bg-amber-500/60"
                          }`}
                          style={{ height: `${height}%` }}
                          title={`${point.time}: ${(point.score * 100).toFixed(0)}% (${point.trending})`}
                        />
                      );
                    })}
                  </div>
                  <div className="flex justify-between text-[9px] text-slate-700 font-mono">
                    <span>{qualityHistory[0]?.time}</span>
                    <span>{qualityHistory[qualityHistory.length - 1]?.time}</span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
        {/* API Status Row */}
        <div className="mt-10 grid grid-cols-1 gap-4 md:grid-cols-3">
          <Card className="border-slate-800 bg-slate-950 p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <DollarSign className="h-4 w-4 text-slate-500" />
                <span className="text-xs font-medium text-slate-300">CostOps Status</span>
              </div>
              <span className="text-[10px] font-mono font-bold text-cyan-400 uppercase tracking-tighter">
                {opsDashboard?.health.cost_ops_enabled ? "ACTIVE" : "DISABLED"}
              </span>
            </div>
          </Card>
          <Card className="border-slate-800 bg-slate-950 p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <CheckCircle className="h-4 w-4 text-slate-500" />
                <span className="text-xs font-medium text-slate-300">QualityOps Status</span>
              </div>
              <span className="text-[10px] font-mono font-bold text-emerald-400 uppercase tracking-tighter">
                {opsDashboard?.health.quality_ops_enabled ? "ACTIVE" : "DISABLED"}
              </span>
            </div>
          </Card>
          <Card className="border-slate-800 bg-slate-950 p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Zap className="h-4 w-4 text-slate-500" />
                <span className="text-xs font-medium text-slate-300">System Health</span>
              </div>
              <span className={`text-[10px] font-mono font-bold uppercase tracking-tighter ${
                opsDashboard?.health.overall_status === 'healthy' ? 'text-emerald-400' : 'text-amber-400'
              }`}>
                {opsDashboard?.health.overall_status?.toUpperCase()}
              </span>
            </div>
          </Card>
        </div>

        {/* Session Stats */}
        <div className="mt-10 grid grid-cols-1 gap-6 md:grid-cols-2">
          {/* Cost Summary */}
          <Card className="border-slate-800 bg-slate-900/50">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-xs font-mono uppercase tracking-wider text-slate-500 flex items-center gap-2">
                <DollarSign className="h-3 w-3" /> Cost Summary
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-[10px] uppercase text-slate-600 tracking-wide">This Week</p>
                  <p className="text-lg font-bold text-cyan-400 tabular-nums">
                    ${opsDashboard?.cost.week.total_cost.toFixed(2)}
                  </p>
                </div>
                <div>
                  <p className="text-[10px] uppercase text-slate-600 tracking-wide">Avg Cost/Request</p>
                  <p className="text-lg font-bold text-slate-300 tabular-nums">
                    ${opsDashboard?.cost.week.avg_cost_per_request.toFixed(4)}
                  </p>
                </div>
                <div>
                  <p className="text-[10px] uppercase text-slate-600 tracking-wide">Weekly Requests</p>
                  <p className="text-lg font-bold text-cyan-400 tabular-nums">{opsDashboard?.cost.week.requests}</p>
                </div>
                <div>
                  <p className="text-[10px] uppercase text-slate-600 tracking-wide">Today Remaining</p>
                  <p className={`text-lg font-bold tabular-nums ${
                    opsDashboard?.cost.today.budget_remaining > 20 ? 'text-emerald-400' : 'text-red-400'
                  }`}>
                    ${opsDashboard?.cost.today.budget_remaining.toFixed(2)}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Quality Summary */}
          <Card className="border-slate-800 bg-slate-900/50">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-xs font-mono uppercase tracking-wider text-slate-500 flex items-center gap-2">
                <CheckCircle className="h-3 w-3" /> Quality Summary
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-[10px] uppercase text-slate-600 tracking-wide">Weekly Avg</p>
                  <p className="text-lg font-bold text-emerald-400 tabular-nums">
                    {(opsDashboard?.quality.week.average_score * 100).toFixed(0)}%
                  </p>
                </div>
                <div>
                  <p className="text-[10px] uppercase text-slate-600 tracking-wide">Monthly Avg</p>
                  <p className="text-lg font-bold text-slate-300 tabular-nums">
                    {(opsDashboard?.quality.month.average_score * 100).toFixed(0)}%
                  </p>
                </div>
                <div>
                  <p className="text-[10px] uppercase text-slate-600 tracking-wide">Weekly Evals</p>
                  <p className="text-lg font-bold text-emerald-400 tabular-nums">{opsDashboard?.quality.week.evaluations}</p>
                </div>
                <div>
                  <p className="text-[10px] uppercase text-slate-600 tracking-wide">Components OK</p>
                  <p className="text-lg font-bold text-slate-300 tabular-nums">
                    {opsDashboard?.quality.week.components_passing.toFixed(1)}%
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Ops Event Stream */}
        <div className="mt-10">
          <div className="flex items-center justify-between rounded-t-xl border border-slate-800 bg-slate-900/50 px-4 py-2">
            <div className="flex items-center gap-2">
              <Terminal className="h-4 w-4 text-slate-400" />
              <span className="text-[10px] font-mono text-slate-400">verirag-ops --stream</span>
            </div>
            <div className="flex gap-1.5">
              <div className="h-2 w-2 rounded-full bg-red-500/50" />
              <div className="h-2 w-2 rounded-full bg-amber-500/50" />
              <div className="h-2 w-2 rounded-full bg-emerald-500/50" />
            </div>
          </div>
          <div className="h-80 overflow-y-auto rounded-b-xl border border-t-0 border-slate-800 bg-black/90 p-4 font-mono text-[11px] leading-relaxed">
            {logs.map((log, i) => (
              <div key={i} className="mb-1 flex gap-4">
                <span className="text-slate-700 shrink-0">{new Date(log.ts).toLocaleTimeString()}</span>
                <span className={`shrink-0 w-10 ${log.level === 'INFO' ? 'text-emerald-500' : 'text-amber-500'}`}>{log.level}</span>
                <span className="text-slate-400">{log.msg}</span>
              </div>
            ))}
            <div className="text-indigo-500 animate-pulse mt-2">█</div>
            <div ref={logEndRef} />
          </div>
        </div>
    </AppShell>
  );
};

export default Monitoring;
