import React from 'react'
import { AlertCircle, CheckCircle, Info, AlertTriangle, X } from 'lucide-react'

/**
 * Alert Component
 * Inline notification for messages, errors, warnings, and success states
 */
export function Alert({ title, children, variant = 'info', onClose = null, className = '' }) {
  const variants = {
    success: {
      bg: 'bg-emerald-500/10',
      border: 'border-emerald-500/20',
      text: 'text-emerald-400',
      icon: CheckCircle,
      iconColor: 'text-emerald-400',
    },
    warning: {
      bg: 'bg-amber-500/10',
      border: 'border-amber-500/20',
      text: 'text-amber-400',
      icon: AlertTriangle,
      iconColor: 'text-amber-400',
    },
    error: {
      bg: 'bg-red-500/10',
      border: 'border-red-500/20',
      text: 'text-red-400',
      icon: AlertCircle,
      iconColor: 'text-red-400',
    },
    info: {
      bg: 'bg-blue-500/10',
      border: 'border-blue-500/20',
      text: 'text-blue-400',
      icon: Info,
      iconColor: 'text-blue-400',
    },
  }

  const config = variants[variant] || variants.info
  const IconComponent = config.icon

  return (
    <div className={`rounded-lg ${config.bg} border ${config.border} p-4 ${className}`}>
      <div className="flex items-start gap-3">
        <IconComponent className={`h-5 w-5 ${config.iconColor} shrink-0 mt-0.5`} />
        <div className="flex-1">
          {title && <p className={`text-sm font-semibold ${config.text}`}>{title}</p>}
          {children && <p className={`text-xs ${config.text} mt-${title ? '1' : '0'}`}>{children}</p>}
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className={`${config.text} hover:opacity-75 transition-opacity shrink-0`}
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  )
}

export default Alert
