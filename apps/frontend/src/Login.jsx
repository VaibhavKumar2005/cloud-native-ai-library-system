import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Shield,
  Loader2,
  AlertCircle,
  Eye,
  EyeOff,
  Github,
  Chrome,
  Sparkles,
} from "lucide-react";
import axios from "axios";
import { consumeOAuthCallbackHash, storeSession } from "@/lib/auth";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const TOKEN_URL = `${API_BASE}/api/token/`;
const AUTH_PROVIDERS_URL = `${API_BASE}/api/auth/providers/`;

const providerIcons = {
  google: Chrome,
  github: Github,
};

export default function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [providerLoading, setProviderLoading] = useState(true);
  const [providers, setProviders] = useState([]);

  useEffect(() => {
    const initializeLogin = async () => {
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

      try {
        const res = await axios.get(AUTH_PROVIDERS_URL);
        setProviders(res.data.providers || []);
      } catch (err) {
        console.error("Provider manifest error:", err);
        setProviders([
          { id: "password", label: "Email or Username", type: "password", enabled: true },
        ]);
      } finally {
        setProviderLoading(false);
      }
    };

    initializeLogin();
    return undefined;
  }, [navigate]);

  const socialProviders = useMemo(
    () => providers.filter((provider) => provider.type === "oauth"),
    [providers]
  );

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!username || !password) return;

    setLoading(true);
    setError(null);

    try {
      const res = await axios.post(TOKEN_URL, { username, password });
      // Store both access and refresh tokens
      storeSession(res.data.access, res.data.refresh);
      navigate("/app");
    } catch (err) {
      if (err.response?.status === 401) {
        setError("Invalid credentials. Check your username and password.");
      } else if (err.response?.status >= 500) {
        setError("Backend is unreachable. Ensure Docker services are running.");
      } else {
        setError("Connection failed. Is the server at localhost:8000 online?");
      }
      console.error("Auth Error:", err);
    } finally {
      setLoading(false);
    }
  };

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
    <div className="flex min-h-screen items-center justify-center bg-slate-950 px-6">
      {/* Background grid effect */}
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(99,102,241,0.05),transparent_70%)]" />

      <div className="w-full max-w-md relative z-10">
        {/* Logo Header */}
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-600/10 border border-indigo-500/20">
            <Shield className="h-7 w-7 text-indigo-400" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">VeriRAG</h1>
          <p className="mt-1 text-xs font-mono uppercase tracking-[0.2em] text-slate-500">
            Secure Authentication Portal
          </p>
        </div>

        {/* Login Card */}
        <Card className="border-slate-800 bg-slate-900/60 backdrop-blur-xl">
          <CardContent className="pt-6">
            <div className="mb-5 space-y-3">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-cyan-300" />
                <p className="text-[10px] font-mono uppercase tracking-[0.22em] text-slate-500">
                  Auth Methods
                </p>
              </div>

              <div className="grid gap-2 sm:grid-cols-2">
                {providerLoading ? (
                  <div className="col-span-full flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-3 py-3 text-xs text-slate-500">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Loading auth providers...
                  </div>
                ) : socialProviders.length > 0 ? (
                  socialProviders.map((provider) => {
                    const Icon = providerIcons[provider.id] || Shield;
                    return (
                      <button
                        key={provider.id}
                        type="button"
                        disabled={!provider.enabled}
                        onClick={() => handleOAuthLogin(provider)}
                        className={`flex items-center justify-between rounded-xl border px-4 py-3 text-left transition ${
                          provider.enabled
                            ? "border-cyan-400/20 bg-cyan-400/10 text-cyan-100 hover:bg-cyan-400/15"
                            : "border-white/8 bg-white/[0.03] text-slate-500"
                        }`}
                      >
                        <span className="flex items-center gap-2 text-sm">
                          <Icon className="h-4 w-4" />
                          Continue with {provider.label}
                        </span>
                        <span className="text-[10px] font-mono uppercase tracking-[0.18em]">
                          {provider.enabled ? "Live" : "Disabled"}
                        </span>
                      </button>
                    );
                  })
                ) : (
                  <div className="col-span-full rounded-xl border border-white/10 bg-white/[0.03] px-3 py-3 text-xs text-slate-500">
                    Social login is not configured yet. Username and password login remains active.
                  </div>
                )}
              </div>
            </div>

            <div className="relative my-5">
              <div className="h-px bg-slate-800" />
              <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-slate-900 px-3 text-[10px] font-mono uppercase tracking-[0.2em] text-slate-600">
                Existing JWT Flow
              </span>
            </div>

            <form onSubmit={handleLogin} className="space-y-4">
              <div className="space-y-2">
                <label className="text-[10px] font-mono uppercase tracking-widest text-slate-500">
                  Username
                </label>
                <Input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Enter username"
                  className="h-11 bg-slate-950 border-slate-700 text-slate-100 placeholder:text-slate-600 focus:border-indigo-500 focus:ring-indigo-500/20"
                  autoComplete="username"
                  autoFocus
                />
              </div>

              <div className="space-y-2">
                <label className="text-[10px] font-mono uppercase tracking-widest text-slate-500">
                  Password
                </label>
                <div className="relative">
                  <Input
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter password"
                    className="h-11 bg-slate-950 border-slate-700 text-slate-100 placeholder:text-slate-600 pr-10 focus:border-indigo-500 focus:ring-indigo-500/20"
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              {/* Error Display */}
              {error && (
                <div className="flex items-start gap-2 rounded-lg bg-red-500/10 border border-red-500/20 p-3">
                  <AlertCircle className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />
                  <p className="text-xs text-red-400">{error}</p>
                </div>
              )}

              <Button
                type="submit"
                disabled={loading || !username || !password}
                className="w-full h-11 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition-all disabled:opacity-50"
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Authenticating...
                  </span>
                ) : (
                  "Sign In"
                )}
              </Button>
            </form>

            {/* Footer Info */}
            <div className="mt-6 pt-4 border-t border-slate-800">
              <p className="text-[10px] text-slate-600 text-center font-mono leading-5">
                PASSWORD LOGIN AND OAUTH BOTH LAND IN THE SAME API JWT SESSION
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Version Tag */}
        <p className="mt-6 text-center text-[10px] text-slate-700 font-mono">
          VeriRAG v2.0 — Cloud-Native AI Library System
        </p>
      </div>
    </div>
  );
}
