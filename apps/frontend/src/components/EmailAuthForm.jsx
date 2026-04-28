import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AlertCircle, Loader2, Mail, CheckCircle, Lock } from "lucide-react";
import axios from "axios";
import { colors } from "@/lib/colors";

const API_BASE = import.meta.env.VITE_API_URL || "";

export default function EmailAuthForm({ onSuccess, onError }) {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !email.includes("@")) {
      setError("Please enter a valid email address");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await axios.post(`${API_BASE}/api/auth/email/send/`, {
        email: email.toLowerCase().trim(),
      });

      if (res.status === 200) {
        setSent(true);
        if (onSuccess) onSuccess(res.data);
      }
    } catch (err) {
      const errorMsg = err.response?.data?.detail || "Failed to send magic link. Please try again.";
      setError(errorMsg);
      if (onError) onError(err);
    } finally {
      setLoading(false);
    }
  };

  if (sent) {
    return (
      <div className="space-y-4 animate-in fade-in duration-300">
        {/* Success message - Clear, confident */}
        <div className="flex items-start gap-3 rounded-lg border border-emerald-500/30 bg-gradient-to-r from-emerald-500/10 to-emerald-400/5 p-4">
          <CheckCircle className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-emerald-300">Magic link sent!</p>
            <p className="text-sm text-emerald-400/80 mt-1">
              Check your inbox for a secure login link. Valid for 15 minutes.
            </p>
          </div>
        </div>

        {/* Resend option */}
        <button
          onClick={() => {
            setSent(false);
            setEmail("");
          }}
          className="w-full text-sm font-medium text-blue-400 hover:text-blue-300 transition-colors py-2 rounded-lg hover:bg-blue-500/10"
        >
          Send another link
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Email Input */}
      <div className="space-y-2">
        <label className="text-xs font-semibold uppercase tracking-widest" style={{ color: colors.text.muted }}>
          Email Address
        </label>
        <div className="relative">
          <Mail className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-blue-400/50 pointer-events-none" />
          <Input
            type="email"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              setError(null);
            }}
            placeholder="researcher@university.edu"
            className="pl-12 h-12 bg-slate-950 border-slate-700 text-slate-100 placeholder:text-slate-500 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 transition-all duration-150"
            autoComplete="email"
            autoFocus
            disabled={loading}
          />
        </div>
      </div>

      {/* Error message - Clear, actionable */}
      {error && (
        <div className="flex items-start gap-3 rounded-lg bg-red-500/10 border border-red-500/20 p-3 animate-in shake duration-300">
          <AlertCircle className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />
          <p className="text-xs text-red-400">{error}</p>
        </div>
      )}

      {/* Submit Button - Large, clear CTA (inspired by Claude) */}
      <Button
        type="submit"
        disabled={loading || !email}
        className="w-full h-12 bg-gradient-to-r from-blue-600 to-blue-600 hover:from-blue-500 hover:to-blue-500 text-white font-semibold transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-blue-500/20 hover:shadow-blue-500/40"
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <Loader2 className="h-5 w-5 animate-spin" />
            Sending...
          </span>
        ) : (
          <span className="flex items-center justify-center gap-2">
            <Lock className="h-5 w-5" />
            Send Magic Link
          </span>
        )}
      </Button>

      {/* Security note - Small, reassuring */}
      <p className="text-[11px] text-center font-mono" style={{ color: colors.text.muted }}>
        ✓ No password needed • ✓ Link expires in 15 min • ✓ Encrypted connection
      </p>
    </form>
  );
}
