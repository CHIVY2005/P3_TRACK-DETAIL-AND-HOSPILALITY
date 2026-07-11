import React, { useEffect, useState } from 'react'
import axios from 'axios'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { BarChart3, Coins } from 'lucide-react'
import { API_BASE_URL } from '../api.js'
import { getCache, setCache } from '../dataCache.js'

// CVD-safe pair (teal / amber) — used for the two identity series.
const COLOR_GUARDIAN = '#0f766e'
const COLOR_COMPETITOR = '#e8833a'
const COLOR_COST = '#0f766e'

function Visualization() {
  const cached = getCache('visualization')
  const [data, setData] = useState(cached ?? null)
  const [loading, setLoading] = useState(!cached)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await axios.get(`${API_BASE_URL}/pricing/visualization`)
        setData(res.data)
        setCache('visualization', res.data)
      } catch (err) {
        console.error('Error fetching visualization data', err)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 8000)
    return () => clearInterval(interval)
  }, [])

  const channels = data?.channels ?? []
  const totals = data?.totals ?? { scrape_count: 0, scrape_cost_total: 0 }

  return (
    <div className="page-stack">
      <section className="header">
        <div className="header-title">
          <h1>Visualization</h1>
          <p>Compare Guardian pricing against competitors per channel and track scraping cost.</p>
        </div>
      </section>

      <div className="viz-kpi-grid">
        <div className="viz-kpi section-card glass">
          <span className="viz-kpi-label">
            <Coins size={14} /> Total scraping cost
          </span>
          <strong className="viz-kpi-value">{formatCurrency(totals.scrape_cost_total)}</strong>
        </div>
        <div className="viz-kpi section-card glass">
          <span className="viz-kpi-label">
            <BarChart3 size={14} /> Total scrapes
          </span>
          <strong className="viz-kpi-value">{totals.scrape_count.toLocaleString('en-GB')}</strong>
        </div>
        <div className="viz-kpi section-card glass">
          <span className="viz-kpi-label">Channels tracked</span>
          <strong className="viz-kpi-value">{channels.length}</strong>
        </div>
      </div>

      <section className="section-card glass">
        <div className="section-header">
          <div className="section-title">Average price: Guardian vs competitor by channel</div>
        </div>
        <div className="chart-frame">
          {channels.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={channels} margin={{ top: 12, right: 12, left: 4, bottom: 8 }} barGap={2}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(47, 79, 79, 0.12)" vertical={false} />
                <XAxis dataKey="channel" stroke="var(--text-muted)" fontSize={12} />
                <YAxis
                  stroke="var(--text-muted)"
                  fontSize={11}
                  tickFormatter={(val) => `${Math.round(val / 1000)}k`}
                />
                <Tooltip
                  cursor={{ fill: 'rgba(15, 118, 110, 0.06)' }}
                  contentStyle={tooltipStyle}
                  formatter={(value, name) => [formatCurrency(value), name]}
                />
                <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: '13px' }} />
                <Bar dataKey="avg_guardian_price" name="Guardian" fill={COLOR_GUARDIAN} radius={[4, 4, 0, 0]} />
                <Bar dataKey="avg_net_price" name="Competitor (net)" fill={COLOR_COMPETITOR} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-chart">{loading ? 'Loading...' : 'No channel data yet.'}</div>
          )}
        </div>
      </section>

      <div className="dashboard-grid dashboard-grid-wide">
        <section className="section-card glass">
          <div className="section-header">
            <div className="section-title">Scraping cost by channel</div>
            <span className="badge badge-info">VND</span>
          </div>
          <div className="chart-frame">
            {channels.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={channels} margin={{ top: 12, right: 12, left: 4, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(47, 79, 79, 0.12)" vertical={false} />
                  <XAxis dataKey="channel" stroke="var(--text-muted)" fontSize={12} />
                  <YAxis
                    stroke="var(--text-muted)"
                    fontSize={11}
                    tickFormatter={(val) => `${Math.round(val / 1000)}k`}
                  />
                  <Tooltip
                    cursor={{ fill: 'rgba(15, 118, 110, 0.06)' }}
                    contentStyle={tooltipStyle}
                    formatter={(value, _name, item) => [
                      `${formatCurrency(value)} (${item.payload.scrape_count} runs × ${formatCurrency(item.payload.scrape_cost_unit)})`,
                      'Cost',
                    ]}
                  />
                  <Bar dataKey="scrape_cost_total" radius={[4, 4, 0, 0]}>
                    {channels.map((entry) => (
                      <Cell key={entry.channel} fill={COLOR_COST} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="empty-chart">{loading ? 'Loading...' : 'No cost data yet.'}</div>
            )}
          </div>
        </section>

        <section className="section-card glass">
          <div className="section-header">
            <div className="section-title">Cost breakdown</div>
          </div>
          <div className="data-table-container">
            <table className="data-table viz-table">
              <thead>
                <tr>
                  <th>Channel</th>
                  <th className="num">Unit cost / run</th>
                  <th className="num">Scrapes</th>
                  <th className="num">Total cost</th>
                </tr>
              </thead>
              <tbody>
                {channels.map((channel) => (
                  <tr key={channel.channel}>
                    <td>{channel.channel}</td>
                    <td className="num">{formatCurrency(channel.scrape_cost_unit)}</td>
                    <td className="num">{channel.scrape_count}</td>
                    <td className="num">{formatCurrency(channel.scrape_cost_total)}</td>
                  </tr>
                ))}
                {channels.length > 0 ? (
                  <tr className="table-total-row">
                    <td>Total</td>
                    <td className="num">—</td>
                    <td className="num">{totals.scrape_count}</td>
                    <td className="num">{formatCurrency(totals.scrape_cost_total)}</td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  )
}

const tooltipStyle = {
  backgroundColor: '#ffffff',
  borderColor: 'rgba(15, 23, 42, 0.12)',
  color: 'var(--text-main)',
  borderRadius: '8px',
}

function formatCurrency(value) {
  if (typeof value !== 'number') return '--'
  return `${Math.round(value).toLocaleString('en-GB')} VND`
}

export default Visualization
