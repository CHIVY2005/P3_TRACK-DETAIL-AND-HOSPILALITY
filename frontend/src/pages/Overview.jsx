import React, { useEffect, useState } from 'react'
import axios from 'axios'
import { API_BASE_URL } from '../App.jsx'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import {
  Activity,
  AlertTriangle,
  BrainCircuit,
  Cpu,
  RefreshCw,
  Radar,
  Send,
  ShieldAlert,
  Sparkles,
  Target,
  TrendingUp,
} from 'lucide-react'

function Overview() {
  const [stats, setStats] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [briefing, setBriefing] = useState(null)
  const [branchSamples, setBranchSamples] = useState([])
  const [recentActions, setRecentActions] = useState([])
  const [loading, setLoading] = useState(true)
  const [triggeringScrape, setTriggeringScrape] = useState(false)
  const [triggeringAgent, setTriggeringAgent] = useState(false)

  const fetchData = async () => {
    try {
      setLoading(true)
      const [
        statsRes,
        alertsRes,
        briefingRes,
        actionsRes,
        branchSamplesRes,
      ] = await Promise.all([
        axios.get(`${API_BASE_URL}/pricing/overview`),
        axios.get(`${API_BASE_URL}/alerts`),
        axios.get(`${API_BASE_URL}/agent/briefing?limit=5`),
        axios.get(`${API_BASE_URL}/agent/actions?limit=5`),
        axios.get(`${API_BASE_URL}/scraper/branch-samples`),
      ])

      setStats(statsRes.data)
      setAlerts(alertsRes.data)
      setBriefing(briefingRes.data)
      setRecentActions(actionsRes.data)
      setBranchSamples(branchSamplesRes.data)
    } catch (err) {
      console.error('Error fetching overview data', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const handleTriggerScrape = async () => {
    try {
      setTriggeringScrape(true)
      await axios.post(`${API_BASE_URL}/scraper/trigger`, {})
      fetchData()
    } catch (err) {
      alert('Unable to trigger competitor scan.')
    } finally {
      setTriggeringScrape(false)
    }
  }

  const handleRunAgent = async () => {
    try {
      setTriggeringAgent(true)
      await axios.post(`${API_BASE_URL}/agent/run`, {
        refresh_market_data: false
      })
      setTimeout(fetchData, 1200)
    } catch (err) {
      alert(err.response?.data?.detail || 'Unable to start agent run.')
    } finally {
      setTriggeringAgent(false)
    }
  }

  const handleResolveAlert = async (alertId) => {
    try {
      await axios.post(`${API_BASE_URL}/alerts/${alertId}/resolve`)
      fetchData()
    } catch (err) {
      console.error('Failed to resolve alert', err)
    }
  }

  if (loading && !stats && !briefing) {
    return <div style={{ color: 'var(--text-muted)' }}>Loading mission control...</div>
  }

  const competitorChartData = stats?.competitor_avg_prices
    ? Object.entries(stats.competitor_avg_prices).map(([name, price]) => ({ name, price }))
    : []

  const summary = briefing?.summary
  const queue = briefing?.priority_queue || []
  const latestTaskLog = briefing?.latest_task?.logs
    ? briefing.latest_task.logs.split('\n').filter(Boolean).slice(-4)
    : ['No autonomous run yet. Seed demo data, then let the agent refresh market data and act.']

  return (
    <div>
      <div className="header">
        <div className="header-title">
          <h1>Agentic Pricing Mission Control</h1>
          <p>Single source of truth for Top SKU pricing, promotion gaps, and approval-ready AI actions.</p>
        </div>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <button className="btn btn-secondary" onClick={handleTriggerScrape} disabled={triggeringScrape}>
            <RefreshCw size={16} className={triggeringScrape ? 'spin' : ''} />
            {triggeringScrape ? 'Scanning...' : 'Scan channels'}
          </button>
          <button className="btn btn-accent" onClick={handleRunAgent} disabled={triggeringAgent}>
            <Cpu size={16} className={triggeringAgent ? 'pulse' : ''} />
            {triggeringAgent ? 'Agent running...' : 'Run autonomous agent'}
          </button>
        </div>
      </div>

      <div className="mission-band glass">
        <div className="mission-copy">
          <span className="mission-eyebrow">Perceive  Reason  Act</span>
          <h2>The hackathon story should be visible in one glance.</h2>
          <p>
            The agent refreshes competitor channels, reasons over CPI and margin protection, then proposes
            the safest next move for a Category Manager to approve.
          </p>
        </div>
        <div className="mission-stats">
          <div className="mission-stat">
            <span>Tracked SKUs</span>
            <strong>{summary?.monitored_sku ?? stats?.total_sku ?? 0}</strong>
          </div>
          <div className="mission-stat">
            <span>Active alerts</span>
            <strong>{summary?.active_alerts ?? alerts.length}</strong>
          </div>
          <div className="mission-stat">
            <span>Pending approvals</span>
            <strong>{summary?.pending_actions ?? 0}</strong>
          </div>
          <div className="mission-stat">
            <span>Last scrape</span>
            <strong>{summary?.last_scrape_at ? formatDateTime(summary.last_scrape_at) : 'N/A'}</strong>
          </div>
        </div>
      </div>

      <div className="kpi-grid">
        <MetricCard
          title="Average CPI"
          value={`${summary?.average_cpi ?? stats?.average_cpi ?? 100}%`}
          detail="Guardian price index vs competitor average"
          icon={<Target className="kpi-icon" size={16} />}
        />
        <MetricCard
          title="High-risk alerts"
          value={summary?.high_severity_alerts ?? stats?.high_severity_alerts ?? 0}
          detail="Urgent undercutting or margin pressure"
          icon={<ShieldAlert className="kpi-icon" size={16} />}
        />
        <MetricCard
          title="Raise-price opportunities"
          value={stats?.underpriced_sku ?? 0}
          detail="Guardian priced meaningfully below market"
          icon={<TrendingUp className="kpi-icon" size={16} />}
        />
        <MetricCard
          title="Channels covered"
          value={summary?.channels_covered ?? 0}
          detail="Sources feeding the pricing command center"
          icon={<Radar className="kpi-icon" size={16} />}
        />
      </div>

      <div className="dashboard-grid" style={{ gridTemplateColumns: '1.3fr 1fr' }}>
        <div className="section-card glass">
          <div className="section-header">
            <div className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <BrainCircuit size={18} style={{ color: '#8b5cf6' }} />
              Live reasoning trace
            </div>
            <span className="badge badge-info">
              <Activity size={12} style={{ marginRight: '6px' }} />
              {briefing?.latest_task?.status || 'Idle'}
            </span>
          </div>
          <div className="reasoning-board">
            {latestTaskLog.map((line, index) => (
              <div key={index} className="reasoning-line">
                {line}
              </div>
            ))}
          </div>
        </div>

        <div className="section-card glass">
          <div className="section-header">
            <div className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Sparkles size={18} style={{ color: 'var(--primary)' }} />
              Priority queue
            </div>
          </div>
          <div className="priority-list">
            {queue.length > 0 ? (
              queue.map((item) => (
                <div key={item.alert_id} className="priority-card">
                  <div className="priority-topline">
                    <span className={`badge ${item.strategy === 'match' ? 'badge-warning' : 'badge-info'}`}>
                      {item.strategy === 'match' ? 'Match' : 'Negotiate'}
                    </span>
                    <span className={`badge ${item.severity === 'High' ? 'badge-danger' : 'badge-warning'}`}>
                      {item.severity}
                    </span>
                  </div>
                  <strong>{item.product_name}</strong>
                  <p>{item.rationale}</p>
                  <div className="priority-metrics">
                    <span>Gap {item.price_gap_pct}%</span>
                    <span>Margin if matched {item.margin_if_matched_pct}%</span>
                  </div>
                </div>
              ))
            ) : (
              <div style={{ color: 'var(--text-muted)' }}>No active decision queue yet.</div>
            )}
          </div>
        </div>
      </div>

      <div className="dashboard-grid" style={{ gridTemplateColumns: '1.2fr 0.8fr' }}>
        <div className="section-card glass">
          <div className="section-header">
            <div className="section-title">Channel pricing map</div>
          </div>
          <div style={{ width: '100%', height: 320 }}>
            {competitorChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={competitorChartData} margin={{ top: 10, right: 10, left: 0, bottom: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={12} />
                  <YAxis stroke="var(--text-muted)" fontSize={11} tickFormatter={(val) => `${Math.round(val / 1000)}k`} />
                  <Tooltip
                    contentStyle={{ backgroundColor: 'var(--bg-input)', borderColor: 'var(--border-color)', color: 'white' }}
                    formatter={(value) => [`${Number(value).toLocaleString()} VND`, 'Average net price']}
                  />
                  <Bar dataKey="price" radius={[8, 8, 0, 0]}>
                    {competitorChartData.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={
                          entry.name === 'GrabMart'
                            ? '#00b14f'
                            : entry.name === 'Shopee'
                              ? '#f04b29'
                              : entry.name === 'Lazada'
                                ? '#3b82f6'
                                : entry.name === 'TikTok Shop'
                                  ? '#111827'
                                  : '#8b5cf6'
                        }
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ color: 'var(--text-muted)', textAlign: 'center', paddingTop: '120px' }}>
                No channel data yet.
              </div>
            )}
          </div>
        </div>

        <div className="section-card glass">
          <div className="section-header">
            <div className="section-title">Branch data evidence</div>
          </div>
          <div className="sample-list">
            {branchSamples.length > 0 ? (
              branchSamples.map((sample, index) => (
                <div key={`${sample.kind}-${index}`} className="sample-card">
                  <div className="sample-labels">
                    <span className="badge badge-info">{sample.platform}</span>
                    <span className="badge badge-warning">{sample.kind.replace('_', ' ')}</span>
                  </div>
                  <strong>{sample.title}</strong>
                  <p>
                    {sample.current_price ? `${Number(sample.current_price).toLocaleString()} VND` : 'Price unavailable'}
                    {sample.discount_pct ? `  •  ${sample.discount_pct}% off` : ''}
                  </p>
                  <div className="sample-meta">
                    <span>{sample.record_count} record(s)</span>
                    <span>{sample.rating ? `${sample.rating} rating` : 'No rating'}</span>
                  </div>
                  {sample.match && (
                    <div className="sample-match">
                      Matched to catalog: {sample.match.product_name}
                    </div>
                  )}
                  {sample.url && (
                    <a href={sample.url} target="_blank" rel="noreferrer" className="action-card-details-btn">
                      Open source listing
                    </a>
                  )}
                </div>
              ))
            ) : (
              <div style={{ color: 'var(--text-muted)' }}>No imported branch samples found.</div>
            )}
          </div>
        </div>
      </div>

      <div className="dashboard-grid">
        <div className="section-card glass">
          <div className="section-header">
            <div className="section-title">Alert feed</div>
            <span className="badge badge-danger">{alerts.length} active</span>
          </div>
          <div className="alerts-list">
            {alerts.length > 0 ? (
              alerts.slice(0, 8).map((alert) => (
                <div className="alert-item" key={alert.id}>
                  <div className={`alert-badge ${alert.severity}`} />
                  <div className="alert-content">
                    <div className="alert-item-header">
                      <span className="alert-product-name">{alert.product?.name || 'Product'}</span>
                      <span className="alert-time">{formatTime(alert.created_at)}</span>
                    </div>
                    <p className="alert-msg">{alert.message}</p>
                  </div>
                  <button className="alert-resolve-btn" onClick={() => handleResolveAlert(alert.id)}>
                    ×
                  </button>
                </div>
              ))
            ) : (
              <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '40px 0' }}>
                No unresolved alerts.
              </div>
            )}
          </div>
        </div>

        <div className="section-card glass">
          <div className="section-header">
            <div className="section-title">Recent agent actions</div>
          </div>
          <div className="priority-list">
            {recentActions.length > 0 ? (
              recentActions.map((action) => (
                <div key={action.id} className="priority-card">
                  <div className="priority-topline">
                    <span className={`badge ${action.action_type === 'AUTO_PRICE_MATCH' ? 'badge-warning' : 'badge-info'}`}>
                      {action.action_type === 'AUTO_PRICE_MATCH' ? 'Price match' : 'Supplier draft'}
                    </span>
                    <span className="badge badge-success">{action.status}</span>
                  </div>
                  <strong>{action.description}</strong>
                  <p>Created at {formatDateTime(action.created_at)}</p>
                </div>
              ))
            ) : (
              <div style={{ color: 'var(--text-muted)' }}>No agent actions yet.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function MetricCard({ title, value, detail, icon }) {
  return (
    <div className="kpi-card glass">
      <div className="kpi-header">
        <span>{title}</span>
        {icon}
      </div>
      <div className="kpi-value">{value}</div>
      <div className="kpi-desc">{detail}</div>
    </div>
  )
}

function formatTime(isoStr) {
  const d = new Date(isoStr)
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

function formatDateTime(isoStr) {
  return new Date(isoStr).toLocaleString('en-GB', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default Overview
