import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowRight,
  BarChart3,
  BrainCircuit,
  FileSearch,
  Lock,
  Shield,
  Sparkles,
  Zap,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { isAuthenticated } from '@/lib/auth'

const proofPoints = [
  { label: 'Verified answers', value: 'Faithfulness scoring + critic review' },
  { label: 'Document scale', value: 'Asynchronous ingestion with pgvector retrieval' },
  { label: 'Cloud-native path', value: 'Docker, Terraform, ACA-ready service split' },
]

const features = [
  {
    title: 'Evidence-first responses',
    body: 'Every answer is shaped by retrieved chunks, citations, and a verification pass instead of raw model confidence.',
    icon: FileSearch,
  },
  {
    title: 'Operational visibility',
    body: 'Indexing progress, retry behavior, and infrastructure health are visible enough to debug real failures.',
    icon: BarChart3,
  },
  {
    title: 'Provider resilience',
    body: 'Gemini and Groq can be composed for retrieval, synthesis, and failover rather than tied to a single model path.',
    icon: Zap,
  },
]

export default function LandingPage() {
  const navigate = useNavigate()
  const authed = useMemo(() => isAuthenticated(), [])

  return (
    <div className="min-h-screen bg-[#040207] text-slate-50">
      <div className="orb w-[460px] h-[460px] bg-cyan-500 top-[-12%] left-[-8%]" />
      <div className="orb w-[420px] h-[420px] bg-emerald-500 bottom-[8%] right-[-10%]" style={{ animationDelay: '6s' }} />
      <div className="orb w-[320px] h-[320px] bg-orange-500 top-[30%] right-[18%]" style={{ animationDelay: '12s' }} />

      <header className="sticky top-0 z-50 border-b border-white/[0.06] bg-[#040207]/80 backdrop-blur-2xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="rounded-2xl border border-cyan-400/20 bg-cyan-400/10 p-2.5">
              <Shield className="h-5 w-5 text-cyan-300" />
            </div>
            <div>
              <div className="text-lg font-bold tracking-tight">VeriRAG</div>
              <div className="text-[10px] font-mono uppercase tracking-[0.24em] text-slate-500">
                Verified AI Librarian
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              className="text-slate-300 hover:bg-white/5 hover:text-white"
              onClick={() => navigate('/login')}
            >
              Sign In
            </Button>
            <Button
              className="rounded-xl bg-cyan-400 text-slate-950 hover:bg-cyan-300"
              onClick={() => navigate(authed ? '/app' : '/login')}
            >
              {authed ? 'Open Workspace' : 'Launch Demo'}
            </Button>
          </div>
        </div>
      </header>

      <main className="relative z-10 mx-auto max-w-7xl px-6 pb-16 pt-14">
        <section className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr] lg:items-end">
          <div className="space-y-8">
            <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-[10px] font-mono uppercase tracking-[0.24em] text-cyan-200">
              <Sparkles className="h-3 w-3" />
              Blueprint Phase
            </div>
            <div className="space-y-5">
              <h1 className="max-w-4xl text-5xl font-black tracking-tight text-white md:text-7xl">
                Verified answers over complex document libraries.
              </h1>
              <p className="max-w-2xl text-base leading-7 text-slate-300 md:text-lg">
                VeriRAG combines retrieval, evidence tracking, and critic-based verification so the product behaves like an AI system you can actually operate.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button
                className="h-12 rounded-2xl bg-cyan-400 px-6 text-slate-950 hover:bg-cyan-300"
                onClick={() => navigate(authed ? '/app' : '/login')}
              >
                Enter Workspace <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                className="h-12 rounded-2xl border-white/10 bg-white/[0.03] px-6 text-slate-100 hover:bg-white/[0.06]"
                onClick={() => navigate('/login')}
              >
                Current Auth Flow
              </Button>
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              {proofPoints.map((item) => (
                <div key={item.label} className="bento-card p-4">
                  <div className="text-[10px] font-mono uppercase tracking-[0.22em] text-slate-500">{item.label}</div>
                  <div className="mt-2 text-sm text-slate-200">{item.value}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="bento-card overflow-hidden p-5">
            <div className="rounded-2xl border border-white/5 bg-black/30 p-5">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-[10px] font-mono uppercase tracking-[0.22em] text-slate-500">Live Workspace</div>
                  <div className="mt-1 text-xl font-semibold">Verification console</div>
                </div>
                <div className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1 text-[10px] font-mono uppercase tracking-[0.18em] text-emerald-300">
                  Operational
                </div>
              </div>
              <div className="mt-6 grid gap-3">
                <div className="rounded-2xl border border-white/5 bg-white/[0.03] p-4">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-slate-400">Document indexing</span>
                    <span className="text-cyan-300">73% complete</span>
                  </div>
                  <div className="mt-3 h-2 rounded-full bg-white/5">
                    <div className="h-2 w-[73%] rounded-full bg-gradient-to-r from-cyan-400 to-emerald-400" />
                  </div>
                </div>
                <div className="rounded-2xl border border-white/5 bg-white/[0.03] p-4">
                  <div className="flex items-center gap-2 text-[10px] font-mono uppercase tracking-[0.18em] text-emerald-300">
                    <BrainCircuit className="h-3 w-3" />
                    Integrity Verified
                  </div>
                  <p className="mt-3 text-sm leading-6 text-slate-200">
                    The platform surfaces citations, confidence, and provider usage instead of a single opaque answer bubble.
                  </p>
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-2xl border border-white/5 bg-white/[0.03] p-4">
                    <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-slate-500">Security posture</div>
                    <div className="mt-2 flex items-center gap-2 text-sm text-slate-200">
                      <Lock className="h-4 w-4 text-cyan-300" />
                      JWT today, OAuth-ready next
                    </div>
                  </div>
                  <div className="rounded-2xl border border-white/5 bg-white/[0.03] p-4">
                    <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-slate-500">Scalability</div>
                    <div className="mt-2 flex items-center gap-2 text-sm text-slate-200">
                      <Zap className="h-4 w-4 text-emerald-300" />
                      Worker + queue split for ACA
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="mt-20 grid gap-4 md:grid-cols-3">
          {features.map(({ title, body, icon: Icon }) => (
            <div key={title} className="bento-card p-6">
              <div className="inline-flex rounded-2xl border border-white/10 bg-white/[0.03] p-3">
                <Icon className="h-5 w-5 text-cyan-300" />
              </div>
              <h2 className="mt-5 text-xl font-semibold text-white">{title}</h2>
              <p className="mt-3 text-sm leading-6 text-slate-300">{body}</p>
            </div>
          ))}
        </section>
      </main>
    </div>
  )
}
