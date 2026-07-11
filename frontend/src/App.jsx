import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { LayoutDashboard, Tag, Cpu, Settings, AlertTriangle, ShieldCheck } from 'lucide-react'
import Overview from './pages/Overview.jsx'
import ProductInsights from './pages/ProductInsights.jsx'
import AgentWorkspace from './pages/AgentWorkspace.jsx'
import Configuration from './pages/Configuration.jsx'

// Accept either a raw backend origin or a fully qualified /api/v1 base.
const rawApiBaseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001').replace(/\/$/, '')
export const API_BASE_URL = rawApiBaseUrl.endsWith('/api/v1') ? rawApiBaseUrl : `${rawApiBaseUrl}/api/v1`

function App() {
  const [activeTab, setActiveTab] = useState('overview')
  const [scraperRunning, setScraperRunning] = useState(false)
  const [agentRunning, setAgentRunning] = useState(false)
  const [alertCount, setAlertCount] = useState(0)

  // Fetch status of background processes periodically
  useEffect(() => {
    const fetchStatuses = async () => {
      try {
        // Scraper status
        const scraperRes = await axios.get(`${API_BASE_URL}/scraper/status`)
        setScraperRunning(scraperRes.data.is_running)

        // Agent status
        const tasksRes = await axios.get(`${API_BASE_URL}/agent/tasks?limit=1`)
        if (tasksRes.data.length > 0) {
          setAgentRunning(tasksRes.data[0].status === 'Running' || tasksRes.data[0].status === 'Pending')
        }

        // Active alerts
        const alertsRes = await axios.get(`${API_BASE_URL}/alerts`)
        setAlertCount(alertsRes.data.length)
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
    <div className="app-container">
      {/* Sidebar Panel */}
      <aside className="sidebar">
        <div className="logo-container">
          <div className="logo-icon">🛡️</div>
          <div className="logo-text">
            GUARDIAN
            <span>Price Intelligence</span>
          </div>
        </div>

        <nav>
          <ul className="nav-links">
            <li>
              <a 
                className={`nav-item ${activeTab === 'overview' ? 'active' : ''}`}
                onClick={() => setActiveTab('overview')}
              >
                <LayoutDashboard size={20} />
                Tổng quan
              </a>
            </li>
            <li>
              <a 
                className={`nav-item ${activeTab === 'products' ? 'active' : ''}`}
                onClick={() => setActiveTab('products')}
              >
                <Tag size={20} />
                Sản phẩm (SKU)
              </a>
            </li>
            <li>
              <a 
                className={`nav-item ${activeTab === 'agent' ? 'active' : ''}`}
                onClick={() => setActiveTab('agent')}
              >
                <Cpu size={20} />
                AI Agent Control
                {agentRunning && <span className="status-dot active" style={{ marginLeft: 'auto' }} />}
              </a>
            </li>
            <li>
              <a 
                className={`nav-item ${activeTab === 'config' ? 'active' : ''}`}
                onClick={() => setActiveTab('config')}
              >
                <Settings size={20} />
                Cấu hình hệ thống
              </a>
            </li>
          </ul>
        </nav>

        {/* System Health Indicators */}
        <div className="sidebar-footer">
          <div className="sidebar-footer-title">Trạng thái hệ thống</div>
          
          <div className="sidebar-footer-status" style={{ marginTop: '8px' }}>
            <span className={`status-dot ${scraperRunning ? 'active' : 'idle'}`} />
            <span style={{ color: scraperRunning ? '#10b981' : '#94a3b8' }}>
              Scraper: {scraperRunning ? 'Đang chạy...' : 'Nghỉ'}
            </span>
          </div>

          <div className="sidebar-footer-status">
            <span className={`status-dot ${agentRunning ? 'active' : 'idle'}`} style={{ color: agentRunning ? '#6366f1' : '#f59e0b' }} />
            <span style={{ color: agentRunning ? '#6366f1' : '#94a3b8' }}>
              AI Agent: {agentRunning ? 'Đang tối ưu...' : 'Sẵn sàng'}
            </span>
          </div>

          {alertCount > 0 && (
            <div className="sidebar-footer-status" style={{ color: '#ef4444', fontWeight: 'bold' }}>
              <AlertTriangle size={14} />
              Cảnh báo: {alertCount} SKU
            </div>
          )}
          {alertCount === 0 && (
            <div className="sidebar-footer-status" style={{ color: '#10b981' }}>
              <ShieldCheck size={14} />
              Cạnh tranh an toàn
            </div>
          )}
        </div>
      </aside>

      {/* Main Screen Router */}
      <main className="main-content">
        {renderContent()}
      </main>
    </div>
  )
}

export default App
