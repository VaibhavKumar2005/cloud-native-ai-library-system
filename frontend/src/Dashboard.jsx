import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Progress } from "@/components/ui/progress"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Shield, Upload, MessageSquare, Activity, FileText, BarChart3, Cpu, Database, Lock, Zap, BrainCircuit, TrendingUp } from "lucide-react"
import axios from 'axios'

// ── Animated Radial Gauge ───────────────────────────────────────────────
function FaithfulnessGauge({ score, size = 160 }) {
  const radius = 45
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (score * circumference)
  const pct = (score * 100).toFixed(0)
  const color = score >= 0.7 ? '#10b981' : score >= 0.5 ? '#f59e0b' : '#ef4444'

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90 gauge-glow">
        {/* Background ring */}
        <circle cx="50" cy="50" r={radius} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="8" />
        {/* Animated foreground ring */}
        <circle
          cx="50" cy="50" r={radius}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="gauge-ring"
          style={{ transition: 'stroke-dashoffset 1.5s cubic-bezier(0.4, 0, 0.2, 1), stroke 0.5s' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-black tabular-nums" style={{ color }}>{pct}</span>
        <span className="text-[9px] font-mono uppercase tracking-widest text-slate-500 mt-0.5">Faithfulness</span>
      </div>
    </div>
  )
}

// ── Mini Area Chart for Score History ────────────────────────────────────
function AreaChart({ data, width = 280, height = 80 }) {
  if (data.length < 2) return null

  const max = Math.max(...data, 1)
  const min = Math.min(...data, 0)
  const range = max - min || 1
  const padY = 4

  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * width
    const y = height - padY - ((v - min) / range) * (height - 2 * padY)
    return `${x},${y}`
  })

  const areaPath = `M0,${height} L${points.join(' L')} L${width},${height} Z`
  const linePath = `M${points.join(' L')}`

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full area-chart-animate">
      <defs>
        <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#10b981" stopOpacity="0.3" />
          <stop offset="100%" stopColor="#10b981" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={areaPath} fill="url(#areaGrad)" />
      <path d={linePath} fill="none" stroke="#10b981" strokeWidth="2" strokeLinejoin="round" />
      {/* Latest point dot */}
      {data.length > 0 && (() => {
        const lastX = width
        const lastY = height - padY - ((data[data.length - 1] - min) / range) * (height - 2 * padY)
        return <circle cx={lastX} cy={lastY} r="3" fill="#10b981" className="animate-pulse" />
      })()}
    </svg>
  )
}

