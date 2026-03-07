import { useState, useEffect } from 'react'
import Dashboard    from './pages/Dashboard'
import SessionStart from './pages/SessionStart'
import SessionEnd   from './pages/SessionEnd'

export default function App() {
  const [page, setPage]       = useState('start')
  const [endData, setEndData] = useState(null)

  // Update browser tab title based on current page
  useEffect(() => {
    const titles = {
      start:   'AffectSync — Start Session',
      session: 'AffectSync — Live Session 🟢',
      end:     'AffectSync — Session Summary',
    }
    document.title = titles[page] || 'AffectSync'
  }, [page])

  if (page === 'start') return (
    <SessionStart onStart={() => setPage('session')} />
  )
  if (page === 'end') return (
    <SessionEnd
      data={endData}
      onRestart={() => { setEndData(null); setPage('start') }}
    />
  )
  return (
    <Dashboard
      onEnd={(data) => { setEndData(data); setPage('end') }}
    />
  )
}