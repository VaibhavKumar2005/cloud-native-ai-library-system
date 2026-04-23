import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowLeft,
  ArrowRight,
  BarChart3,
  CheckCircle2,
  ChevronRight,
  ExternalLink,
  Github,
  Rocket,
  Search,
  ShieldCheck,
  Sparkles,
  Star,
  GitFork,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { getDefaultRepoHealthReport, getRepoHealthReport, normalizeRepoIdentifier, repoHealthExamples } from '@/lib/repoHealthData'

const priorityStyles = {
  high: 'bg-rose-500/15 text-rose-200 border-rose-400/20',
  medium: 'bg-amber-500/15 text-amber-200 border-amber-400/20',
  low: 'bg-emerald-500/15 text-emerald-200 border-emerald-400/20',
}

function scoreTone(score) {
  if (score >= 85) return 'text-emerald-300'
  if (score >= 70) return 'text-cyan-300'
  if (score >= 50) return 'text-amber-300'
  return 'text-rose-300'
}

function analyzeRepoInput(value) {
  return new Promise((resolve) => {
    window.setTimeout(() => {
      resolve(getRepoHealthReport(value))
    }, 520)
  })
}

function StatPill({ icon: Icon, value, label }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
      <div className="flex items-center gap-2 text-sm text-slate-100">
        <Icon className="h-4 w-4 text-cyan-300" />
        <span className="font-semibold">{value}</span>
      </div>
      <div className="mt-1 text-xs uppercase tracking-[0.18em] text-slate-500">{label}</div>
    </div>
  )
}

function DimensionCard({ dimension }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-white">{dimension.title}</div>
          <div className="mt-1 text-sm text-slate-400">{dimension.question}</div>
        </div>
        <div className={`text-3xl font-black ${scoreTone(dimension.score)}`}>{dimension.score}</div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {dimension.highlights.map((item) => (
          <span
            key={item}
            className="rounded-full border border-white/8 bg-black/20 px-3 py-1 text-xs text-slate-300"
          >
            {item}
          </span>
        ))}
      </div>
    </div>
  )
}

