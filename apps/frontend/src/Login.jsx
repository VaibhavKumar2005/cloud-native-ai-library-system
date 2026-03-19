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
import { colors } from "@/lib/colors";

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
    <div
      className="min-h-screen flex items-center justify-center px-4 sm:px-6 py-12"
      style={{ backgroundColor: colors.background.darkest }}
    >
      {/* Background gradient effect (inspired by Claude website) */}
      <div className="pointer-events-none fixed inset-0 bg-gradient-to-br from-blue-600/10 via-transparent to-purple-600/10" />

      {/* Main container */}
      <div className="w-full max-w-md relative z-10">
        {/* Hero Section - Inspired by Tailwind design */}
        <div className="mb-12 text-center">
          {/* Icon with subtle animation */}
          <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-600/20 to-blue-500/10 border border-blue-500/30 shadow-lg shadow-blue-500/10">
            <Shield className="h-8 w-8 text-blue-400 animate-pulse" />
          </div>

          {/* Main heading - Large, bold, clear (Tailwind + Claude style) */}
          <h1 className="text-4xl sm:text-3xl font-bold tracking-tight mb-3" style={{ color: colors.text.primary }}>
            VeriRAG
          </h1>

          {/* Subheading */}
          <p className="text-base font-medium mb-2" style={{ color: colors.text.secondary }}>
            Enterprise AI Research Platform
          </p>

          {/* Descriptor - Small, muted text */}
          <p className="text-xs font-mono uppercase tracking-widest" style={{ color: colors.text.muted }}>
            Secure • Cloud-Native • Encrypted
          </p>
        </div>

        {/* Auth Card - Spacious, clean layout */}
        <Card className="border-slate-800 bg-slate-900/60 backdrop-blur-xl shadow-2xl">
          <CardContent className="pt-8 pb-8 px-8">
            {/* Card title section */}
            <div className="mb-8">
              <div className="flex items-center gap-2 mb-2">
                <Lock className="h-5 w-5 text-blue-400" />
                <h2 className="text-2xl font-bold" style={{ color: colors.text.primary }}>
                  Sign In
                </h2>
              </div>
              <p className="text-sm" style={{ color: colors.text.muted }}>
                Choose your preferred authentication method
              </p>
            </div>

            {/* Email Auth Section - Generous spacing */}
            <div className="mb-8 p-6 rounded-xl" style={{ backgroundColor: 'rgba(3, 102, 214, 0.05)', border: `1px solid ${colors.border.default}` }}>
              <div className="flex items-center gap-2 mb-4">
                <Mail className="h-5 w-5 text-blue-400" />
                <h3 className="font-semibold text-slate-100">Email Magic Link</h3>
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

            {/* Global Error Display */}
            {error && (
              <div className="mb-6 flex items-start gap-3 rounded-lg bg-red-500/10 border border-red-500/20 p-4">
                <AlertCircle className="h-5 w-5 text-red-400 shrink-0 mt-0.5" />
                <p className="text-sm text-red-400">{error}</p>
              </div>
            )}

            {/* Divider with text (Claude style) */}
            <div className="relative my-8">
              <div className="h-px" style={{ backgroundColor: colors.border.default }} />
              <span
                className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 px-3 text-xs font-medium uppercase tracking-widest bg-slate-900"
                style={{ color: colors.text.muted }}
              >
                or
              </span>
            </div>

            {/* OAuth Providers - Clean grid layout */}
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
                        className={`group w-full flex items-center justify-between rounded-lg border px-5 py-4 font-medium text-base transition-all transform duration-150 ${
                          provider.enabled && !loading
                            ? "border-blue-400/30 bg-gradient-to-r from-blue-400/10 to-blue-500/5 text-slate-100 hover:border-blue-400/50 hover:from-blue-400/15 hover:to-blue-500/10 hover:shadow-lg hover:shadow-blue-500/10 hover:-translate-y-0.5"
                            : "border-slate-700/50 bg-slate-800/30 text-slate-500 cursor-not-allowed"
                        }`}
                      >
                        <span className="flex items-center gap-3">
                          <Icon className="h-5 w-5" />
                          <span>Continue with {provider.label}</span>
                        </span>
                        {provider.enabled && !loading && (
                          <ArrowRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
                        )}
                      </button>
                    );
                  })}
                </div>
              ) : (
                <div className="rounded-lg border border-white/10 bg-white/[0.03] px-4 py-4 text-center text-sm text-slate-500">
                  OAuth providers are not configured
                </div>
              )}
            </div>

            {/* Footer Security Info */}
            <div className="mt-8 pt-6 border-t" style={{ borderColor: colors.border.default }}>
              <div className="flex items-center gap-2 mb-3">
                <Sparkles className="h-4 w-4 text-blue-400" />
                <p className="text-xs font-semibold text-slate-300">Security Features</p>
              </div>
              <ul className="space-y-2 text-xs text-slate-400">
                <li className="flex items-center gap-2">
                  <div className="h-1 w-1 rounded-full bg-blue-500" />
                  <span>JWT-based secure sessions</span>
                </li>
                <li className="flex items-center gap-2">
                  <div className="h-1 w-1 rounded-full bg-blue-500" />
                  <span>Field-level document encryption</span>
                </li>
                <li className="flex items-center gap-2">
                  <div className="h-1 w-1 rounded-full bg-blue-500" />
                  <span>HashiCorp Vault secret protection</span>
                </li>
              </ul>
            </div>
          </CardContent>
        </Card>

        {/* Footer version tag */}
        <div className="mt-8 text-center">
          <p className="text-xs font-mono" style={{ color: colors.text.muted }}>
            VeriRAG v2.1 — Securing Enterprise AI Research
          </p>
          <p className="text-[10px] font-mono mt-2" style={{ color: colors.text.muted }}>
            🔐 End-to-end encryption • Multi-tenant isolated • Audit logged
          </p>
        </div>
      </div>
    </div>
  );
}
