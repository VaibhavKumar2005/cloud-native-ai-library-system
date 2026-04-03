import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Shield,
  Loader2,
  AlertCircle,
  Github,
  Chrome,
  Mail,
  ArrowRight,
  Lock,
  Sparkles,
} from "lucide-react";
import axios from "axios";
import { consumeOAuthCallbackHash, storeSession } from "@/lib/auth";
import EmailAuthForm from "@/components/EmailAuthForm";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const AUTH_PROVIDERS_URL = `${API_BASE}/api/auth/providers/`;

const providerIcons = {
  google: Chrome,
  github: Github,
};

export default function Login() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [providerLoading, setProviderLoading] = useState(true);
  const [providers, setProviders] = useState([]);

  useEffect(() => {
    const initializeLogin = async () => {
      // Check for OAuth callback
      const oauthResult = consumeOAuthCallbackHash();
      if (oauthResult?.ok && oauthResult.code) {
        setLoading(true);
        setError(null);

        try {
          const res = await axios.post(`${API_BASE}/api/auth/exchange/`, {
            code: oauthResult.code,
          });
          storeSession(res.data.access, res.data.refresh);
          navigate("/app", { replace: true });
          return;
        } catch (err) {
          setError(
            err.response?.data?.detail ||
              "OAuth login expired before it could be completed. Please try again."
          );
        } finally {
          setLoading(false);
        }
      }

      if (oauthResult && !oauthResult.ok) {
        setError(oauthResult.message);
      }

      // Fetch available auth providers
      try {
        const res = await axios.get(AUTH_PROVIDERS_URL);
        setProviders(res.data.providers || []);
      } catch (err) {
        console.error("Provider manifest error:", err);
        setProviders([]);
      } finally {
        setProviderLoading(false);
      }
    };

    initializeLogin();
  }, [navigate]);

  const socialProviders = (providers || []).filter(
    (provider) => provider.type === "oauth"
  );

  const handleOAuthLogin = (provider) => {
    if (!provider.enabled || !provider.start_url) {
      return;
    }

    const startUrl = provider.start_url.startsWith("http")
      ? provider.start_url
      : `${API_BASE}${provider.start_url}`;
    window.location.href = startUrl;
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#040207] px-4 py-8 text-slate-50 sm:px-6 lg:px-8">
      <div className="hero-grid" />
      <div className="pointer-events-none fixed inset-0 bg-gradient-to-br from-cyan-500/10 via-transparent to-emerald-500/10" />
      <div className="orb left-[-10%] top-[-8%] h-[420px] w-[420px] bg-cyan-500" />
      <div className="orb bottom-[6%] right-[-8%] h-[360px] w-[360px] bg-emerald-500" style={{ animationDelay: '7s' }} />

      <div className="relative z-10 mx-auto grid min-h-[calc(100vh-4rem)] max-w-7xl gap-8 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
        <section className="space-y-8 lg:pr-8">
          <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-[10px] font-mono uppercase tracking-[0.24em] text-cyan-200">
            <Sparkles className="h-3 w-3" />
            Secure access
          </div>

          <div className="space-y-5">
            <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl border border-cyan-400/20 bg-cyan-400/10 shadow-lg shadow-cyan-500/10">
              <Shield className="h-8 w-8 text-cyan-300" />
            </div>

            <h1 className="max-w-2xl text-4xl font-black tracking-tight text-white md:text-6xl">
              VeriRAG keeps answers grounded, auditable, and ready for real work.
            </h1>

            <p className="max-w-2xl text-base leading-7 text-slate-300 md:text-lg">
              Sign in with email magic link or your configured identity provider, then move into a workspace built for verified document retrieval rather than opaque chat.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="bento-card p-4">
              <p className="text-[10px] font-mono uppercase tracking-[0.22em] text-slate-500">Trust</p>
              <p className="mt-2 text-sm text-slate-200">JWT sessions and Vault-backed secrets.</p>
            </div>
            <div className="bento-card p-4">
              <p className="text-[10px] font-mono uppercase tracking-[0.22em] text-slate-500">Retrieval</p>
              <p className="mt-2 text-sm text-slate-200">Grounded answers with citations and verification.</p>
            </div>
            <div className="bento-card p-4">
              <p className="text-[10px] font-mono uppercase tracking-[0.22em] text-slate-500">Flow</p>
              <p className="mt-2 text-sm text-slate-200">Fast onboarding without extra ceremony.</p>
            </div>
          </div>
        </section>

        <section className="relative">
          <Card className="border-white/10 bg-black/30 shadow-2xl backdrop-blur-2xl">
            <CardContent className="p-6 sm:p-8">
              <div className="mb-8">
                <div className="flex items-center gap-2 mb-2">
                  <Lock className="h-5 w-5 text-cyan-300" />
                  <h2 className="text-2xl font-bold text-white">
                    Sign in
                  </h2>
                </div>
                <p className="text-sm text-slate-400">
                  Choose the fastest path into your workspace.
                </p>
              </div>

              <div className="mb-8 rounded-2xl border border-white/10 bg-white/[0.03] p-5">
                <div className="mb-4 flex items-center gap-2">
                  <Mail className="h-5 w-5 text-cyan-300" />
                  <h3 className="font-semibold text-white">Email magic link</h3>
                </div>
                <EmailAuthForm
                  onSuccess={() => {
                    navigate("/login?email_verified=true", { replace: true });
                  }}
                  onError={(err) => {
                    setError(
                      err.response?.data?.detail || "Authentication error. Please try again."
                    );
                  }}
                />
              </div>

              {error && (
                <div className="mb-6 flex items-start gap-3 rounded-xl border border-red-500/20 bg-red-500/10 p-4">
                  <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-400" />
                  <p className="text-sm text-red-300">{error}</p>
                </div>
              )}

              <div className="relative my-8">
                <div className="h-px bg-white/10" />
                <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-[#040207] px-3 text-xs font-medium uppercase tracking-widest text-slate-500">
                  or
                </span>
              </div>

              <div className="space-y-3">
                {providerLoading ? (
                  <div className="flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-4 py-4 text-sm text-slate-500">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Loading authentication options...
                  </div>
                ) : socialProviders.length > 0 ? (
                  <div className="space-y-3">
                    {socialProviders.map((provider) => {
                      const Icon = providerIcons[provider.id] || Shield;
                      return (
                        <button
                          key={provider.id}
                          type="button"
                          disabled={!provider.enabled || loading}
                          onClick={() => handleOAuthLogin(provider)}
                          className={`group flex w-full items-center justify-between rounded-2xl border px-5 py-4 text-base font-medium transition-all duration-150 ${
                            provider.enabled && !loading
                              ? "border-cyan-400/20 bg-white/[0.03] text-slate-100 hover:-translate-y-0.5 hover:border-cyan-400/35 hover:bg-white/[0.05]"
                              : "cursor-not-allowed border-slate-700/50 bg-slate-800/30 text-slate-500"
                          }`}
                        >
                          <span className="flex items-center gap-3">
                            <Icon className="h-5 w-5" />
                            <span>Continue with {provider.label}</span>
                          </span>
                          {provider.enabled && !loading && (
                            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                          )}
                        </button>
                      );
                    })}
                  </div>
                ) : (
                  <div className="rounded-xl border border-white/10 bg-white/[0.03] px-4 py-4 text-center text-sm text-slate-500">
                    OAuth providers are not configured
                  </div>
                )}
              </div>

              <div className="mt-8 border-t border-white/10 pt-6">
                <div className="mb-3 flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-cyan-300" />
                  <p className="text-xs font-semibold text-slate-200">Security features</p>
                </div>
                <ul className="space-y-2 text-xs text-slate-400">
                  <li className="flex items-center gap-2">
                    <div className="h-1 w-1 rounded-full bg-cyan-400" />
                    <span>JWT-based secure sessions</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <div className="h-1 w-1 rounded-full bg-cyan-400" />
                    <span>Field-level document encryption</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <div className="h-1 w-1 rounded-full bg-cyan-400" />
                    <span>HashiCorp Vault secret protection</span>
                  </li>
                </ul>
              </div>
            </CardContent>
          </Card>

          <div className="text-center text-xs font-mono text-slate-500 lg:text-left">
            VeriRAG v2.1 · Securing enterprise AI research
          </div>
        </section>
      </div>
    </div>
  );
}
