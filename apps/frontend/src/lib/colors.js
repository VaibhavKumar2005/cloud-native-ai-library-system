/**
 * VeriRAG Color System
 * Centralized color palette for professional, consistent UI/UX
 *
 * Design Principles:
 * - Dark theme with professional accents (designed for enterprise)
 * - Accessible contrast ratios (WCAG AA minimum)
 * - Semantic colors for common UI patterns
 * - Tailwind-compatible values
 */

export const colors = {
  // ─────────────────────────────────────────────────────────────
  // PRIMARY BACKGROUNDS: Dark, professional palette
  // ─────────────────────────────────────────────────────────────
  background: {
    // Darkest: Page/app background
    darkest: '#040207',    // Deep navy/black (from LandingPage)
    // Dark: Sidebar, card backgrounds
    dark: '#0F172A',       // Slate-900
    // Muted: Secondary cards, hover states
    muted: '#1E293B',      // Slate-800
    // Lighter: Elevated surfaces
    lighter: '#334155',    // Slate-700
  },

  // ─────────────────────────────────────────────────────────────
  // ACCENT COLORS: Brand and interaction colors (Azure Blue Enterprise)
  // ─────────────────────────────────────────────────────────────
  accent: {
    // Primary brand color (Azure Blue - Microsoft enterprise standard)
    azure: '#0078D4',      // Azure Blue (primary CTA, main brand)
    // Primary brand hover
    azureDark: '#106EBE',  // Azure Blue Dark (hover states)
    // Light accent for highlights
    azureLight: '#50E6FF', // Azure Light Blue (accents, highlights)
    // Secondary colors for variety
    cyan: '#06B6D4',       // Cyan-500 (secondary accent)
    indigo: '#4F46E5',     // Indigo-600 (tertiary)
    emerald: '#10B981',    // Emerald-500 (growth, success)
    orange: '#F97316',     // Orange-500 (attention, energy)
  },

  // ─────────────────────────────────────────────────────────────
  // TEXT COLORS: Typography hierarchy
  // ─────────────────────────────────────────────────────────────
  text: {
    // Primary: Headings, body text on dark bg
    primary: '#F1F5F9',    // Slate-100
    // Secondary: Subtle text, subheadings
    secondary: '#CBD5E1',  // Slate-300
    // Tertiary: Disabled, muted text
    muted: '#94A3B8',      // Slate-400
    // Quarternary: Very subtle (captions, hints)
    subtle: '#64748B',     // Slate-500
  },

  // ─────────────────────────────────────────────────────────────
  // SEMANTIC COLORS: Status and meaning
  // ─────────────────────────────────────────────────────────────
  semantic: {
    // Success: Positive actions, completed states
    success: '#10B981',    // Emerald-500
    // Warning: Caution, needs attention
    warning: '#F59E0B',    // Amber-500
    // Error: Errors, destructive actions
    error: '#EF4444',      // Red-500
    // Info: Information, neutral actions
    info: '#3B82F6',       // Blue-500
  },

  // ─────────────────────────────────────────────────────────────
  // BORDERS AND DIVIDERS
  // ─────────────────────────────────────────────────────────────
  border: {
    // Strong borders (primary elements)
    strong: '#475569',     // Slate-600
    // Normal borders (secondary elements)
    normal: '#334155',     // Slate-700
    // Subtle borders (dividers, faint lines)
    subtle: '#1E293B',     // Slate-800
    // Very subtle (almost invisible)
    faint: '#0F172A',      // Slate-900
  },

  // ─────────────────────────────────────────────────────────────
  // INTERACTIVE COLORS
  // ─────────────────────────────────────────────────────────────
  interactive: {
    // Button hover/focus states
    hover: 'rgba(255, 255, 255, 0.1)',
    // Button active state
    active: 'rgba(255, 255, 255, 0.15)',
    // Disabled state
    disabled: 'rgba(255, 255, 255, 0.05)',
    // Focus ring (accessibility)
    focus: '#06B6D4',      // Cyan (matches primary accent)
  },

  // ─────────────────────────────────────────────────────────────
  // GRADIENTS: Preset gradients for cards and hero sections
  // ─────────────────────────────────────────────────────────────
  gradients: {
    // Tech gradient (cyan to purple)
    tech: 'linear-gradient(135deg, #06B6D4 0%, #A855F7 100%)',
    // Professional gradient (indigo to cyan)
    professional: 'linear-gradient(135deg, #4F46E5 0%, #06B6D4 100%)',
    // Success gradient (emerald to cyan)
    success: 'linear-gradient(135deg, #10B981 0%, #06B6D4 100%)',
    // Warning gradient (orange to amber)
    warning: 'linear-gradient(135deg, #F97316 0%, #F59E0B 100%)',
  },

  // ─────────────────────────────────────────────────────────────
  // OPACITY VARIANTS: For layering and depth
  // ─────────────────────────────────────────────────────────────
  overlay: {
    light: 'rgba(0, 0, 0, 0.25)',
    medium: 'rgba(0, 0, 0, 0.5)',
    dark: 'rgba(0, 0, 0, 0.75)',
  },
};

