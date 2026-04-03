import * as React from 'react'
import { Search, Sparkles } from 'lucide-react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'

export default function CommandPalette({ open, onOpenChange, actions = [] }) {
  const [query, setQuery] = React.useState('')
  const inputRef = React.useRef(null)

  React.useEffect(() => {
    if (open) {
      setQuery('')
      window.setTimeout(() => inputRef.current?.focus(), 0)
    }
  }, [open])

  const filteredActions = React.useMemo(() => {
    const normalized = query.trim().toLowerCase()
    if (!normalized) return actions
    return actions.filter((action) => {
      const haystack = [action.label, action.description, ...(action.keywords || [])]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()
      return haystack.includes(normalized)
    })
  }, [actions, query])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="border-white/10 bg-[#06070d]/95 p-0 text-slate-50 shadow-2xl backdrop-blur-2xl sm:max-w-2xl">
        <DialogHeader className="border-b border-white/10 px-5 py-4 text-left">
          <DialogTitle className="flex items-center gap-2 text-base font-semibold text-white">
            <Sparkles className="h-4 w-4 text-cyan-300" />
            Command Palette
          </DialogTitle>
          <p className="text-sm text-slate-400">Navigate, switch context, and trigger common workspace actions.</p>
        </DialogHeader>

        <div className="px-5 pb-5 pt-4">
          <div className="relative">
            <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-600" />
            <Input
              ref={inputRef}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Type to search actions..."
              className="h-12 border-white/10 bg-white/[0.03] pl-11 text-slate-100 placeholder:text-slate-600 focus:border-cyan-400/30 focus:ring-cyan-400/20"
            />
          </div>

          <div className="mt-4 max-h-[360px] space-y-2 overflow-y-auto pr-1 custom-scrollbar">
            {filteredActions.length > 0 ? (
              filteredActions.map((action) => {
                const ActionIcon = action.icon
                return (
                  <button
                    key={action.id}
                    type="button"
                    onClick={() => {
                      action.run?.()
                      onOpenChange(false)
                    }}
                    className="flex w-full items-start justify-between rounded-2xl border border-white/5 bg-white/[0.03] px-4 py-3 text-left transition hover:-translate-y-0.5 hover:border-cyan-400/20 hover:bg-white/[0.05]"
                  >
                    <div className="flex items-start gap-3">
                      {ActionIcon ? (
                        <div className="rounded-xl border border-white/5 bg-black/20 p-2">
                          <ActionIcon className="h-4 w-4 text-cyan-300" />
                        </div>
                      ) : null}
                      <div>
                        <div className="text-sm font-semibold text-white">{action.label}</div>
                        <div className="mt-1 text-xs leading-5 text-slate-400">{action.description}</div>
                      </div>
                    </div>
                    {action.shortcut && (
                      <span className="rounded-full border border-white/10 bg-black/20 px-2 py-1 text-[10px] font-mono uppercase tracking-[0.18em] text-slate-500">
                        {action.shortcut}
                      </span>
                    )}
                  </button>
                )
              })
            ) : (
              <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.02] px-4 py-8 text-center text-sm text-slate-500">
                No commands matched your search.
              </div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
