import React from 'react'
import { clsx } from 'clsx'

const Tabs = ({ tabs, activeTab, onTabChange, darkMode }) => {
  return (
    <div className="border-b border-gray-200 dark:border-gray-700">
      <nav className="-mb-px flex space-x-2 overflow-x-auto py-3" aria-label="Tabs">
        {tabs.map((tab) => {
          const Icon = tab.icon
          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={clsx(
                'group inline-flex items-center py-2 px-4 border-b-2 font-medium text-sm transition-all duration-200 whitespace-nowrap rounded-t-lg',
                activeTab === tab.id
                  ? darkMode
                    ? 'border-blue-400 text-blue-400 bg-gray-700'
                    : 'border-blue-500 text-blue-600 bg-blue-50'
                  : darkMode
                    ? 'border-transparent text-gray-400 hover:text-gray-200 hover:border-gray-600 hover:bg-gray-700'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 hover:bg-gray-50'
              )}
            >
              <Icon
                className={clsx(
                  'mr-2 h-4 w-4',
                  activeTab === tab.id 
                    ? darkMode
                      ? 'text-blue-400' 
                      : 'text-blue-500'
                    : darkMode
                      ? 'text-gray-400 group-hover:text-gray-200'
                      : 'text-gray-400 group-hover:text-gray-500'
                )}
              />
              {tab.label}
            </button>
          )
        })}
      </nav>
    </div>
  )
}

export default Tabs
