/**
 * Skeleton Components for Loading States
 *
 * Provides animated skeleton loaders for better UX during data loading.
 * Based on PWA_IMPLEMENTATION_PLAN.md Phase 4, Section 4.1
 */

/**
 * Base Skeleton Component
 * A simple animated placeholder element with pulse animation
 *
 * @param {string} className - Additional Tailwind CSS classes
 * @param {object} props - Additional HTML element props
 * @returns {JSX.Element}
 */
export function Skeleton({ className = '', ...props }) {
  return (
    <div
      className={`
        animate-pulse
        rounded-md
        bg-gray-200
        dark:bg-gray-700
        ${className}
      `}
      {...props}
    />
  );
}

/**
 * Dashboard Skeleton Component
 * Displays a loading skeleton for the main dashboard layout
 * Shows header, stats grid, and chart placeholders
 *
 * @returns {JSX.Element}
 */
export function DashboardSkeleton() {
  return (
    <div className="space-y-6 p-4 sm:p-6 md:p-8 lg:p-10">
      {/* Dashboard Header Skeleton */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-gray-200 dark:border-gray-700">
        {/* Title and subtitle skeleton */}
        <div className="flex-1">
          <Skeleton className="h-8 w-48 mb-2" />
          <Skeleton className="h-4 w-64" />
        </div>
        {/* Action button skeleton */}
        <Skeleton className="h-10 w-32 rounded-lg" />
      </div>

      {/* Stats Grid Skeleton */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="bg-white dark:bg-gray-800 rounded-lg p-4 sm:p-6 space-y-4 border border-gray-200 dark:border-gray-700"
          >
            {/* Stat label */}
            <Skeleton className="h-4 w-24" />
            {/* Stat value */}
            <Skeleton className="h-10 w-32" />
            {/* Stat change indicator */}
            <Skeleton className="h-3 w-20" />
          </div>
        ))}
      </div>

      {/* Charts Grid Skeleton */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        {/* Large chart skeleton */}
        <div className="lg:col-span-2 bg-white dark:bg-gray-800 rounded-lg p-4 sm:p-6 border border-gray-200 dark:border-gray-700">
          {/* Chart title */}
          <Skeleton className="h-6 w-48 mb-4" />
          {/* Chart area */}
          <Skeleton className="h-64 w-full rounded-md" />
        </div>

        {/* Side chart skeleton */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 sm:p-6 border border-gray-200 dark:border-gray-700">
          {/* Chart title */}
          <Skeleton className="h-6 w-40 mb-4" />
          {/* Chart area */}
          <Skeleton className="h-48 w-full rounded-md" />
        </div>

        {/* Side chart skeleton */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 sm:p-6 border border-gray-200 dark:border-gray-700">
          {/* Chart title */}
          <Skeleton className="h-6 w-40 mb-4" />
          {/* Chart area */}
          <Skeleton className="h-48 w-full rounded-md" />
        </div>
      </div>

      {/* Table/List Skeleton */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 sm:p-6 border border-gray-200 dark:border-gray-700">
        {/* Table header */}
        <Skeleton className="h-6 w-32 mb-6" />
        {/* Table rows */}
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="flex gap-4">
              <Skeleton className="h-4 w-1/3 rounded" />
              <Skeleton className="h-4 w-1/4 rounded" />
              <Skeleton className="h-4 w-1/4 rounded" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/**
 * Chart Skeleton Component
 * Displays a loading skeleton for individual charts
 *
 * @param {number} height - Height of the skeleton in pixels (default: 300)
 * @param {string} title - Optional title for the chart skeleton
 * @returns {JSX.Element}
 */
export function ChartSkeleton({ height = 300, title = 'Loading chart...' }) {
  return (
    <div className="w-full bg-white dark:bg-gray-800 rounded-lg p-4 sm:p-6 border border-gray-200 dark:border-gray-700">
      {/* Chart title skeleton */}
      <div className="mb-4 sm:mb-6">
        <Skeleton className="h-6 w-48" />
      </div>

      {/* Chart area skeleton */}
      <div style={{ height: `${height}px` }} className="w-full">
        <Skeleton className="w-full h-full rounded-md" />
      </div>

      {/* Loading indicator text */}
      <div className="mt-4 text-center">
        <Skeleton className="h-4 w-40 mx-auto" />
      </div>
    </div>
  );
}

/**
 * Card Skeleton Component
 * Displays a loading skeleton for card-based layouts
 * Useful for holdings, assets, or other card-based data displays
 *
 * @param {number} count - Number of card skeletons to display (default: 3)
 * @returns {JSX.Element}
 */
export function CardSkeleton({ count = 3 }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="bg-white dark:bg-gray-800 rounded-lg p-4 sm:p-6 border border-gray-200 dark:border-gray-700"
        >
          {/* Card header */}
          <div className="flex items-start justify-between mb-4">
            <div className="flex-1">
              <Skeleton className="h-5 w-32 mb-2" />
              <Skeleton className="h-4 w-24" />
            </div>
            <Skeleton className="h-8 w-8 rounded-full" />
          </div>

          {/* Card content */}
          <div className="space-y-3 mb-4">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
          </div>

          {/* Card footer */}
          <div className="flex gap-2 pt-4 border-t border-gray-200 dark:border-gray-700">
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-4 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Table Skeleton Component
 * Displays a loading skeleton for table-based layouts
 *
 * @param {number} rows - Number of table rows to display (default: 5)
 * @param {number} columns - Number of columns (default: 4)
 * @returns {JSX.Element}
 */
export function TableSkeleton({ rows = 5, columns = 4 }) {
  return (
    <div className="w-full bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* Table header skeleton */}
      <div className="grid gap-4 p-4 sm:p-6 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={i} className="h-4 w-24" />
        ))}
      </div>

      {/* Table rows skeleton */}
      <div className="divide-y divide-gray-200 dark:divide-gray-700">
        {Array.from({ length: rows }).map((_, rowIdx) => (
          <div key={rowIdx} className="grid gap-4 p-4 sm:p-6">
            {Array.from({ length: columns }).map((_, colIdx) => (
              <Skeleton key={colIdx} className="h-4 w-full" />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Mini Card Skeleton Component
 * Compact skeleton for small metric cards
 *
 * @returns {JSX.Element}
 */
export function MiniCardSkeleton() {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
      <Skeleton className="h-3 w-20 mb-2" />
      <Skeleton className="h-6 w-24 mb-2" />
      <Skeleton className="h-3 w-16" />
    </div>
  );
}

export default Skeleton;
