import React, { useEffect, useState } from 'react'
import axios from 'axios'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  Activity,
  Clock3,
  Cpu,
  Database,
  Radar,
  RefreshCw,
  ServerOff,
  ShieldAlert,
  Sparkles,
  Target,
  TrendingUp,
  Workflow,
  X,
} from 'lucide-react'
import { API_BASE_URL, API_ORIGIN } from '../api.js'

function Overview() {
  const [stats, setStats] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [briefing, setBriefing] = useState(null)
  const [channelIntelligence, setChannelIntelligence] = useState(null)
  const [recentActions, setRecentActions] = useState([])
  const [loading, setLoading] = useState(true)
  const [triggeringScrape, setTriggeringScrape] = useState(false)
  const [triggeringAgent, setTriggeringAgent] = useState(false)
  const [seedingDemo, setSeedingDemo] = useState(false)
  const [loadError, setLoadError] = useState('')

  const fetchData = async () => {
    setLoading(true)
    try {
      const results = await Promise.allSettled([
        axios.get(`${API_BASE_URL}/pricing/overview`),
        axios.get(`${API_BASE_URL}/alerts`),
        axios.get(`${API_BASE_URL}/agent/briefing?limit=5`),
        axios.get(`${API_BASE_URL}/agent/actions?limit=5`),
        axios.get(`${API_BASE_URL}/pricing/channel-index`),
      ])

      const setters = [setStats, setAlerts, setBriefing, setRecentActions, setChannelIntelligence]
      results.forEach((result, index) => {
        if (result.status === 'fulfilled') {
          setters[index](result.value.data)
        }
      })

      const failures = results.filter((result) => result.status === 'rejected')
      if (failures.length === results.length) {
        setLoadError(`Backend is unavailable at ${API_ORIGIN}.`)
      } else if (failures.length > 0) {
        setLoadError(`${failures.length} pricing API endpoint(s) did not respond. Data shown may be incomplete.`)
      } else {
        setLoadError('')
      }
    } catch (err) {
      console.error('Error fetching overview data', err)
      setLoadError(`Unable to load pricing data from ${API_ORIGIN}.`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  useEffect(() => {
    if (!loadError) return undefined
    const retryTimer = setInterval(fetchData, 5000)
    return () => clearInterval(retryTimer)
  }, [loadError])

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

  const handleSeedDemo = async () => {
    try {
      setSeedingDemo(true)
      await axios.post(`${API_BASE_URL}/products/seed-demo`)
      await fetchData()
    } catch (err) {
      setLoadError(err.response?.data?.detail || `Unable to initialize the demo catalog at ${API_ORIGIN}.`)
    } finally {
      setSeedingDemo(false)
    }
  }

  if (loading && !stats && !briefing) {
    return <div className="loading-state">Loading pricing command center...</div>
  }

  const summary = channelIntelligence?.summary
  const briefingSummary = briefing?.summary
  const channels = channelIntelligence?.channels || []
  const queue = briefing?.priority_queue || []
  const catalogIsEmpty = !loading && (
    summary?.monitored_sku === 0 || (!summary && stats?.total_sku === 0)
  )
  const latestTaskLog = briefing?.latest_task?.logs
    ? briefing.latest_task.logs.split('\n').filter(Boolean).slice(-6)
    : ['No decision cycle has run yet. Market intelligence is ready for operator review.']

  return (
    <div className="page-stack">
      <section className="hero-band">
        <div className="hero-copy">
          <div className="eyebrow">
            <Workflow size={14} />
            <span>Commercial control room / Daily market read</span>
          </div>
          <h1>Guardian Pricing OS</h1>
          <p>
            200 priority SKUs. Six channels. One decision loop turning effective competitor prices into
            margin-safe actions for the commercial team.
          </p>
        </div>

        <div className="hero-actions">
          <button className="btn btn-secondary" onClick={handleTriggerScrape} disabled={triggeringScrape}>
            <RefreshCw size={16} className={triggeringScrape ? 'spin' : ''} />
            {triggeringScrape ? 'Scanning channels...' : 'Refresh market'}
          </button>
          <button className="btn btn-accent" onClick={handleRunAgent} disabled={triggeringAgent}>
            <Cpu size={16} className={triggeringAgent ? 'pulse' : ''} />
            {triggeringAgent ? 'Cycle running...' : 'Run decision cycle'}
          </button>
        </div>
      </section>

      {loadError ? (
        <section className="system-notice system-notice-error" role="alert">
          <div className="system-notice-icon"><ServerOff size={18} /></div>
          <div className="system-notice-copy">
            <strong>Pricing data connection needs attention</strong>
            <span>{loadError}</span>
          </div>
          <button type="button" className="btn btn-secondary btn-compact" onClick={fetchData} disabled={loading}>
            <RefreshCw size={15} className={loading ? 'spin' : ''} />
            Retry
          </button>
        </section>
      ) : null}

      {catalogIsEmpty ? (
        <section className="system-notice system-notice-empty">
          <div className="system-notice-icon"><Database size={18} /></div>
          <div className="system-notice-copy">
            <strong>The catalog is empty</strong>
            <span>Initialize the 200-SKU, six-channel dataset to populate Pricing Command.</span>
          </div>
          <button type="button" className="btn btn-accent btn-compact" onClick={handleSeedDemo} disabled={seedingDemo}>
            <Database size={15} />
            {seedingDemo ? 'Loading demo...' : 'Load demo data'}
          </button>
        </section>
      ) : null}

      <section className="hero-metrics">
        <MetricCard
          title="Priority SKU coverage"
          value={`${summary?.monitored_sku ?? stats?.total_sku ?? 0}/${summary?.target_sku ?? 200}`}
          detail={`${formatPct(summary?.target_coverage_pct)} of the priority catalog monitored`}
          icon={<Target size={16} />}
        />
        <MetricCard
          title="Omnichannel CPI"
          value={formatIndex(summary?.overall_cpi ?? stats?.average_cpi)}
          detail="100 is price parity after discounts and vouchers"
          icon={<TrendingUp size={16} />}
        />
        <MetricCard
          title="Automated coverage"
          value={formatPct(summary?.automated_observation_coverage_pct)}
          detail={`${summary?.channels_with_data ?? briefingSummary?.channels_covered ?? 0} active competitor channels`}
          icon={<Radar size={16} />}
        />
        <MetricCard
          title="Fresh within 24h"
          value={formatPct(summary?.fresh_observation_pct)}
          detail={`${summary?.fresh_sku ?? 0} SKU meet the daily freshness SLA`}
          icon={<Clock3 size={16} />}
        />
      </section>

      <section className="signal-strip" aria-label="Current pricing signals">
        <SignalStat label="Valid observations" value={formatPct(summary?.valid_observation_pct)} />
        <SignalStat label="Promotion signals" value={summary?.promotion_observations ?? 0} />
        <SignalStat label="Pricing opportunities" value={summary?.pricing_opportunities ?? 0} />
        <SignalStat
          label="Latest market signal"
          value={formatAge(summary?.latest_observation_age_hours)}
        />
      </section>

      <div className="dashboard-grid dashboard-grid-wide">
        <section className="section-card glass">
          <div className="section-header">
            <div className="section-title section-title-inline">
              <Activity size={18} />
              <span>Decision audit trail</span>
            </div>
            <span className="badge badge-info">{briefing?.latest_task?.status || 'Idle'}</span>
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
              <span>Priority decisions</span>
            </div>
            <span className="badge badge-warning">{queue.length} SKU</span>
          </div>
          <div className="priority-list">
            {queue.length > 0 ? (
              queue.map((item) => (
                <div key={item.alert_id} className="priority-card">
                  <div className="priority-topline">
                    <span className={`badge ${item.strategy === 'match' ? 'badge-warning' : 'badge-info'}`}>
                      {item.strategy === 'match' ? 'Align price' : 'Negotiate'}
                    </span>
                    <span className={`badge ${item.severity === 'High' ? 'badge-danger' : 'badge-warning'}`}>
                      {item.severity}
                    </span>
                  </div>
                  <strong>{item.product_name}</strong>
                  <p>{item.rationale}</p>
                  <div className="priority-metrics">
                    <span>{item.competitor_name}</span>
                    <span>Gap {formatPct(item.price_gap_pct)}</span>
                    <span>Margin after action {formatPct(item.margin_if_matched_pct)}</span>
                  </div>
                </div>
              ))
            ) : (
              <div className="empty-note">No active decision queue.</div>
            )}
          </div>
        </section>
      </div>

      <div className="dashboard-grid dashboard-grid-wide">
        <section className="section-card glass">
          <div className="section-header">
            <div className="section-title">Competitor pricing index by channel</div>
            <span className="badge badge-info">Parity = 100</span>
          </div>
          <div className="chart-frame">
            {channels.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={channels} margin={{ top: 12, right: 12, left: 0, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(47, 79, 79, 0.12)" />
                  <XAxis dataKey="channel" stroke="var(--text-muted)" fontSize={12} />
                  <YAxis
                    stroke="var(--text-muted)"
                    fontSize={11}
                    domain={['dataMin - 10', 'dataMax + 10']}
                  />
                  <Tooltip
                    cursor={{ fill: 'rgba(255, 212, 0, 0.12)' }}
                    contentStyle={{
                      backgroundColor: '#ffffff',
                      borderColor: 'rgba(15, 23, 42, 0.12)',
                      color: 'var(--text-main)',
                      borderRadius: '8px',
                    }}
                    formatter={(value, name, item) => [
                      `${Number(value).toFixed(1)} (coverage ${formatPct(item.payload.coverage_pct)})`,
                      'CPI',
                    ]}
                  />
                  <ReferenceLine y={100} stroke="#66665f" strokeDasharray="5 4" />
                  <Bar dataKey="cpi" radius={[4, 4, 0, 0]}>
                    {channels.map((entry) => (
                      <Cell key={entry.channel} fill={channelColor(entry.position)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="empty-chart">No channel CPI data yet.</div>
            )}
          </div>
        </section>

        <section className="section-card glass">
          <div className="section-header">
            <div className="section-title">Promotion intelligence</div>
          </div>
          <div className="channel-list">
            {channels.map((channel) => (
              <div className="channel-row" key={channel.channel}>
                <div className="channel-row-main">
                  <strong>{channel.channel}</strong>
                  <span>{channel.sku_coverage} comparable SKU</span>
                </div>
                <div className="channel-row-metrics">
                  <span>Voucher {channel.voucher_sku}</span>
                  <span>Bundle {channel.bundle_sku}</span>
                  <span>Flash {channel.flash_sale_sku}</span>
                  <span className={channel.opportunity_count > 0 ? 'price-bad' : 'price-good'}>
                    {channel.opportunity_count} gaps
                  </span>
                </div>
              </div>
            ))}
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
              alerts.slice(0, 8).map((alertItem) => (
                <div className="alert-item" key={alertItem.id}>
                  <div className={`alert-badge ${alertItem.severity}`} />
                  <div className="alert-content">
                    <div className="alert-item-header">
                      <span className="alert-product-name">{alertItem.product?.name || 'Product'}</span>
                      <span className="alert-time">{formatTime(alertItem.created_at)}</span>
                    </div>
                    <p className="alert-msg">{alertItem.message}</p>
                  </div>
                  <button
                    type="button"
                    className="alert-resolve-btn"
                    onClick={() => handleResolveAlert(alertItem.id)}
                    aria-label="Resolve alert"
                    title="Resolve alert"
                  >
                    <X size={16} />
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
            <span className="badge badge-info">Human approval</span>
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
                        {action.action_type === 'AUTO_PRICE_MATCH' ? 'Price alignment' : 'Supplier draft'}
                      </span>
                      <span className={`badge ${actionStatusClass(action.status)}`}>{action.status}</span>
                    </div>
                    <strong>{action.description}</strong>
                    {decisionSummary ? (
                      <>
                        <p>{decisionSummary.reason}</p>
                        <div className="priority-metrics">
                          <span>{decisionSummary.competitor_name}</span>
                          <span>Margin after action {formatPct(decisionSummary.margin_if_matched_pct)}</span>
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

function SignalStat({ label, value }) {
  return (
    <div className="signal-stat">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function formatTime(isoStr) {
  const date = new Date(isoStr)
  return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
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

function formatIndex(value) {
  if (typeof value !== 'number') return '--'
  return value.toFixed(1)
}

function formatAge(value) {
  if (typeof value !== 'number') return 'No signal'
  if (value < 1) return '<1h ago'
  return `${Math.round(value)}h ago`
}

function channelColor(position) {
  if (position === 'guardian_premium') return '#c2410c'
  if (position === 'guardian_value') return '#0f9f72'
  return '#d4ad00'
}

function actionStatusClass(status) {
  if (status === 'Approved' || status === 'Executed') return 'badge-success'
  if (status === 'Rejected') return 'badge-danger'
  return 'badge-warning'
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
