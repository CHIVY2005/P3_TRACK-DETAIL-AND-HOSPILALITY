import React, { useEffect, useState } from 'react'
import axios from 'axios'
import { BarChart, Bar, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import {
  Activity,
  ArrowRight,
  BrainCircuit,
  Cpu,
  Radar,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  Target,
  TrendingUp,
  Workflow,
} from 'lucide-react'
import { API_BASE_URL } from '../App.jsx'

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
      const [statsRes, alertsRes, briefingRes, actionsRes, branchSamplesRes] = await Promise.all([
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
        refresh_market_data: false,
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
    return <div className="loading-state">Loading mission control...</div>
  }

  const competitorChartData = stats?.competitor_avg_prices
    ? Object.entries(stats.competitor_avg_prices).map(([name, price]) => ({ name, price }))
    : []

  const summary = briefing?.summary
  const queue = briefing?.priority_queue || []
  const latestTaskLog = briefing?.latest_task?.logs
    ? briefing.latest_task.logs.split('\n').filter(Boolean).slice(-5)
    : ['No autonomous run yet. Import data, trigger scrape, then let the agent decide.']

  return (
    <div className="page-stack">
      <section className="hero-band">
        <div className="hero-copy">
          <div className="eyebrow">
            <Workflow size={14} />
            <span>Dynamic ingestion • link discovery • hybrid crawl • human approval</span>
          </div>
          <h1>Agentic pricing cockpit for Guardian&apos;s MVP merge.</h1>
          <p>
            This branch now combines the dashboard workflow, the scrape-oriented branch direction, and a cleaner
            agent architecture so the story from internal catalog to competitor action is visible in one screen.
          </p>
        </div>

        <div className="hero-actions">
          <button className="btn btn-secondary" onClick={handleTriggerScrape} disabled={triggeringScrape}>
            <RefreshCw size={16} className={triggeringScrape ? 'spin' : ''} />
            {triggeringScrape ? 'Scanning channels...' : 'Refresh channels'}
          </button>
          <button className="btn btn-accent" onClick={handleRunAgent} disabled={triggeringAgent}>
            <Cpu size={16} className={triggeringAgent ? 'pulse' : ''} />
            {triggeringAgent ? 'Agent running...' : 'Run pricing agent'}
          </button>
        </div>
      </section>

      <section className="hero-metrics">
        <MetricCard
          title="Tracked SKU"
          value={summary?.monitored_sku ?? stats?.total_sku ?? 0}
          detail="Catalog rows ready for sync and CPI logic"
          icon={<Target size={16} />}
        />
        <MetricCard
          title="Average CPI"
          value={`${summary?.average_cpi ?? stats?.average_cpi ?? 100}%`}
          detail="Guardian index versus competitor market average"
          icon={<TrendingUp size={16} />}
        />
        <MetricCard
          title="High-risk alerts"
          value={summary?.high_severity_alerts ?? stats?.high_severity_alerts ?? 0}
          detail="Undercut cases that need judgment fast"
          icon={<ShieldAlert size={16} />}
        />
        <MetricCard
          title="Covered channels"
          value={summary?.channels_covered ?? 0}
          detail="Live and fallback sources in current MVP"
          icon={<Radar size={16} />}
        />
      </section>

      <section className="pipeline-strip">
        {[
          ['1', 'Dynamic ingestion', 'CSV or JSON maps into the product catalog and optional competitor links.'],
          ['2', 'Link discovery', 'Missing URLs are generated into search-driven competitor link records.'],
          ['3', 'Hybrid scrape', 'Apify, Playwright, Crawl4AI, or fixture fallback keep the flow alive.'],
          ['4', 'Agent action', 'Margin Guardian and Supplier Negotiator propose the safest next move.'],
        ].map(([step, title, copy]) => (
          <div key={step} className="pipeline-step">
            <span>{step}</span>
            <strong>{title}</strong>
            <p>{copy}</p>
          </div>
        ))}
      </section>

      <div className="dashboard-grid dashboard-grid-wide">
        <section className="section-card glass">
          <div className="section-header">
            <div className="section-title section-title-inline">
              <BrainCircuit size={18} />
              <span>Live reasoning trace</span>
            </div>
            <span className="badge badge-info">
              <Activity size={12} />
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
        </section>

        <section className="section-card glass">
          <div className="section-header">
            <div className="section-title section-title-inline">
              <Sparkles size={18} />
              <span>Priority queue</span>
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
              <div className="empty-note">No active decision queue yet.</div>
            )}
          </div>
        </section>
      </div>

      <div className="dashboard-grid dashboard-grid-wide">
        <section className="section-card glass">
          <div className="section-header">
            <div className="section-title">Channel pricing map</div>
          </div>
          <div style={{ width: '100%', height: 320 }}>
            {competitorChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={competitorChartData} margin={{ top: 12, right: 12, left: 0, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(47, 79, 79, 0.12)" />
                  <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={12} />
                  <YAxis stroke="var(--text-muted)" fontSize={11} tickFormatter={(val) => `${Math.round(val / 1000)}k`} />
                  <Tooltip
                    cursor={{ fill: 'rgba(15, 118, 110, 0.08)' }}
                    contentStyle={{
                      backgroundColor: 'rgba(255,255,255,0.98)',
                      borderColor: 'rgba(15, 23, 42, 0.08)',
                      color: 'var(--text-main)',
                      borderRadius: '12px',
                    }}
                    formatter={(value) => [`${Number(value).toLocaleString()} VND`, 'Average net price']}
                  />
                  <Bar dataKey="price" radius={[10, 10, 0, 0]}>
                    {competitorChartData.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={
                          entry.name === 'GrabMart'
                            ? '#0f9f72'
                            : entry.name === 'Shopee'
                              ? '#ee6c4d'
                              : entry.name === 'Lazada'
                                ? '#2563eb'
                                : entry.name === 'TikTok Shop'
                                  ? '#111827'
                                  : '#0f766e'
                        }
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="empty-chart">No channel data yet.</div>
            )}
          </div>
        </section>

        <section className="section-card glass">
          <div className="section-header">
            <div className="section-title">Scrape branch evidence</div>
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
                    {sample.discount_pct ? ` • ${sample.discount_pct}% off` : ''}
                  </p>
                  <div className="sample-meta">
                    <span>{sample.record_count} record(s)</span>
                    <span>{sample.rating ? `${sample.rating} rating` : 'No rating'}</span>
                  </div>
                  {sample.match ? <div className="sample-match">Matched catalog SKU: {sample.match.product_name}</div> : null}
                  {sample.url ? (
                    <a href={sample.url} target="_blank" rel="noreferrer" className="inline-link-button">
                      Open source listing
                      <ArrowRight size={13} />
                    </a>
                  ) : null}
                </div>
              ))
            ) : (
              <div className="empty-note">No imported branch samples found.</div>
            )}
          </div>
        </section>
      </div>

      <div className="dashboard-grid">
        <section className="section-card glass">
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
              <div className="empty-note">No unresolved alerts.</div>
            )}
          </div>
        </section>

        <section className="section-card glass">
          <div className="section-header">
            <div className="section-title">Recent agent actions</div>
          </div>
          <div className="priority-list">
            {recentActions.length > 0 ? (
              recentActions.map((action) => {
                const payload = parseActionPayload(action.data)
                const decisionSummary = payload?.decision_summary

                return (
                  <div key={action.id} className="priority-card">
                    <div className="priority-topline">
                      <span className={`badge ${action.action_type === 'AUTO_PRICE_MATCH' ? 'badge-warning' : 'badge-info'}`}>
                        {action.action_type === 'AUTO_PRICE_MATCH' ? 'Price match' : 'Supplier draft'}
                      </span>
                      <span className="badge badge-success">{action.status}</span>
                    </div>
                    <strong>{action.description}</strong>
                    {decisionSummary ? (
                      <>
                        <p>{decisionSummary.reason}</p>
                        <div className="priority-metrics">
                          <span>{decisionSummary.competitor_name}</span>
                          <span>Margin if matched {formatPct(decisionSummary.margin_if_matched_pct)}</span>
                        </div>
                      </>
                    ) : (
                      <p>Created at {formatDateTime(action.created_at)}</p>
                    )}
                  </div>
                )
              })
            ) : (
              <div className="empty-note">No agent actions yet.</div>
            )}
          </div>
        </section>
      </div>
    </div>
  )
}

function MetricCard({ title, value, detail, icon }) {
  return (
    <div className="metric-card">
      <div className="metric-card-head">
        <span>{title}</span>
        <div className="metric-icon">{icon}</div>
      </div>
      <strong>{value}</strong>
      <p>{detail}</p>
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

function formatPct(value) {
  if (typeof value !== 'number') return '--'
  return `${value.toFixed(1)}%`
}

function parseActionPayload(rawData) {
  if (!rawData) return null
  try {
    return JSON.parse(rawData)
  } catch (err) {
    return null
  }
}

export default Overview
