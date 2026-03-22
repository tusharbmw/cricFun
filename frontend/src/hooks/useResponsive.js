import { useState, useEffect } from 'react'

export function useResponsive() {
  const [breakpoint, setBreakpoint] = useState('mobile')

  useEffect(() => {
    function handleResize() {
      if (window.innerWidth >= 1024) setBreakpoint('desktop')
      else if (window.innerWidth >= 768) setBreakpoint('tablet')
      else setBreakpoint('mobile')
    }
    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  return {
    isMobile: breakpoint === 'mobile',
    isTablet: breakpoint === 'tablet',
    isDesktop: breakpoint === 'desktop',
  }
}