// ═════════════════════════════════════════════════════════════════════════════
// TAILWIND CLASS MAPPINGS: Use these in className props
// ═════════════════════════════════════════════════════════════════════════════

export const cardClasses = {
  // Base card styles
  base: 'rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-xl shadow-lg',
  // Elevated card (more prominent)
  elevated: 'rounded-xl border border-slate-700 bg-slate-800/80 backdrop-blur-xl shadow-xl',
  // Ghost card (minimal)
  ghost: 'rounded-xl border border-slate-700/50 bg-transparent hover:bg-slate-900/50 transition-colors',
  // Accent card (with border color)
  accent: 'rounded-xl border border-cyan-500/30 bg-slate-900/60 backdrop-blur-xl hover:border-cyan-500/50 transition-colors',
};

export const buttonClasses = {
  // Primary button (Azure Blue)
  primary:
    'bg-blue-600 hover:bg-blue-700 text-white font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed',
  // Azure Blue variant (same as primary)
  azure:
    'bg-blue-600 hover:bg-blue-700 text-white font-semibold transition-all disabled:opacity-50',
  // Secondary button
  secondary:
    'bg-slate-800 hover:bg-slate-700 text-slate-100 border border-slate-700 font-semibold transition-all',
  // Ghost button
  ghost:
    'bg-transparent hover:bg-slate-800 text-slate-100 border border-slate-700 font-semibold transition-all',
  // Danger button
  danger:
    'bg-red-600 hover:bg-red-500 text-white font-semibold transition-all disabled:opacity-50',
  // Success button
  success:
    'bg-emerald-600 hover:bg-emerald-500 text-white font-semibold transition-all disabled:opacity-50',
};

export const inputClasses = {
  // Standard input (Azure Blue focus)
  base: 'h-11 rounded-lg bg-slate-950 border border-slate-700 text-slate-100 placeholder:text-slate-600 focus:border-blue-500 focus:ring-1 focus:ring-blue-500/20 transition-colors',
  // Focused state
  focused: 'border-blue-500 ring-1 ring-blue-500/20',
  // Error state
  error: 'border-red-500/50 focus:border-red-500 focus:ring-red-500/20',
  // Disabled state
  disabled: 'opacity-50 cursor-not-allowed',
};

export const badgeClasses = {
  // Success badge
  success: 'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-xs font-semibold text-emerald-400',
  // Warning badge
  warning: 'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-xs font-semibold text-amber-400',
  // Error badge
  error: 'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-red-500/10 border border-red-500/20 text-xs font-semibold text-red-400',
  // Info badge
  info: 'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-xs font-semibold text-blue-400',
  // Neutral badge
  neutral: 'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-500/10 border border-slate-500/20 text-xs font-semibold text-slate-400',
};

export const alertClasses = {
  // Success alert
  success: 'rounded-lg border border-emerald-500/20 bg-emerald-500/10 p-4 text-emerald-400',
  // Warning alert
  warning: 'rounded-lg border border-amber-500/20 bg-amber-500/10 p-4 text-amber-400',
  // Error alert
  error: 'rounded-lg border border-red-500/20 bg-red-500/10 p-4 text-red-400',
  // Info alert
  info: 'rounded-lg border border-blue-500/20 bg-blue-500/10 p-4 text-blue-400',
};

export default colors;