function DetailPanel({ title, items, tone }) {
  if (!items.length) return null

  return (
    <div>
      <div className={`text-sm font-semibold ${tone}`}>{title}</div>
      <div className="mt-3 space-y-3">
        {items.map((item) => (
          <div key={item} className="flex gap-3 text-sm leading-6 text-slate-300">
            <ChevronRight className="mt-1 h-4 w-4 flex-none text-cyan-300" />
            <span>{item}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function GitHubHealthChecker() {
  const [repoInput, setRepoInput] = useState(getDefaultRepoHealthReport().repository.repoUrl)
  const [report, setReport] = useState(getDefaultRepoHealthReport())
  const [loading, setLoading] = useState(false)

  const handleAnalyze = async (value = repoInput) => {
    const normalized = normalizeRepoIdentifier(value)
    if (!normalized) return

    setRepoInput(value)
    setLoading(true)

    try {
      const nextReport = await analyzeRepoInput(value)
      if (nextReport) {
        setReport(nextReport)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen overflow-x-hidden bg-[#050816] text-slate-50">
      <div className="hero-grid" />
      <div className="orb left-[-10%] top-[-10%] h-[420px] w-[420px] bg-cyan-500" />
      <div className="orb bottom-[4%] right-[-8%] h-[460px] w-[460px] bg-emerald-500" style={{ animationDelay: '5s' }} />
      <div className="orb right-[22%] top-[28%] h-[280px] w-[280px] bg-orange-500" style={{ animationDelay: '11s' }} />

      <header className="relative z-20 border-b border-white/8 bg-[#050816]/80 backdrop-blur-2xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-4">
          <div className="flex items-center gap-4">
            <Link
              to="/"
              className="inline-flex items-center gap-2 text-sm text-slate-300 transition hover:text-white"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to VeriRAG
            </Link>
            <div className="hidden h-6 w-px bg-white/10 md:block" />
            <div>
              <div className="text-lg font-bold tracking-tight text-white">VeriRAG Tools</div>
              <div className="text-[10px] uppercase tracking-[0.24em] text-slate-500">Public diagnostics</div>
            </div>
          </div>
          <Button
            asChild
            variant="outline"
            className="rounded-xl border-white/10 bg-white/[0.03] text-slate-100 hover:bg-white/[0.08]"
          >
            <Link to="/login">Start Building Free</Link>
          </Button>
        </div>
      </header>

      <main className="relative z-10 mx-auto max-w-7xl px-6 pb-20 pt-10">
        <section className="float-in-up rounded-[2rem] border border-white/10 bg-[linear-gradient(135deg,rgba(255,255,255,0.08),rgba(255,255,255,0.02))] p-6 shadow-[0_30px_120px_rgba(0,0,0,0.45)] md:p-8">
          <div className="flex flex-wrap items-center gap-3 text-xs uppercase tracking-[0.24em] text-cyan-200">
            <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1">
              <Sparkles className="h-3 w-3" />
              AI-Powered Repo Insights
            </div>
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 text-slate-400">
              <Github className="h-3 w-3" />
              Frontend demo route
            </div>
          </div>

          <div className="mt-6 grid gap-8 lg:grid-cols-[1.1fr_0.9fr] lg:items-end">
            <div>
              <div className="text-sm text-cyan-300">Product</div>
              <h1 className="mt-3 max-w-4xl text-4xl font-black tracking-tight text-white md:text-6xl">
                GitHub Repo Health Checker
              </h1>
              <p className="mt-4 max-w-2xl text-base leading-7 text-slate-300 md:text-lg">
                Analyze any GitHub repository and get a comprehensive health score with AI-powered recommendations.
              </p>
            </div>

            <div className="rounded-[1.75rem] border border-white/10 bg-black/25 p-5">
              <div className="text-[10px] uppercase tracking-[0.22em] text-slate-500">How it works</div>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                {[
                  { step: '1', title: 'Enter Repo', body: 'Paste a GitHub URL or owner/name.' },
                  { step: '2', title: 'Analyze', body: 'Load a seeded AI-style report instantly.' },
                  { step: '3', title: 'Review', body: 'Explore scores, strengths, and recommendations.' },
                  { step: '4', title: 'Extend', body: 'Swap the mock adapter for a real API later.' },
                ].map((item) => (
                  <div key={item.step} className="rounded-2xl border border-white/8 bg-white/[0.03] p-4">
                    <div className="text-lg font-black text-cyan-300">{item.step}</div>
                    <div className="mt-2 font-semibold text-white">{item.title}</div>
                    <div className="mt-1 text-sm text-slate-400">{item.body}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-8 rounded-[1.75rem] border border-white/10 bg-black/30 p-5 md:p-6">
            <label className="text-sm font-semibold text-white">GitHub Repository URL or Name</label>
            <div className="mt-3 flex flex-col gap-3 lg:flex-row">
              <div className="relative flex-1">
                <Github className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-500" />
                <input
                  value={repoInput}
                  onChange={(event) => setRepoInput(event.target.value)}
                  placeholder="https://github.com/owner/repository"
                  className="h-14 w-full rounded-2xl border border-white/10 bg-white/[0.04] pl-12 pr-4 text-sm text-white placeholder:text-slate-500 focus:border-cyan-400/30 focus:outline-none focus:ring-2 focus:ring-cyan-400/20"
                />
              </div>
              <Button
                onClick={() => handleAnalyze(repoInput)}
                disabled={loading || !normalizeRepoIdentifier(repoInput)}
                className="h-14 rounded-2xl bg-cyan-400 px-7 text-base font-semibold text-slate-950 hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? 'Analyzing...' : 'Analyze'}
                <Search className="ml-2 h-4 w-4" />
              </Button>
            </div>

            <div className="mt-5 flex flex-wrap items-center gap-3 text-sm text-slate-400">
              <span>Try examples:</span>
              {repoHealthExamples.map((example) => (
                <button
                  key={example}
                  type="button"
                  onClick={() => handleAnalyze(example)}
                  className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5 text-slate-200 transition hover:border-cyan-400/30 hover:text-cyan-200"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        </section>

        <section className="mt-10 float-in-up" style={{ animationDelay: '120ms' }}>
          <div className="rounded-[2rem] border border-white/10 bg-white/[0.03] p-6 md:p-8">
            <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
              <div className="max-w-3xl">
                <div className="inline-flex items-center gap-2 rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1 text-[10px] uppercase tracking-[0.2em] text-emerald-200">
                  <CheckCircle2 className="h-3 w-3" />
                  Repository Analysis Complete
                </div>
                <h2 className="mt-4 text-3xl font-black tracking-tight text-white md:text-4xl">
                  {report.repository.fullName}
                </h2>
                <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-300 md:text-base">
                  {report.repository.description}
                </p>
                <div className="mt-5 flex flex-wrap gap-2">
                  {report.repository.tags.map((tag) => (
                    <span
                      key={tag}
                      className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-xs font-medium text-cyan-100"
                    >
                      #{tag}
                    </span>
                  ))}
                </div>
                <div className="mt-6 grid gap-3 sm:grid-cols-3">
                  <StatPill icon={Star} value={report.repository.stars.toLocaleString()} label="Stars" />
                  <StatPill icon={GitFork} value={report.repository.forks.toLocaleString()} label="Forks" />
                  <StatPill icon={BarChart3} value={report.summary.dimensionCount} label="Dimensions" />
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2 lg:w-[320px] lg:grid-cols-1">
                <div className="rounded-[1.75rem] border border-white/10 bg-black/25 p-5 text-center">
                  <div className="text-sm uppercase tracking-[0.18em] text-slate-500">Overall Health Score</div>
                  <div className={`mt-4 text-6xl font-black ${scoreTone(report.summary.overallScore)}`}>
                    {report.summary.overallScore}
                  </div>
                </div>
                <div className="rounded-[1.75rem] border border-white/10 bg-black/25 p-5 text-center">
                  <div className="text-sm uppercase tracking-[0.18em] text-slate-500">Grade</div>
                  <div className="mt-4 text-6xl font-black text-white">{report.summary.grade}</div>
                  <p className="mt-3 text-sm leading-6 text-slate-400">{report.summary.verdict}</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="mt-10">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {report.dimensions.map((dimension, index) => (
              <div key={dimension.key} className="float-in-up" style={{ animationDelay: `${index * 40}ms` }}>
                <DimensionCard dimension={dimension} />
              </div>
            ))}
          </div>
        </section>

        <section className="mt-12">
          <div className="flex items-center justify-between gap-4">
            <div>
              <div className="text-sm font-semibold text-white">Detailed Analysis</div>
              <div className="mt-1 text-sm text-slate-400">Strengths and opportunities across each dimension.</div>
            </div>
          </div>

          <div className="mt-6 grid gap-5">
            {report.dimensions.map((dimension) => (
              <div key={`${dimension.key}-detail`} className="rounded-[1.75rem] border border-white/10 bg-white/[0.03] p-6">
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div>
                    <h3 className="text-xl font-semibold text-white">
                      {dimension.title} <span className="text-slate-400">({dimension.score}/100)</span>
                    </h3>
                    <p className="mt-1 text-sm text-slate-400">{dimension.question}</p>
                  </div>
                  <div className={`text-3xl font-black ${scoreTone(dimension.score)}`}>{dimension.score}</div>
                </div>

                <div className="mt-6 grid gap-8 lg:grid-cols-2">
                  <DetailPanel title="Strengths" items={dimension.strengths} tone="text-emerald-300" />
                  <DetailPanel title="Areas for Improvement" items={dimension.improvements} tone="text-amber-300" />
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="mt-12">
          <div className="rounded-[2rem] border border-white/10 bg-[linear-gradient(135deg,rgba(8,15,35,0.95),rgba(10,31,45,0.82))] p-6 md:p-8">
            <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
              <div>
                <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-[10px] uppercase tracking-[0.2em] text-cyan-200">
                  <Sparkles className="h-3 w-3" />
                  AI-Powered Recommendations
                </div>
                <h3 className="mt-4 text-2xl font-black text-white md:text-3xl">Most valuable next improvements</h3>
                <p className="mt-2 max-w-2xl text-sm leading-7 text-slate-300 md:text-base">
                  Each recommendation is presented as a standalone action track so this mock UI can evolve cleanly into a real analyzer later.
                </p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-slate-300">
                Demo-ready interface, API-ready shape
              </div>
            </div>

            <div className="mt-8 grid gap-5 lg:grid-cols-2">
              {report.recommendations.map((recommendation) => (
                <div key={recommendation.title} className="rounded-[1.75rem] border border-white/10 bg-black/20 p-6">
                  <div className="flex items-center justify-between gap-3">
                    <h4 className="text-xl font-semibold text-white">{recommendation.title}</h4>
                    <span
                      className={`rounded-full border px-3 py-1 text-[10px] uppercase tracking-[0.18em] ${priorityStyles[recommendation.priority]}`}
                    >
                      {recommendation.priority} priority
                    </span>
                  </div>
                  <p className="mt-4 text-sm leading-7 text-slate-300">{recommendation.summary}</p>
                  <div className="mt-5 space-y-3">
                    {recommendation.actionSteps.map((step) => (
                      <div key={step} className="flex gap-3 text-sm text-slate-200">
                        <ArrowRight className="mt-1 h-4 w-4 flex-none text-cyan-300" />
                        <span>{step}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="mt-12 grid gap-6 lg:grid-cols-[1fr_0.9fr]">
          <div className="rounded-[1.75rem] border border-white/10 bg-white/[0.03] p-6">
            <div className="text-sm font-semibold text-white">Frequently Asked Questions</div>
            <div className="mt-5 divide-y divide-white/8">
              {report.faqs.map((faq) => (
                <div key={faq} className="flex items-center justify-between gap-3 py-4 text-sm text-slate-300">
                  <span>{faq}</span>
                  <ChevronRight className="h-4 w-4 text-slate-500" />
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-[1.75rem] border border-white/10 bg-white/[0.03] p-6">
            <div className="text-sm font-semibold text-white">Related Tools</div>
            <div className="mt-5 grid gap-3">
              {report.relatedTools.map((tool) => (
                <div
                  key={tool}
                  className="flex items-center justify-between rounded-2xl border border-white/8 bg-black/20 px-4 py-4 text-sm text-slate-200"
                >
                  <span>{tool}</span>
                  <ExternalLink className="h-4 w-4 text-cyan-300" />
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="mt-12 rounded-[2rem] border border-white/10 bg-white/[0.03] p-6 md:p-8">
          <div className="grid gap-6 md:grid-cols-[1.2fr_0.8fr] md:items-center">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1 text-[10px] uppercase tracking-[0.2em] text-emerald-200">
                <ShieldCheck className="h-3 w-3" />
                Ready for live data next
              </div>
              <h3 className="mt-4 text-2xl font-black text-white md:text-3xl">Share or export results</h3>
              <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-300 md:text-base">
                This version stays frontend-only by design, but the UI contract is already shaped for a future GitHub-backed analysis endpoint.
              </p>
            </div>
            <div className="flex flex-wrap gap-3 md:justify-end">
              <Button
                asChild
                className="h-11 rounded-2xl bg-emerald-400 px-5 text-slate-950 hover:bg-emerald-300"
              >
                <a href={report.repository.repoUrl} target="_blank" rel="noreferrer">
                  View on GitHub <ExternalLink className="ml-2 h-4 w-4" />
                </a>
              </Button>
              <Button
                variant="outline"
                className="h-11 rounded-2xl border-white/10 bg-transparent px-5 text-slate-100 hover:bg-white/[0.06]"
              >
                Analyze Another Repository
              </Button>
            </div>
          </div>
        </section>

        <footer className="mt-12 flex flex-col gap-4 border-t border-white/8 pt-8 text-sm text-slate-400 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3">
            <Rocket className="h-4 w-4 text-cyan-300" />
            <span>VeriRAG Tools demo surface for public product exploration.</span>
          </div>
          <Link to="/" className="inline-flex items-center gap-2 text-cyan-200 transition hover:text-white">
            Explore the main product <ArrowRight className="h-4 w-4" />
          </Link>
        </footer>
      </main>
    </div>
  )
}
