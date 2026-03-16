import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Progress } from "@/components/ui/progress"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import {
  Shield, Upload, MessageSquare, FileText,
  Cpu, Database, Lock, Zap, BrainCircuit, TrendingUp, ArrowUpRight,
  ArrowDownRight, Sparkles, Clock, Search
} from "lucide-react"
import api from '@/lib/api'
import AppShell from '@/components/AppShell'

/* ═══════════════════════════════════════════════════════════════════════════
   MICRO-COMPONENTS — Premium UI building blocks
   ═══════════════════════════════════════════════════════════════════════════ */

// ── Animated Number Counter ─────────────────────────────────────────────
function AnimatedCounter({ value, duration = 1200, suffix = '', prefix = '' }) {
  const [display, setDisplay] = useState(0)
  const prevValue = useRef(0)

  useEffect(() => {
    if (typeof value !== 'number' || isNaN(value)) return
    const start = prevValue.current
    const end = value
    const startTime = performance.now()

    const animate = (now) => {
      const elapsed = now - startTime
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setDisplay(Math.round(start + (end - start) * eased))
      if (progress < 1) requestAnimationFrame(animate)
    }
    requestAnimationFrame(animate)
    prevValue.current = end
  }, [value, duration])

  if (typeof value !== 'number' || isNaN(value)) return <span>—</span>
  return <span>{prefix}{display}{suffix}</span>
}

// ── Skeleton Loader ─────────────────────────────────────────────────────
function Skeleton({ className = '' }) {
  return (
    <div className={`skeleton-pulse rounded-lg bg-white/[0.04] ${className}`} />
  )
}

// ── Status Dot with ping animation ──────────────────────────────────────
function StatusDot({ ok }) {
  return (
    <span className="relative flex h-2 w-2">
      {ok && <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />}
      <span className={`relative inline-flex h-2 w-2 rounded-full ${ok ? 'bg-emerald-500' : 'bg-red-500'}`} />
    </span>
  )
}

// ── Trend Badge (↑12% / ↓5%) ────────────────────────────────────────────
function TrendBadge({ current, previous }) {
  if (previous === 0 || current === previous) return null
  const up = current > previous
  const pct = Math.abs(((current - previous) / previous) * 100).toFixed(0)
  return (
    <span className={`inline-flex items-center gap-0.5 text-[10px] font-semibold tracking-tight px-1.5 py-0.5 rounded-full
      ${up ? 'text-emerald-400 bg-emerald-500/10' : 'text-red-400 bg-red-500/10'}`}>
      {up ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
      {pct}%
    </span>
  )
}

// ── Bento Card with spotlight mouse-follow effect ───────────────────────
function BentoCard({ children, className = '', span = '', style }) {
  const cardRef = useRef(null)

  const handleMouse = (e) => {
    const card = cardRef.current
    if (!card) return
    const rect = card.getBoundingClientRect()
    card.style.setProperty('--mx', `${e.clientX - rect.left}px`)
    card.style.setProperty('--my', `${e.clientY - rect.top}px`)
  }

  return (
    <div
      ref={cardRef}
      onMouseMove={handleMouse}
      className={`bento-card spotlight-card ${span} ${className}`}
      style={style}
    >
      {children}
    </div>
  )
}

// ── Animated Radial Gauge ───────────────────────────────────────────────
function FaithfulnessGauge({ score, size = 160 }) {
  const radius = 45
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (score * circumference)
  const pct = (score * 100).toFixed(0)
  const color = score >= 0.7 ? '#10b981' : score >= 0.5 ? '#f59e0b' : '#ef4444'
  const glowColor = score >= 0.7 ? 'rgba(16,185,129,0.35)' : score >= 0.5 ? 'rgba(245,158,11,0.35)' : 'rgba(239,68,68,0.35)'

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
        <circle cx="50" cy="50" r={radius} fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth="10" />
        <circle
          cx="50" cy="50" r={radius}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="gauge-ring"
          style={{
            transition: 'stroke-dashoffset 1.8s cubic-bezier(0.4, 0, 0.2, 1), stroke 0.5s',
            filter: `drop-shadow(0 0 8px ${glowColor})`
          }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-4xl font-black tabular-nums tracking-tight" style={{ color }}>{pct}</span>
        <span className="text-[8px] font-mono uppercase tracking-[0.25em] text-slate-500 mt-1">Faithfulness</span>
      </div>
    </div>
  )
}

// ── Mini Area Chart ─────────────────────────────────────────────────────
function AreaChart({ data, width = 320, height = 100, color = '#10b981' }) {
  if (data.length < 2) return null

  const max = Math.max(...data, 1)
  const min = Math.min(...data, 0)
  const range = max - min || 1
  const padY = 6

  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * width
    const y = height - padY - ((v - min) / range) * (height - 2 * padY)
    return `${x},${y}`
  })

  const areaPath = `M0,${height} L${points.join(' L')} L${width},${height} Z`
  const linePath = `M${points.join(' L')}`
  const lastX = width
  const lastY = height - padY - ((data[data.length - 1] - min) / range) * (height - 2 * padY)

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full area-chart-animate">
      <defs>
        <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.25" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={areaPath} fill="url(#chartGrad)" />
      <path d={linePath} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />
      <circle cx={lastX} cy={lastY} r="4" fill={color} className="animate-pulse" />
      <circle cx={lastX} cy={lastY} r="8" fill={color} fillOpacity="0.2" />
    </svg>
  )
}