export default function Dashboard({ onLogout }) {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [selectedFile, setSelectedFile] = useState(null)
  const [chatHistory, setChatHistory] = useState(() => {
    // Load from localStorage on initial render only
    const saved = localStorage.getItem('verirag_query_history')
    return saved ? JSON.parse(saved) : []
  })
  const [documents, setDocuments] = useState([])
  const [systemMetrics, setSystemMetrics] = useState(null)

  const fetchDocuments = useCallback(async () => {
    try {
      const token = localStorage.getItem('access_token')
      const res = await axios.get('http://localhost:8000/api/documents/', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setDocuments(res.data)
    } catch (err) { console.error("Sync error", err) }
  }, [])

  const fetchSystemMetrics = useCallback(async () => {
    try {
      const token = localStorage.getItem('access_token')
      const res = await axios.get('http://localhost:8000/api/system-insights/', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setSystemMetrics(res.data)
    } catch { /* silent */ }
  }, [])

  useEffect(() => {
    // Initial fetch wrapped to avoid cascading render warnings
    const initialFetch = async () => {
      await Promise.all([fetchDocuments(), fetchSystemMetrics()])
    }
    initialFetch()
    
    const interval = setInterval(() => { 
      fetchDocuments()
      fetchSystemMetrics()
    }, 8000)
    return () => clearInterval(interval)
  }, [fetchDocuments, fetchSystemMetrics])

  const handleFileUpload = async () => {
    if (!selectedFile) return
    setUploading(true)
    const formData = new FormData()
    formData.append('file', selectedFile)
    formData.append('title', selectedFile.name)
    try {
      const token = localStorage.getItem('access_token')
      await axios.post('http://localhost:8000/api/documents/', formData, {
        headers: { Authorization: `Bearer ${token}` }
      })
      fetchDocuments()
      setSelectedFile(null)
    } catch (err) { console.error("Upload failed", err) }
    setUploading(false)
  }

  const handleQuery = async (e) => {
    e.preventDefault()
    if (!query) return
    setLoading(true)
    try {
      const token = localStorage.getItem('access_token')
      const res = await axios.post('http://localhost:8000/api/query/',
        { query },
        { headers: { Authorization: `Bearer ${token}` } }
      )
      const newEntry = { question: query, timestamp: new Date().toISOString(), ...res.data }
      const updated = [newEntry, ...chatHistory]
      setChatHistory(updated)
      localStorage.setItem('verirag_query_history', JSON.stringify(updated.slice(0, 100)))
      setQuery('')
    } catch (err) { console.error("AI Error", err) }
    setLoading(false)
  }

  // Score trend for area chart
  const scoreTrend = useMemo(() =>
    chatHistory.slice(0, 20).map(c => c.faithfulness_score || 0).reverse(),
    [chatHistory]
  )

  const latestScore = chatHistory.length > 0 ? chatHistory[0].faithfulness_score || 0 : 0
  const avgScore = chatHistory.length > 0
    ? chatHistory.reduce((a, c) => a + (c.faithfulness_score || 0), 0) / chatHistory.length
    : 0

  return (
    <div className="min-h-screen bg-[#040207] text-slate-50 font-sans relative overflow-hidden">
      {/* Ambient Background Orbs */}
      <div className="orb w-96 h-96 bg-indigo-600 top-[-10%] left-[-5%]" />
      <div className="orb w-80 h-80 bg-emerald-600 bottom-[10%] right-[-5%]" style={{ animationDelay: '7s' }} />
      <div className="orb w-64 h-64 bg-violet-600 top-[40%] left-[60%]" style={{ animationDelay: '14s' }} />

      {/* ── Top Navigation ─────────────────────────────────────────────── */}
      <nav className="sticky top-0 z-50 border-b border-white/5 bg-[#040207]/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-indigo-500/10 p-2.5 border border-indigo-500/20">
              <Shield className="h-5 w-5 text-indigo-400" />
            </div>
            <div>
              <span className="font-bold text-lg tracking-tight">VeriRAG</span>
              <p className="text-[9px] font-mono uppercase tracking-[0.2em] text-slate-600">AI Librarian</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button onClick={() => navigate('/monitoring')} variant="ghost" size="sm" className="text-slate-400 hover:text-white hover:bg-white/5 gap-2">
              <Activity className="w-4 h-4" /> Mission Control
            </Button>
            <Button onClick={() => navigate('/analytics')} variant="ghost" size="sm" className="text-slate-400 hover:text-white hover:bg-white/5 gap-2">
              <BarChart3 className="w-4 h-4" /> Analytics
            </Button>
            <div className="w-px h-6 bg-white/10 mx-2" />
            <Button onClick={onLogout} variant="ghost" size="sm" className="text-slate-500 hover:text-red-400 hover:bg-red-500/5">
              Logout
            </Button>
          </div>
        </div>
      </nav>

      <main className="relative z-10 mx-auto max-w-7xl px-6 py-8">
        {/* ── BENTO GRID ─────────────────────────────────────────────── */}
        <div className="grid grid-cols-12 gap-4 auto-rows-min">

          {/* ── Cell 1: Faithfulness Gauge (spans 4 cols) ─────────────── */}
          <div className="col-span-12 md:col-span-4 bento-card p-6 flex flex-col items-center justify-center min-h-[280px]">
            <p className="text-[10px] font-mono uppercase tracking-widest text-slate-500 mb-4">Critic Agent Score</p>
            <FaithfulnessGauge score={latestScore} size={180} />
            <div className="mt-4 flex gap-6 text-center">
              <div>
                <p className="text-xs text-slate-500">Average</p>
                <p className="text-lg font-bold text-emerald-400 tabular-nums">{(avgScore * 100).toFixed(0)}%</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Queries</p>
                <p className="text-lg font-bold text-indigo-400 tabular-nums">{chatHistory.length}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Verified</p>
                <p className="text-lg font-bold text-blue-400 tabular-nums">
                  {chatHistory.filter(c => c.verification_passed).length}
                </p>
              </div>
            </div>
          </div>

          {/* ── Cell 2: Confidence Trend (spans 5 cols) ───────────────── */}
          <div className="col-span-12 md:col-span-5 bento-card p-6 min-h-[280px] flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <p className="text-[10px] font-mono uppercase tracking-widest text-slate-500 flex items-center gap-2">
                <TrendingUp className="h-3 w-3 text-emerald-500" /> Faithfulness Trend
              </p>
              <span className="text-[9px] font-mono text-slate-600">{scoreTrend.length} pts</span>
            </div>
            <div className="flex-1 flex items-end">
              {scoreTrend.length >= 2 ? (
                <AreaChart data={scoreTrend} width={400} height={160} />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-slate-600 text-xs italic">
                  Submit queries to build the trend chart...
                </div>
              )}
            </div>
          </div>

          {/* ── Cell 3: Infrastructure Status (spans 3 cols) ──────────── */}
          <div className="col-span-12 md:col-span-3 bento-card p-6 min-h-[280px] flex flex-col justify-between">
            <p className="text-[10px] font-mono uppercase tracking-widest text-slate-500 mb-4">Infrastructure</p>
            <div className="space-y-4 flex-1">
              {[
                { icon: Database, label: 'PostgreSQL', status: systemMetrics?.infrastructure?.database || '—', ok: systemMetrics?.infrastructure?.database === 'Connected' },
                { icon: Zap, label: 'Redis', status: 'Active', ok: true },
                { icon: Lock, label: 'Vault', status: systemMetrics?.infrastructure?.vault || '—', ok: systemMetrics?.infrastructure?.vault === 'Unsealed' },
                { icon: BrainCircuit, label: 'LLM Engine', status: systemMetrics?.metrics?.active_model?.split(' ')[0] || '—', ok: true },
              ].map(({ icon, label, status, ok }) => (
                <div key={label} className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    {icon && React.createElement(icon, { className: "h-4 w-4 text-slate-600" })}
                    <span className="text-xs text-slate-400">{label}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className={`h-1.5 w-1.5 rounded-full ${ok ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`} />
                    <span className={`text-[10px] font-mono ${ok ? 'text-emerald-400' : 'text-red-400'}`}>{status}</span>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-4 pt-4 border-t border-white/5">
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-slate-600">System Status</span>
                <span className={`text-[10px] font-bold ${systemMetrics?.status === 'Operational' ? 'text-emerald-400' : 'text-amber-400'}`}>
                  {systemMetrics?.status?.toUpperCase() || 'LOADING'}
                </span>
              </div>
            </div>
          </div>

          {/* ── Cell 4: Document Library (spans 4 cols) ───────────────── */}
          <div className="col-span-12 md:col-span-4 bento-card p-6 max-h-[400px] flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <p className="text-[10px] font-mono uppercase tracking-widest text-slate-500">Document Library</p>
              <Dialog>
                <DialogTrigger asChild>
                  <Button size="sm" className="h-7 text-xs bg-indigo-600 hover:bg-indigo-500 rounded-lg">
                    <Upload className="w-3 h-3 mr-1.5" /> Upload
                  </Button>
                </DialogTrigger>
                <DialogContent className="bg-[#0a0a12] border-white/10 text-white backdrop-blur-xl">
                  <DialogHeader><DialogTitle>Ingest New Document</DialogTitle></DialogHeader>
                  <div className="py-4 flex flex-col gap-4">
                    <Input type="file" accept=".pdf"
                      onChange={(e) => setSelectedFile(e.target.files[0])}
                      className="bg-white/5 border-white/10" />
                    {selectedFile && (
                      <Button onClick={handleFileUpload} disabled={uploading}
                        className="w-full bg-emerald-600 hover:bg-emerald-500 text-white">
                        {uploading ? "Indexing..." : "Upload to Library"}
                      </Button>
                    )}
                    {uploading && <p className="text-xs text-indigo-400 animate-pulse text-center">Processing vector embeddings...</p>}
                  </div>
                </DialogContent>
              </Dialog>
            </div>
            <div className="flex-1 overflow-y-auto space-y-2 pr-1">
              {documents.length === 0 && (
                <div className="flex flex-col items-center justify-center h-full text-slate-600">
                  <FileText className="w-8 h-8 mb-2 opacity-30" />
                  <p className="text-xs">No documents yet</p>
                </div>
              )}
              {documents.map(doc => (
                <div key={doc.id} className="flex items-center gap-3 p-3 rounded-xl bg-white/[0.02] border border-white/5 hover:bg-white/[0.04] transition-colors">
                  <FileText className="w-4 h-4 text-indigo-400 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium truncate">{doc.title}</p>
                    <p className={`text-[9px] mt-0.5 font-bold uppercase tracking-wider ${doc.processed ? 'text-emerald-500' : 'text-amber-500'}`}>
                      {doc.processed ? '● Indexed' : '○ Processing'}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* ── Cell 5: AI Chat (spans 8 cols — main area) ────────────── */}
          <div className="col-span-12 md:col-span-8 bento-card flex flex-col min-h-[400px] max-h-[600px]">
            {/* Chat Messages */}
            <div className="flex-1 p-6 overflow-y-auto space-y-6">
              {chatHistory.length === 0 && (
                <div className="h-full flex flex-col items-center justify-center text-slate-600">
                  <MessageSquare className="w-10 h-10 mb-3 opacity-20" />
                  <p className="text-sm italic">Ask a question. Responses are verified against your library.</p>
                </div>
              )}
              {chatHistory.map((chat, i) => (
                <div key={i} className="space-y-3">
                  {/* User message */}
                  <div className="flex justify-end">
                    <div className="bg-indigo-600/80 backdrop-blur-sm px-4 py-2.5 rounded-2xl rounded-tr-sm max-w-md text-sm">
                      {chat.question}
                    </div>
                  </div>
                  {/* AI response */}
                  <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-5 space-y-3">
                    <div className="flex items-center gap-2 text-[9px] font-mono uppercase tracking-widest text-emerald-500">
                      <Shield className="w-3 h-3" />
                      {chat.verification_passed ? 'Integrity Verified' : 'Low Confidence — Flagged'}
                      <span className="ml-auto text-slate-600">{chat.model_used}</span>
                    </div>
                    <p className="text-sm text-slate-200 leading-relaxed">{chat.answer}</p>

                    {/* Inline faithfulness bar */}
                    <div className="flex items-center gap-3 pt-2 border-t border-white/5">
                      <span className="text-[10px] font-mono text-slate-500">Faithfulness</span>
                      <Progress value={(chat.faithfulness_score || 0) * 100} className="h-1.5 flex-1 bg-white/5" />
                      <span className="text-xs font-bold tabular-nums text-emerald-400">
                        {((chat.faithfulness_score || 0) * 100).toFixed(0)}%
                      </span>
                    </div>

                    {chat.source_citation && chat.source_citation !== "None" && (
                      <div className="p-3 bg-white/[0.02] rounded-xl border border-white/5 text-[11px] italic text-slate-400">
                        &ldquo;{chat.source_citation}&rdquo;
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Chat Input */}
            <div className="p-5 border-t border-white/5">
              <form onSubmit={handleQuery} className="flex gap-3">
                <Input
                  placeholder="Ask VeriRAG Librarian..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="bg-white/5 border-white/10 h-12 text-slate-100 placeholder:text-slate-600 rounded-xl"
                />
                <Button type="submit" disabled={loading} className="h-12 px-6 bg-indigo-600 hover:bg-indigo-500 rounded-xl">
                  {loading ?
                    <span className="flex items-center gap-2"><Cpu className="w-4 h-4 animate-spin" /> Verifying</span>
                    : "Query AI"}
                </Button>
              </form>
            </div>
          </div>

          {/* ── Cell 6: Metric Cards Row (spans full width) ──────────── */}
          <div className="col-span-12 grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: 'Hallucinations Blocked', value: systemMetrics?.metrics?.hallucinations_prevented ?? '—', color: 'text-amber-400', icon: Shield },
              { label: 'Failover Recoveries', value: systemMetrics?.metrics?.failover_recoveries ?? '—', color: 'text-blue-400', icon: Zap },
              { label: 'Total Queries', value: systemMetrics?.metrics?.total_queries ?? '—', color: 'text-violet-400', icon: BrainCircuit },
              { label: 'Docs Ingested', value: systemMetrics?.metrics?.documents_ingested ?? documents.length, color: 'text-emerald-400', icon: FileText },
            ].map(({ label, value, color, icon }) => (
              <div key={label} className="bento-card p-5 flex items-center gap-4">
                <div className="rounded-xl bg-white/[0.03] p-3 border border-white/5">
                  {icon && React.createElement(icon, { className: `h-5 w-5 ${color}` })}
                </div>
                <div>
                  <p className={`text-2xl font-black tabular-nums ${color}`}>{value}</p>
                  <p className="text-[9px] font-mono uppercase tracking-wider text-slate-600 mt-0.5">{label}</p>
                </div>
              </div>
            ))}
          </div>

        </div>
      </main>
    </div>
  )
}
