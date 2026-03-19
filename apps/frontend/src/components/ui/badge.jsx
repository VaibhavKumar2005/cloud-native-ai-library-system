import React from 'react'

/**
 * Badge Component
 * Small, inline elements for labels, tags, and status indicators
 */
export function Badge({ children, variant = 'neutral', className = '' }) {
  const variants = {
    success: 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400',
    warning: 'bg-amber-500/10 border border-amber-500/20 text-amber-400',
    error: 'bg-red-500/10 border border-red-500/20 text-red-400',
    info: 'bg-blue-500/10 border border-blue-500/20 text-blue-400',
    neutral: 'bg-slate-500/10 border border-slate-500/20 text-slate-400',
    cyan: 'bg-cyan-500/10 border border-cyan-500/20 text-cyan-400',
    indigo: 'bg-indigo-500/10 border border-indigo-500/20 text-indigo-400',
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${variants[variant]} ${className}`}
    >
      {children}
    </span>
  )
}

export default Badge
