import { ResponsiveContainer } from 'recharts'
import { useEffect, useState } from 'react'

/**
 * ResponsiveChartContainer Component
 *
 * Wraps Recharts ResponsiveContainer with mobile-optimized height adjustments.
 * Automatically adjusts chart height based on screen size for optimal viewing
 * across all devices.
 *
 * Usage:
 * <ResponsiveChartContainer height={300} mobileHeight={250}>
 *   <LineChart data={data}>
 *     Chart components here
 *   </LineChart>
 * </ResponsiveChartContainer>
 */
export function ResponsiveChartContainer({
  children,
  height = 300,
  mobileHeight = 250,
  className = ''
}) {
  const [chartHeight, setChartHeight] = useState(height)

  useEffect(() => {
    // Detect screen size on mount
    const updateChartHeight = () => {
      const isMobile = window.innerWidth < 768
      setChartHeight(isMobile ? mobileHeight : height)
    }

    // Set initial height
    updateChartHeight()

    // Listen for window resize events
    window.addEventListener('resize', updateChartHeight)

    // Cleanup event listener
    return () => {
      window.removeEventListener('resize', updateChartHeight)
    }
  }, [height, mobileHeight])

  return (
    <div className={className}>
      <ResponsiveContainer width="100%" height={chartHeight}>
        {children}
      </ResponsiveContainer>
    </div>
  )
}

export default ResponsiveChartContainer
