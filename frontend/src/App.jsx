import React, { useEffect, useState } from 'react'
import axios from 'axios'
import {
  Activity,
  Bot,
  LayoutDashboard,
  PackageSearch,
  Settings,
  ShieldAlert,
} from 'lucide-react'
import Overview from './pages/Overview.jsx'
import ProductInsights from './pages/ProductInsights.jsx'
import AgentWorkspace from './pages/AgentWorkspace.jsx'
import Configuration from './pages/Configuration.jsx'

const API_ORIGIN = import.meta.env.VITE_API_ORIGIN || 'http://localhost:8001'
export const API_BASE_URL = `${API_ORIGIN}/api/v1`

const NAV_ITEMS = [
  { key: 'overview', label: 'Mission Control', icon: LayoutDashboard },
  { key: 'products', label: 'SKU Insights', icon: PackageSearch },
  { key: 'agent', label: 'Agent Workspace', icon: Bot },
  { key: 'config', label: 'Operations Config', icon: Settings },
]

function App() {
  const [activeTab, setActiveTab] = useState('overview')
  const [scraperRunning, setScraperRunning] = useState(false)
  const [agentRunning, setAgentRunning] = useState(false)
  const [alertCount, setAlertCount] = useState(0)

  useEffect(() => {
    const fetchStatuses = async () => {
      try {
        const [scraperRes, tasksRes, alertsRes] = await Promise.all([
          axios.get(`${API_BASE_URL}/scraper/status`),
          axios.get(`${API_BASE_URL}/agent/tasks?limit=1`),
          axios.get(`${API_BASE_URL}/alerts`),
        ])

        setScraperRunning(Boolean(scraperRes.data?.is_running))
        setAlertCount(alertsRes.data.length)

        if (tasksRes.data.length > 0) {
          const status = tasksRes.data[0].status
          setAgentRunning(status === 'Running' || status === 'Pending')
        } else {
          setAgentRunning(false)
        }
      } catch (err) {
        console.error('Failed to connect to backend API. Ensure FastAPI is running.', err)
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
            <strong>Guardian Pricing OS</strong>
            <span>Hackathon MVP command layer</span>
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

      <main className="main-content">{renderContent()}</main>
    </div>
  )
}

export default App
