import React, { Suspense, lazy, useEffect, useState } from 'react'
import axios from 'axios'
import {
  Activity,
  Bot,
  LayoutDashboard,
  PackageSearch,
  Server,
  Settings,
  ShieldAlert,
} from 'lucide-react'
import { API_BASE_URL } from './api.js'

const Overview = lazy(() => import('./pages/Overview.jsx'))
const ProductInsights = lazy(() => import('./pages/ProductInsights.jsx'))
const AgentWorkspace = lazy(() => import('./pages/AgentWorkspace.jsx'))
const Configuration = lazy(() => import('./pages/Configuration.jsx'))

const NAV_ITEMS = [
  { key: 'overview', label: 'Pricing Command', icon: LayoutDashboard },
  { key: 'products', label: 'SKU Insights', icon: PackageSearch },
  { key: 'agent', label: 'Decision Desk', icon: Bot },
  { key: 'config', label: 'Guardrails', icon: Settings },
]

function App() {
  const [activeTab, setActiveTab] = useState('overview')
  const [scraperRunning, setScraperRunning] = useState(false)
  const [agentRunning, setAgentRunning] = useState(false)
  const [alertCount, setAlertCount] = useState(0)
  const [backendOnline, setBackendOnline] = useState(null)

  useEffect(() => {
    const fetchStatuses = async () => {
      try {
        const results = await Promise.allSettled([
          axios.get(`${API_BASE_URL}/scraper/status`),
          axios.get(`${API_BASE_URL}/agent/tasks?limit=1`),
          axios.get(`${API_BASE_URL}/alerts`),
        ])

        const scraperRes = results[0].status === 'fulfilled' ? results[0].value : null
        const tasksRes = results[1].status === 'fulfilled' ? results[1].value : null
        const alertsRes = results[2].status === 'fulfilled' ? results[2].value : null

        const isOnline = results.some(r => r.status === 'fulfilled')
        setBackendOnline(isOnline)

        if (!isOnline) {
          setScraperRunning(false)
          setAgentRunning(false)
          setAlertCount(0)
          return
        }

        if (scraperRes) {
          setScraperRunning(Boolean(scraperRes.data?.is_running))
        }
        if (alertsRes) {
          setAlertCount(alertsRes.data.length)
        }
        if (tasksRes) {
          if (tasksRes.data.length > 0) {
            const status = tasksRes.data[0].status
            setAgentRunning(status === 'Running' || status === 'Pending')
          } else {
            setAgentRunning(false)
          }
        }
      } catch (err) {
        console.error('Failed to connect to backend API. Ensure FastAPI is running.', err)
        setBackendOnline(false)
        setScraperRunning(false)
        setAgentRunning(false)
        setAlertCount(0)
      }
    }

    fetchStatuses()
    const interval = setInterval(fetchStatuses, 4000)
    return () => clearInterval(interval)
  }, [])

  const renderContent = () => {
    switch (activeTab) {
      case 'overview':
        return <Overview />
      case 'products':
        return <ProductInsights />
      case 'agent':
        return <AgentWorkspace />
      case 'config':
        return <Configuration />
      default:
        return <Overview />
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-panel">
          <div className="brand-mark">
            <ShieldAlert size={18} />
          </div>
          <div className="brand-copy">
            <strong>GUARDIAN</strong>
            <span>Pricing Intelligence OS</span>
          </div>
        </div>

        <div className="sidebar-cluster">
          <div className="sidebar-section-label">Navigate</div>
          <nav className="nav-links">
            {NAV_ITEMS.map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                type="button"
                className={`nav-item ${activeTab === key ? 'active' : ''}`}
                onClick={() => setActiveTab(key)}
              >
                <Icon size={18} />
                <span>{label}</span>
                {key === 'agent' && agentRunning ? <span className="status-pill live">Live</span> : null}
              </button>
            ))}
          </nav>
        </div>

        <div className="status-panel">
          <div className="sidebar-section-label">System pulse</div>
          <div className="status-row">
            <div className="status-row-label">
              <Server size={14} />
              <span>Backend API</span>
            </div>
            <span className={`status-pill ${backendOnline ? 'good' : backendOnline === false ? 'bad' : 'muted'}`}>
              {backendOnline ? 'Online' : backendOnline === false ? 'Offline' : 'Checking'}
            </span>
          </div>
          <div className="status-row">
            <div className="status-row-label">
              <Activity size={14} />
              <span>Scraper</span>
            </div>
            <span className={`status-pill ${scraperRunning ? 'good' : 'muted'}`}>
              {scraperRunning ? 'Running' : 'Idle'}
            </span>
          </div>
          <div className="status-row">
            <div className="status-row-label">
              <Bot size={14} />
              <span>Agent</span>
            </div>
            <span className={`status-pill ${agentRunning ? 'warn' : 'muted'}`}>
              {agentRunning ? 'Thinking' : 'Ready'}
            </span>
          </div>
          <div className="status-summary">
            <strong>{alertCount}</strong>
            <span>open pricing alerts</span>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <Suspense fallback={<div className="loading-state">Loading workspace...</div>}>
          {renderContent()}
        </Suspense>
      </main>
    </div>
  )
}

export default App
