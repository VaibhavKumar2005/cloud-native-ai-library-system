import React, { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Activity,
  ShieldCheck,
  Zap,
  BrainCircuit,
  Database,
  Lock,
  Container,
  Terminal,
  Loader2,
  WifiOff,
  RefreshCw,
  AlertTriangle,
  ArrowLeft,
  TrendingUp,
  Clock
} from "lucide-react";
import { Progress } from "@/components/ui/progress";
import api from '@/lib/api';

const POLL_INTERVAL_MS = 10000;

const Monitoring = () => {
  const navigate = useNavigate();
  const [telemetry, setTelemetry] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [logs, setLogs] = useState([]);
  const [trendHistory, setTrendHistory] = useState([]);
  const [sessionStart] = useState(new Date());
  const logEndRef = useRef(null);

  // ── Telemetry Logic ──────────────────────────────────────────────────
  const fetchInsights = useCallback(async (isInitial = false) => {
    try {
      const res = await api.get('/api/system-insights/');
      const data = res.data;
      setTelemetry(data);
      setFetchError(null);
      setLastUpdated(new Date());

      // Append real-time log event based on engine status
      const newLog = {
        ts: new Date().toISOString(),
        level: data.status === "Operational" ? "INFO" : "WARN",
        msg: `[system] Telemetry sync: ${data.metrics.hallucinations_prevented} blocked, Vault: ${data.infrastructure.vault}, DB: ${data.infrastructure.database}`
      };
      setLogs(prev => [newLog, ...prev].slice(0, 50));

      // Track trend data for confidence chart (up to 20 data points)
      setTrendHistory(prev => [
        ...prev,
        {
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
          blocked: data.metrics.hallucinations_prevented,
          failovers: data.metrics.failover_recoveries,
          status: data.status
        }
      ].slice(-20));

    } catch (err) {
      console.error("Telemetry Fetch Error:", err);
      setFetchError("network");
    } finally {
      if (isInitial) setIsLoading(false);
    }
  }, [navigate]);

  useEffect(() => {
    fetchInsights(true);
    const interval = setInterval(() => fetchInsights(false), POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchInsights]);

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
        <p className="mt-4 font-mono text-xs uppercase tracking-[0.2em]">Synchronizing Telemetry Link...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 pb-12 font-sans text-slate-100 selection:bg-indigo-500/30">
      {/* Top Navigation Bar */}
      <nav className="sticky top-0 z-50 border-b border-slate-800 bg-slate-950/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            
            {/* --- THE NEW BACK BUTTON --- */}
            <button 
              onClick={() => navigate("/")} 
              className="mr-2 p-2 hover:bg-slate-800 rounded-lg transition-colors text-slate-400 hover:text-white"
              title="Back to Library"
            >
              <ArrowLeft className="h-5 w-5" />
            </button>
            {/* ------------------------- */}

            <div className="rounded-lg bg-indigo-500/10 p-2 border border-indigo-500/20">
              <Activity className="h-5 w-5 text-indigo-400" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight">Mission Control</h1>
              <p className="text-[10px] font-mono uppercase tracking-widest text-slate-500">VeriRAG Node Cluster v2.0</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            {fetchError === "network" && (
              <span className="flex items-center gap-2 rounded-full bg-amber-500/10 px-3 py-1 text-[10px] font-bold text-amber-500 border border-amber-500/20">
                <WifiOff className="h-3 w-3" /> LINK INTERRUPTED
              </span>
            )}
            <div className="text-right">
              <p className="text-[10px] font-mono text-slate-500 uppercase">System Status</p>
              <p className={`text-xs font-bold ${telemetry?.status === 'Operational' ? 'text-emerald-400' : 'text-red-400'}`}>
                {telemetry?.status?.toUpperCase()}
              </p>
              {lastUpdated && (
                <p className="text-[9px] text-slate-600 mt-1 font-mono">
                  UPDATED: {lastUpdated.toLocaleTimeString()}
                </p>
              )}
            </div>
          </div>
        </div>
      </nav>

      <main className="mx-auto max-w-7xl px-6 pt-10">
        {/* Metric Cards */}
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          <Card className="border-slate-800 bg-slate-900/50 hover:border-emerald-500/30 transition-all">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-xs font-mono uppercase tracking-wider text-slate-500">AI Integrity</CardTitle>
              <ShieldCheck className="h-4 w-4 text-emerald-500" />
            </CardHeader>
            <CardContent>
              <div className="text-4xl font-black text-emerald-400 tabular-nums">
                {telemetry?.metrics.hallucinations_prevented}
              </div>
              <p className="mt-1 text-[10px] uppercase text-slate-500 tracking-wide">Hallucinations Blocked</p>
              <Progress value={85} className="mt-4 h-1 bg-slate-800" />
            </CardContent>
          </Card>

          <Card className="border-slate-800 bg-slate-900/50 hover:border-blue-500/30 transition-all">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-xs font-mono uppercase tracking-wider text-slate-500">Availability</CardTitle>
              <Zap className="h-4 w-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-4xl font-black text-blue-400 tabular-nums">
                {telemetry?.metrics.failover_recoveries}
              </div>
              <p className="mt-1 text-[10px] uppercase text-slate-500 tracking-wide">Failover Recoveries</p>
              <Progress value={100} className="mt-4 h-1 bg-slate-800" />
            </CardContent>
          </Card>

          <Card className="border-slate-800 bg-slate-900/50 hover:border-violet-500/30 transition-all">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-xs font-mono uppercase tracking-wider text-slate-500">Engine Status</CardTitle>
              <div className="relative flex h-2 w-2">
                <span className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-75 ${telemetry?.metrics.active_model.includes('Flash') ? 'bg-emerald-500' : 'bg-blue-500'}`}></span>
                <span className={`relative inline-flex h-2 w-2 rounded-full ${telemetry?.metrics.active_model.includes('Flash') ? 'bg-emerald-500' : 'bg-blue-500'}`}></span>
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-xl font-bold text-violet-400 truncate">
                {telemetry?.metrics.active_model}
              </div>
              <p className="mt-1 text-[10px] uppercase text-slate-500 tracking-wide">Active Verification Model</p>
              <div className="mt-5 flex gap-1">
                {[...Array(6)].map((_, i) => (
                  <div key={i} className="h-1 w-full rounded-full bg-violet-500/40" />
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Infrastructure Row */}
        <div className="mt-10 grid grid-cols-1 gap-4 md:grid-cols-3">
          <Card className="border-slate-800 bg-slate-950 p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Database className="h-4 w-4 text-slate-500" />
                <span className="text-xs font-medium text-slate-300">Vector Database</span>
              </div>
              <span className="text-[10px] font-mono font-bold text-emerald-400 uppercase tracking-tighter">
                {telemetry?.infrastructure.database}
              </span>
            </div>
          </Card>
          <Card className="border-slate-800 bg-slate-950 p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Lock className="h-4 w-4 text-slate-500" />
                <span className="text-xs font-medium text-slate-300">HashiCorp Vault</span>
              </div>
              <span className="text-[10px] font-mono font-bold text-emerald-400 uppercase tracking-tighter">
                {telemetry?.infrastructure.vault}
              </span>
            </div>
          </Card>
          <Card className="border-slate-800 bg-slate-950 p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Container className="h-4 w-4 text-slate-500" />
                <span className="text-xs font-medium text-slate-300">Orchestration</span>
              </div>
              <span className="text-[10px] font-mono font-bold text-blue-400 uppercase tracking-tighter">
                {telemetry?.infrastructure.orchestration}
              </span>
            </div>
          </Card>
        </div>

        {/* Confidence Trend & Uptime Row */}
        <div className="mt-10 grid grid-cols-1 gap-6 md:grid-cols-2">
          {/* Verification Confidence Trend (Mini Sparkline) */}
          <Card className="border-slate-800 bg-slate-900/50">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-xs font-mono uppercase tracking-wider text-slate-500 flex items-center gap-2">
                <TrendingUp className="h-3 w-3" /> Integrity Trend
              </CardTitle>
              <span className="text-[9px] text-slate-600 font-mono">{trendHistory.length} SAMPLES</span>
            </CardHeader>
            <CardContent>
              {trendHistory.length < 2 ? (
                <p className="text-xs text-slate-600 italic py-4 text-center">Collecting data points...</p>
              ) : (
                <div className="space-y-3">
                  {/* ASCII-style sparkline visualization */}
                  <div className="flex items-end gap-[3px] h-16">
                    {trendHistory.map((point, i) => {
                      const maxVal = Math.max(...trendHistory.map(p => p.blocked), 1);
                      const height = Math.max((point.blocked / maxVal) * 100, 8);
                      return (
                        <div
                          key={i}
                          className={`flex-1 rounded-t transition-all duration-500 ${
                            point.status === "Operational" ? "bg-emerald-500/60" : "bg-amber-500/60"
                          }`}
                          style={{ height: `${height}%` }}
                          title={`${point.time}: ${point.blocked} blocked`}
                        />
                      );
                    })}
                  </div>
                  <div className="flex justify-between text-[9px] text-slate-700 font-mono">
                    <span>{trendHistory[0]?.time}</span>
                    <span>{trendHistory[trendHistory.length - 1]?.time}</span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Session Uptime & Stats */}
          <Card className="border-slate-800 bg-slate-900/50">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-xs font-mono uppercase tracking-wider text-slate-500 flex items-center gap-2">
                <Clock className="h-3 w-3" /> Session Stats
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-[10px] uppercase text-slate-600 tracking-wide">Session Uptime</p>
                  <p className="text-lg font-bold text-indigo-400 tabular-nums">
                    <SessionUptime start={sessionStart} />
                  </p>
                </div>
                <div>
                  <p className="text-[10px] uppercase text-slate-600 tracking-wide">Telemetry Polls</p>
                  <p className="text-lg font-bold text-slate-300 tabular-nums">{trendHistory.length}</p>
                </div>
                <div>
                  <p className="text-[10px] uppercase text-slate-600 tracking-wide">System Health</p>
                  <p className={`text-lg font-bold ${
                    trendHistory.length > 0 && trendHistory.every(p => p.status === "Operational") 
                      ? "text-emerald-400" 
                      : "text-amber-400"
                  }`}>
                    {trendHistory.length > 0 && trendHistory.every(p => p.status === "Operational") ? "100%" : "Degraded"}
                  </p>
                </div>
                <div>
                  <p className="text-[10px] uppercase text-slate-600 tracking-wide">Avg Block Rate</p>
                  <p className="text-lg font-bold text-emerald-400 tabular-nums">
                    {trendHistory.length > 0 
                      ? (trendHistory[trendHistory.length - 1].blocked / Math.max(trendHistory.length, 1)).toFixed(1)
                      : "—"
                    }/poll
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Terminal Section */}
        <div className="mt-10">
          <div className="flex items-center justify-between rounded-t-xl border border-slate-800 bg-slate-900/50 px-4 py-2">
            <div className="flex items-center gap-2">
              <Terminal className="h-4 w-4 text-slate-400" />
              <span className="text-[10px] font-mono text-slate-400">verirag-telemetry --stream</span>
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
      </main>
    </div>
  );
};

// ── Session Uptime Live Counter ────────────────────────────────────────
function SessionUptime({ start }) {
  const [elapsed, setElapsed] = useState("");
  useEffect(() => {
    const tick = () => {
      const diff = Math.floor((Date.now() - start.getTime()) / 1000);
      const h = Math.floor(diff / 3600);
      const m = Math.floor((diff % 3600) / 60);
      const s = diff % 60;
      setElapsed(`${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [start]);
  return <>{elapsed}</>;
}

export default Monitoring;