// ── Mini Sparkline (for metric cards) ───────────────────────────────────
function Sparkline({ data = [], width = 60, height = 24, color = '#818cf8' }) {
  if (data.length < 2) return null
  const max = Math.max(...data)
  const min = Math.min(...data)
  const range = max - min || 1
  const points = data.map((v, i) =>
    `${(i / (data.length - 1)) * width},${height - ((v - min) / range) * height}`
  ).join(' L')
  return (
    <svg width={width} height={height} className="opacity-60">
      <path d={`M${points}`} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  )
}


/* ═══════════════════════════════════════════════════════════════════════════
   MAIN DASHBOARD
   ═══════════════════════════════════════════════════════════════════════════ */

export default function Dashboard({ onLogout }) {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [selectedFile, setSelectedFile] = useState(null)
  const [uploadError, setUploadError] = useState('')
  const [chatHistory, setChatHistory] = useState(() => {
    const saved = localStorage.getItem('verirag_query_history')
    return saved ? JSON.parse(saved) : []
  })
  const [documents, setDocuments] = useState([])
  const [systemMetrics, setSystemMetrics] = useState(null)
  const [metricsLoaded, setMetricsLoaded] = useState(false)
  const [selectedChatIndex, setSelectedChatIndex] = useState(0)
  const [queryError, setQueryError] = useState('')
  const chatEndRef = useRef(null)

  const getDocumentStatusMeta = useCallback((doc) => {
    const status = doc.status || (doc.processed ? 'indexed' : 'queued')
    if (status === 'indexed') {
      return {
        label: 'Indexed',
        tone: 'text-emerald-500',
        iconTone: 'text-emerald-400',
        bgTone: 'bg-emerald-500/10',
      }
    }
    if (status === 'failed') {
      return {
        label: 'Failed',
        tone: 'text-red-500',
        iconTone: 'text-red-400',
        bgTone: 'bg-red-500/10',
      }
    }
    if (status === 'indexing') {
      return {
        label: `${doc.progress_percent || 0}% Indexed`,
        tone: 'text-amber-500',
        iconTone: 'text-amber-400',
        bgTone: 'bg-amber-500/10',
      }
    }
    return {
      label: 'Queued',
      tone: 'text-indigo-500',
      iconTone: 'text-indigo-400',
      bgTone: 'bg-indigo-500/10',
    }
  }, [])

  const indexedDocuments = useMemo(
    () => documents.filter((doc) => doc.status === 'indexed' || doc.processed),
    [documents]
  )

  const selectedChat = chatHistory[selectedChatIndex] || chatHistory[0] || null
  const selectedEvidenceItems = useMemo(() => {
    if (!selectedChat) return []
    if (Array.isArray(selectedChat.evidence_items) && selectedChat.evidence_items.length > 0) {
      return selectedChat.evidence_items
    }
    const raw = selectedChat.source_citation
    if (!raw || raw === 'None') return []
    return raw
      .split(/(?:\s*\|\s*|;\s*|\n+)/)
      .map((item, idx) => ({
        source_index: idx + 1,
        citation: item.trim(),
      }))
      .filter((item) => item.citation)
  }, [selectedChat])

  const selectedEvidenceSummary = useMemo(
    () =>
      selectedEvidenceItems
        .map((item) => item.citation || item)
        .filter(Boolean)
    ,
    [selectedEvidenceItems]
  )

  // ── Data Fetching ───────────────────────────────────────────────────
  const fetchDocuments = useCallback(async () => {
    try {
      const res = await api.get('/api/documents/')
      setDocuments(res.data)
    } catch (err) { console.error("Sync error", err) }
  }, [])

  const fetchSystemMetrics = useCallback(async () => {
    try {
      const res = await api.get('/api/system-insights/')
      setSystemMetrics(res.data)
      setMetricsLoaded(true)
    } catch { /* silent */ }
  }, [])

  useEffect(() => {
    const init = async () => {
      await Promise.all([fetchDocuments(), fetchSystemMetrics()])
    }
    init()
    const interval = setInterval(() => {
      fetchDocuments()
      fetchSystemMetrics()
    }, 8000)
    return () => clearInterval(interval)
  }, [fetchDocuments, fetchSystemMetrics])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatHistory])

  // ── Handlers ────────────────────────────────────────────────────────
  const handleFileUpload = async () => {
    if (!selectedFile) return
    if ((selectedFile.type && selectedFile.type !== 'application/pdf') || !selectedFile.name.toLowerCase().endsWith('.pdf')) {
      setUploadError('Only PDF files are supported.')
      return
    }
    setUploading(true)
    setUploadError('')
    setUploadProgress(0)
    
    const formData = new FormData()
    formData.append('file', selectedFile)
    formData.append('title', selectedFile.name)
    
    return new Promise((resolve) => {
      const xhr = new XMLHttpRequest()
      
      // Track upload progress
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          const progress = Math.round((e.loaded / e.total) * 100)
          setUploadProgress(progress)
        }
      })
      
      // Handle completion
      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          // Success
          setUploadProgress(100)
          fetchDocuments()
          setSelectedFile(null)
          setUploadError('')
          setTimeout(() => {
            setUploading(false)
            setUploadProgress(0)
          }, 800)
        } else {
          // Server error
          const response = JSON.parse(xhr.responseText)
          const message = response?.detail || response?.error || `Upload failed (${xhr.status})`
          setUploadError(`❌ ${message}`)
          setUploading(false)
          setUploadProgress(0)
        }
        resolve()
      })
      
      // Handle network errors
      xhr.addEventListener('error', () => {
        setUploadError('❌ Network error. Check your connection.')
        setUploading(false)
        setUploadProgress(0)
        resolve()
      })
      
      xhr.addEventListener('abort', () => {
        setUploadError('❌ Upload cancelled')
        setUploading(false)
        setUploadProgress(0)
        resolve()
      })
      
      // Set auth header
      const token = localStorage.getItem('auth_token')
      if (token) {
        xhr.setRequestHeader('Authorization', `Bearer ${token}`)
      }
      
      xhr.open('POST', '/api/documents/')
      xhr.send(formData)
    })
  }

  const handleQuery = async (e) => {
    e.preventDefault()
    if (!query.trim()) return
    setQueryError('')
    setLoading(true)
    try {
      const res = await api.post('/api/query/', { query })
      const newEntry = { question: query, timestamp: new Date().toISOString(), ...res.data }
      const updated = [newEntry, ...chatHistory]
      setChatHistory(updated)
      setSelectedChatIndex(0)
      localStorage.setItem('verirag_query_history', JSON.stringify(updated.slice(0, 100)))
      setQuery('')
    } catch (err) {
      console.error("AI Error", err)
      const serverData = err?.response?.data || {}
      
      // Extract detailed error message
      let errorMessage = 'Query failed. Please try again.'
      if (serverData.detail) {
        errorMessage = serverData.detail
      } else if (serverData.error) {
        errorMessage = serverData.error
      } else if (err?.message === 'Network Error') {
        errorMessage = 'Network error. Check your connection.'
      } else if (err?.response?.status === 401) {
        errorMessage = 'Session expired. Please log in again.'
        setTimeout(() => window.location.href = '/login', 1500)
      } else if (err?.response?.status === 429) {
        errorMessage = 'Too many requests. Please wait a moment.'
      }
      
      setQueryError(`❌ ${errorMessage}`)
    }
    setLoading(false)
  }

  // ── Derived Data ────────────────────────────────────────────────────
  const scoreTrend = useMemo(() =>
    chatHistory.slice(0, 20).map(c => c.faithfulness_score || 0).reverse(),
    [chatHistory]
  )

  const latestScore = chatHistory.length > 0 ? chatHistory[0].faithfulness_score || 0 : 0
  const avgScore = chatHistory.length > 0
    ? chatHistory.reduce((a, c) => a + (c.faithfulness_score || 0), 0) / chatHistory.length
    : 0
  const prevAvg = chatHistory.length > 1
    ? chatHistory.slice(1).reduce((a, c) => a + (c.faithfulness_score || 0), 0) / (chatHistory.length - 1)
    : 0

  const verifiedRate = chatHistory.length > 0
    ? chatHistory.filter(c => c.verification_passed).length / chatHistory.length
    : 0

  const metricCards = [
    { label: 'Hallucinations Blocked', value: systemMetrics?.metrics?.hallucinations_prevented, icon: Shield, color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/20', sparkColor: '#f59e0b' },
    { label: 'Failover Recoveries', value: systemMetrics?.metrics?.failover_recoveries, icon: Zap, color: 'text-blue-400', bg: 'bg-blue-500/10', border: 'border-blue-500/20', sparkColor: '#3b82f6' },
    { label: 'Total Queries', value: systemMetrics?.metrics?.total_queries, icon: BrainCircuit, color: 'text-violet-400', bg: 'bg-violet-500/10', border: 'border-violet-500/20', sparkColor: '#8b5cf6' },
    { label: 'Docs Ingested', value: systemMetrics?.metrics?.documents_ingested ?? documents.length, icon: FileText, color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20', sparkColor: '#10b981' },
  ]

  /* ═════════════════════════════════════════════════════════════════════
     RENDER
     ═════════════════════════════════════════════════════════════════════ */
  return (
    <AppShell
      title="Workspace"
      subtitle="Real-time verification metrics, document ingestion, and evidence-backed chat."
      status={systemMetrics?.status?.toUpperCase() || 'CONNECTING'}
      headerRight={
        <Button onClick={onLogout} variant="ghost" size="sm" className="text-slate-500 hover:text-red-400 hover:bg-red-500/5 rounded-xl text-xs">
          Logout
        </Button>
      }
    >
        {/* ── BENTO GRID ─────────────────────────────────────────────── */}
        <div className="grid grid-cols-12 gap-3.5 auto-rows-min">

          {/* ── Cell 1: Faithfulness Gauge (4 cols) ──────────────────── */}
          <BentoCard span="col-span-12 md:col-span-4" className="p-6 flex flex-col items-center justify-center min-h-[300px]">
            <div className="flex items-center gap-2 mb-5">
              <Sparkles className="h-3.5 w-3.5 text-indigo-400" />
              <p className="text-[10px] font-mono uppercase tracking-widest text-slate-500">Critic Agent Score</p>
            </div>
            <FaithfulnessGauge score={latestScore} size={190} />
            <div className="mt-5 grid grid-cols-3 gap-4 w-full max-w-[240px]">
              <div className="text-center">
                <p className="text-[10px] text-slate-500 mb-0.5">Average</p>
                <p className="text-lg font-bold text-emerald-400 tabular-nums">
                  <AnimatedCounter value={Math.round(avgScore * 100)} suffix="%" />
                </p>
                <TrendBadge current={avgScore} previous={prevAvg} />
              </div>
              <div className="text-center">
                <p className="text-[10px] text-slate-500 mb-0.5">Queries</p>
                <p className="text-lg font-bold text-indigo-400 tabular-nums">
                  <AnimatedCounter value={chatHistory.length} />
                </p>
              </div>
              <div className="text-center">
                <p className="text-[10px] text-slate-500 mb-0.5">Verified</p>
                <p className="text-lg font-bold text-blue-400 tabular-nums">
                  <AnimatedCounter value={Math.round(verifiedRate * 100)} suffix="%" />
                </p>
              </div>
            </div>
          </BentoCard>

          {/* ── Cell 2: Faithfulness Trend (5 cols) ──────────────────── */}
          <BentoCard span="col-span-12 md:col-span-5" className="p-6 min-h-[300px] flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                  <TrendingUp className="h-3.5 w-3.5 text-emerald-500" />
                </div>
                <p className="text-xs font-medium text-slate-400">Faithfulness Trend</p>
              </div>
              <span className="text-[9px] font-mono text-slate-600 bg-white/[0.03] px-2 py-0.5 rounded-full">
                {scoreTrend.length} pts
              </span>
            </div>
            <div className="flex-1 flex items-end">
              {scoreTrend.length >= 2 ? (
                <AreaChart data={scoreTrend} width={400} height={160} />
              ) : (
                <div className="w-full h-full flex flex-col items-center justify-center text-slate-600 gap-2">
                  <TrendingUp className="w-8 h-8 opacity-20" />
                  <p className="text-xs italic">Submit queries to build the trend chart...</p>
                </div>
              )}
            </div>
          </BentoCard>

          {/* ── Cell 3: Infrastructure Status (3 cols) ───────────────── */}
          <BentoCard span="col-span-12 md:col-span-3" className="p-5 min-h-[300px] flex flex-col">
            <div className="flex items-center gap-2 mb-4">
              <div className="p-1.5 rounded-lg bg-violet-500/10 border border-violet-500/20">
                <Cpu className="h-3.5 w-3.5 text-violet-400" />
              </div>
              <p className="text-xs font-medium text-slate-400">Infrastructure</p>
            </div>
            <div className="space-y-3 flex-1">
              {!metricsLoaded ? (
                <>
                  <Skeleton className="h-8 w-full" />
                  <Skeleton className="h-8 w-full" />
                  <Skeleton className="h-8 w-full" />
                  <Skeleton className="h-8 w-full" />
                </>
              ) : [
                { icon: Database, label: 'PostgreSQL', status: systemMetrics?.infrastructure?.database || '—', ok: systemMetrics?.infrastructure?.database === 'Connected' },
                { icon: Zap, label: 'Redis', status: 'Active', ok: true },
                { icon: Lock, label: 'Vault', status: systemMetrics?.infrastructure?.vault || '—', ok: systemMetrics?.infrastructure?.vault === 'Unsealed' },
                { icon: BrainCircuit, label: 'LLM Engine', status: systemMetrics?.metrics?.active_model?.split(' ')[0] || '—', ok: true },
              ].map(({ icon, label, status, ok }) => (
                <div key={label} className="flex items-center justify-between py-1.5 group">
                  <div className="flex items-center gap-2.5">
                    {React.createElement(icon, { className: "h-3.5 w-3.5 text-slate-600 group-hover:text-slate-400 transition-colors" })}
                    <span className="text-xs text-slate-400">{label}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusDot ok={ok} />
                    <span className={`text-[10px] font-mono ${ok ? 'text-emerald-400' : 'text-red-400'}`}>{status}</span>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-3 pt-3 border-t border-white/5">
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-slate-600">Uptime Score</span>
                <div className="flex items-center gap-2">
                  <Progress value={systemMetrics?.infrastructure?.uptime_score ?? 0} className="h-1 w-16 bg-white/5" />
                  <span className="text-[10px] font-mono text-emerald-400">{systemMetrics?.infrastructure?.uptime_score ?? '—'}%</span>
                </div>
              </div>
            </div>
          </BentoCard>

          {/* ── Cell 4: Document Library (4 cols) ────────────────────── */}
          <BentoCard span="col-span-12 md:col-span-4" className="p-5 max-h-[420px] flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20">
                  <FileText className="h-3.5 w-3.5 text-indigo-400" />
                </div>
                <p className="text-xs font-medium text-slate-400">Document Library</p>
                <span className="text-[9px] font-mono text-slate-600 bg-white/[0.03] px-1.5 py-0.5 rounded-full ml-1">{documents.length}</span>
              </div>
              <Dialog>
                <DialogTrigger asChild>
                  <Button size="sm" className="h-7 text-[10px] bg-indigo-600 hover:bg-indigo-500 rounded-lg gap-1.5 font-medium">
                    <Upload className="w-3 h-3" /> Upload
                  </Button>
                </DialogTrigger>
                <DialogContent className="bg-[#0a0a14] border-white/10 text-white backdrop-blur-2xl">
                  <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-indigo-400" /> Ingest New Document
                    </DialogTitle>
                  </DialogHeader>
                  <div className="py-4 flex flex-col gap-4">
                    <Input 
                      type="file" 
                      accept=".pdf" 
                      onChange={(e) => {
                        setSelectedFile(e.target.files[0])
                        setUploadError('')
                      }} 
                      className="bg-white/5 border-white/10 rounded-xl"
                      disabled={uploading}
                    />
                    
                    {/* Error Message */}
                    {uploadError && (
                      <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2 flex items-start gap-2">
                        <span className="mt-0.5">⚠️</span>
                        <span>{uploadError}</span>
                      </div>
                    )}
                    
                    {/* Upload Progress Bar */}
                    {uploading && (
                      <div className="space-y-2">
                        <div className="flex items-center justify-between text-xs text-slate-400">
                          <span>Uploading... {uploadProgress}%</span>
                          <span className="text-emerald-400 font-mono">{uploadProgress}%</span>
                        </div>
                        <Progress value={uploadProgress} className="h-2 bg-white/5" />
                      </div>
                    )}
                    
                    {/* Upload Button */}
                    {selectedFile && !uploading && (
                      <div className="space-y-2">
                        <p className="text-xs text-slate-400">📄 {selectedFile.name}</p>
                        <Button 
                          onClick={handleFileUpload} 
                          className="w-full bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl"
                        >
                          <Upload className="w-3.5 h-3.5 mr-2" />
                          Upload to Library
                        </Button>
                      </div>
                    )}
                    
                    {/* Success State */}
                    {uploading && uploadProgress === 100 && (
                      <div className="text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-lg px-3 py-2 flex items-center gap-2 animate-pulse">
                        <span>✓</span>
                        <span>Upload complete! Processing document...</span>
                      </div>
                    )}
                  </div>
                </DialogContent>
              </Dialog>
            </div>
            <div className="flex-1 overflow-y-auto space-y-1.5 pr-1 custom-scrollbar">
              {documents.length === 0 && (
                <div className="flex flex-col items-center justify-center h-full text-slate-600 gap-2">
                  <FileText className="w-8 h-8 opacity-20" />
                  <p className="text-xs">No documents yet</p>
                  <p className="text-[10px] text-slate-700">Upload a PDF to get started</p>
                </div>
              )}
              {documents.map((doc, idx) => {
                const statusMeta = getDocumentStatusMeta(doc)
                return (
                <div key={doc.id}
                  className="flex items-center gap-3 p-3 rounded-xl bg-white/[0.02] border border-white/5 hover:bg-white/[0.04] hover:border-white/10 transition-all duration-200 group stagger-in"
                  style={{ animationDelay: `${idx * 50}ms` }}>
                  <div className={`p-2 rounded-lg ${statusMeta.bgTone}`}>
                    <FileText className={`w-3.5 h-3.5 ${statusMeta.iconTone}`} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium truncate group-hover:text-white transition-colors">{doc.title}</p>
                    <p className={`text-[9px] mt-0.5 font-bold uppercase tracking-wider ${statusMeta.tone}`}>
                      {statusMeta.label}
                    </p>
                    <div className="mt-1 flex items-center gap-2 text-[9px] text-slate-600">
                      <Clock className="w-3 h-3" />
                      <span>{new Date(doc.uploaded_at).toLocaleString()}</span>
                    </div>
                    {doc.status === 'indexing' && (
                      <div className="mt-2">
                        <Progress value={doc.progress_percent || 0} className="h-1 bg-white/5" />
                        <p className="mt-1 text-[9px] text-slate-600">
                          {doc.processed_chunks || 0} / {doc.total_chunks || 0} chunks
                        </p>
                      </div>
                    )}
                    {doc.status === 'failed' && doc.last_error && (
                      <p className="mt-1 text-[10px] text-red-400 truncate">
                        {doc.last_error}
                      </p>
                    )}
                  </div>
                </div>
              )})}
            </div>
          </BentoCard>

          {/* ── Cell 5: AI Chat (8 cols) ─────────────────────────────── */}
          <BentoCard span="col-span-12 md:col-span-8" className="flex flex-col min-h-[420px] max-h-[620px]">
            <div className="px-6 py-3.5 border-b border-white/5 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                  <MessageSquare className="h-3.5 w-3.5 text-emerald-400" />
                </div>
                <p className="text-xs font-medium text-slate-400">Verified AI Chat</p>
                <span className="text-[9px] font-mono text-slate-600 bg-white/[0.03] px-1.5 py-0.5 rounded-full">
                  {indexedDocuments.length} indexed docs
                </span>
              </div>
              {chatHistory.length > 0 && (
                <button onClick={() => { setChatHistory([]); localStorage.removeItem('verirag_query_history') }}
                  className="text-[10px] text-slate-600 hover:text-red-400 transition-colors">
                  Clear history
                </button>
              )}
            </div>

            <div className="grid flex-1 grid-cols-1 xl:grid-cols-[minmax(0,1.7fr)_minmax(280px,0.9fr)] min-h-0">
              <div className="px-6 py-4 overflow-y-auto space-y-5 custom-scrollbar border-b xl:border-b-0 xl:border-r border-white/5">
                {chatHistory.length === 0 && (
                  <div className="h-full flex flex-col items-center justify-center text-slate-600 gap-3">
                    <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/5">
                      <Search className="w-8 h-8 opacity-30" />
                    </div>
                    <div className="text-center">
                      <p className="text-sm font-medium text-slate-500">Ask VeriRAG a question</p>
                      <p className="text-xs text-slate-700 mt-1">Responses are verified against your indexed document library</p>
                    </div>
                  </div>
                )}
                {chatHistory.map((chat, i) => (
                  <div
                    key={i}
                    className={`space-y-3 stagger-in rounded-3xl p-2 transition-all ${
                      selectedChatIndex === i ? 'bg-white/[0.02] ring-1 ring-indigo-500/20' : ''
                    }`}
                    style={{ animationDelay: `${i * 30}ms` }}
                  >
                    <div className="flex justify-end">
                      <button
                        type="button"
                        onClick={() => setSelectedChatIndex(i)}
                        className="bg-gradient-to-br from-indigo-600/90 to-indigo-700/90 backdrop-blur-sm px-4 py-2.5 rounded-2xl rounded-tr-sm max-w-md text-sm shadow-lg shadow-indigo-500/10 text-left"
                      >
                        {chat.question}
                      </button>
                    </div>
                    <div
                      className={`bg-white/[0.02] border rounded-2xl p-5 space-y-3 transition-colors cursor-pointer ${
                        selectedChatIndex === i ? 'border-indigo-500/20' : 'border-white/5 hover:border-white/10'
                      }`}
                      onClick={() => setSelectedChatIndex(i)}
                    >
                      <div className="flex items-center gap-2 text-[9px] font-mono uppercase tracking-widest">
                        <Shield className={`w-3 h-3 ${chat.verification_passed ? 'text-emerald-500' : 'text-amber-500'}`} />
                        <span className={chat.verification_passed ? 'text-emerald-500' : 'text-amber-500'}>
                          {chat.verification_passed ? 'Integrity Verified' : 'Low Confidence — Flagged'}
                        </span>
                        <span className="ml-auto text-slate-600 flex items-center gap-1">
                          <Cpu className="w-2.5 h-2.5" /> {chat.model_used}
                        </span>
                      </div>
                      <p className="text-sm text-slate-200 leading-relaxed">{chat.answer}</p>
                      <div className="flex items-center gap-3 pt-2 border-t border-white/5">
                        <span className="text-[10px] font-mono text-slate-500">Faithfulness</span>
                        <Progress value={(chat.faithfulness_score || 0) * 100} className="h-1.5 flex-1 bg-white/5" />
                        <span className="text-xs font-bold tabular-nums text-emerald-400">
                          {((chat.faithfulness_score || 0) * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
                <div ref={chatEndRef} />
              </div>

              <div className="px-5 py-4 overflow-y-auto custom-scrollbar bg-black/10">
                <div className="flex items-center gap-2 mb-4">
                  <div className="p-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/20">
                    <Shield className="h-3.5 w-3.5 text-cyan-400" />
                  </div>
                  <div>
                    <p className="text-xs font-medium text-slate-300">Evidence Panel</p>
                    <p className="text-[10px] text-slate-600">Selected answer trace and grounding</p>
                  </div>
                </div>

                {!selectedChat ? (
                  <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-4 text-sm text-slate-600">
                    Run a verified query to inspect the supporting evidence here.
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-mono uppercase tracking-[0.2em] text-slate-500">Verification</span>
                        <span className={`text-[10px] font-mono uppercase ${selectedChat.verification_passed ? 'text-emerald-400' : 'text-amber-400'}`}>
                          {selectedChat.verification_passed ? 'Passed' : 'Needs Review'}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 leading-relaxed">
                        {selectedChat.explanation || 'No verification narrative was returned for this answer.'}
                      </p>
                      <div className="grid grid-cols-2 gap-3 pt-2 border-t border-white/5">
                        <div>
                          <p className="text-[10px] font-mono uppercase tracking-[0.18em] text-slate-600">Model</p>
                          <p className="mt-1 text-sm text-slate-200">{selectedChat.model_used || 'unknown'}</p>
                        </div>
                        <div>
                          <p className="text-[10px] font-mono uppercase tracking-[0.18em] text-slate-600">Chunks Used</p>
                          <p className="mt-1 text-sm text-slate-200">{selectedChat.context_chunks_used ?? '—'}</p>
                        </div>
                      </div>
                    </div>

                    <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <p className="text-[10px] font-mono uppercase tracking-[0.2em] text-slate-500">Source Citations</p>
                        <span className="text-[10px] text-slate-600">{selectedEvidenceItems.length} refs</span>
                      </div>
                      {selectedEvidenceItems.length > 0 ? (
                        <div className="space-y-2">
                          {selectedEvidenceItems.map((item, idx) => (
                            <div key={`${item.citation || item}-${idx}`} className="rounded-xl border border-white/5 bg-black/10 px-3 py-2 text-xs text-slate-300 leading-relaxed">
                              <div className="flex items-center justify-between gap-3">
                                <span className="font-medium text-slate-200">{item.citation || item}</span>
                                {item.chunk_index !== undefined && item.chunk_index !== null && (
                                  <span className="text-[10px] font-mono text-slate-500">chunk {item.chunk_index}</span>
                                )}
                              </div>
                              {item.excerpt && (
                                <p className="mt-2 text-[11px] text-slate-500 leading-relaxed">
                                  {item.excerpt}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-xs text-slate-500">No citation metadata was returned for this answer.</p>
                      )}
                    </div>

                    <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-4 space-y-3">
                      <p className="text-[10px] font-mono uppercase tracking-[0.2em] text-slate-500">Query Context</p>
                      <p className="text-sm text-slate-200 leading-relaxed">{selectedChat.question}</p>
                      <div className="pt-2 border-t border-white/5">
                        <p className="text-[10px] font-mono uppercase tracking-[0.18em] text-slate-600">Answer Snapshot</p>
                        <p className="mt-2 text-xs text-slate-400 leading-relaxed">{selectedChat.answer}</p>
                      </div>
                      {selectedEvidenceSummary.length > 0 && (
                        <div className="pt-2 border-t border-white/5">
                          <p className="text-[10px] font-mono uppercase tracking-[0.18em] text-slate-600">Citations Summary</p>
                          <p className="mt-2 text-xs text-slate-500 leading-relaxed">
                            {selectedEvidenceSummary.join(' | ')}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="p-5 border-t border-white/5">
              <form onSubmit={handleQuery} className="flex gap-3">
                <div className="relative flex-1">
                  <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-600" />
                  <Input
                    placeholder="Ask VeriRAG Librarian..."
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    className="bg-white/5 border-white/10 h-12 pl-11 text-slate-100 placeholder:text-slate-600 rounded-xl focus:border-indigo-500/30 focus:ring-1 focus:ring-indigo-500/20 transition-all"
                  />
                </div>
                <Button type="submit" disabled={loading}
                  className="h-12 px-6 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 rounded-xl shadow-lg shadow-indigo-500/20 disabled:opacity-50 transition-all">
                  {loading ? (
                    <span className="flex items-center gap-2"><Cpu className="w-4 h-4 animate-spin" /> Verifying</span>
                  ) : (
                    <span className="flex items-center gap-2"><Sparkles className="w-4 h-4" /> Query AI</span>
                  )}
                </Button>
              </form>
              {queryError && (
                <div className="mt-3 rounded-xl border border-red-500/20 bg-red-500/10 px-3 py-2 text-xs text-red-300">
                  {queryError}
                </div>
              )}
              {indexedDocuments.length === 0 && (
                <div className="mt-3 rounded-xl border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
                  Wait for at least one document to finish indexing before expecting grounded answers.
                </div>
              )}
            </div>
          </BentoCard>

          {/* ── Cell 6: Metric Cards Row ─────────────────────────────── */}
          <div className="col-span-12 grid grid-cols-2 md:grid-cols-4 gap-3.5">
            {metricCards.map(({ label, value, icon, color, bg, border, sparkColor }, idx) => (
              <BentoCard key={label} className="p-5 flex flex-col gap-3 stagger-in" style={{ animationDelay: `${idx * 80}ms` }}>
                <div className="flex items-center justify-between">
                  <div className={`rounded-xl ${bg} p-2.5 border ${border}`}>
                    {React.createElement(icon, { className: `h-4 w-4 ${color}` })}
                  </div>
                  <Sparkline data={scoreTrend.slice(-8)} color={sparkColor} />
                </div>
                <div>
                  <p className={`text-3xl font-black tabular-nums ${color} tracking-tight`}>
                    {typeof value === 'number' ? <AnimatedCounter value={value} /> : '—'}
                  </p>
                  <p className="text-[9px] font-mono uppercase tracking-wider text-slate-600 mt-1">{label}</p>
                </div>
              </BentoCard>
            ))}
          </div>

        </div>
    </AppShell>
  )
}
