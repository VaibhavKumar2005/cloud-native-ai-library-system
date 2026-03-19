import React, { useState } from 'react'

/**
 * Tabs Component
 * Reusable tab interface for switching between views
 */
export function Tabs({ tabs = [], defaultTab = 0, onChange = null }) {
  const [activeIndex, setActiveIndex] = useState(defaultTab)

  const handleTabClick = (index) => {
    setActiveIndex(index)
    onChange?.(index)
  }

  return (
    <div className="w-full">
      {/* Tab Navigation */}
      <div className="flex gap-1 border-b border-slate-800 mb-6">
        {tabs.map((tab, index) => (
          <button
            key={index}
            onClick={() => handleTabClick(index)}
            className={`px-4 py-3 text-sm font-semibold transition-all border-b-2 ${
              activeIndex === index
                ? 'border-cyan-500 text-cyan-400'
                : 'border-transparent text-slate-400 hover:text-slate-300'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="animate-in fade-in-0 duration-200">
        {tabs[activeIndex]?.content}
      </div>
    </div>
  )
}

export default Tabs
