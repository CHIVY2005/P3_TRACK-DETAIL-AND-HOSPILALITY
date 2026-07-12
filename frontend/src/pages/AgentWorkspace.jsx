import React, { useEffect, useRef, useState } from 'react'
import axios from 'axios'
import { Bot, CheckCircle2, ExternalLink, Mail, Send, Sparkles, Terminal, Wrench, XCircle } from 'lucide-react'
import { API_BASE_URL } from '../api.js'
import { getCache, setCache } from '../dataCache.js'

function AgentWorkspace() {
  const cached = getCache('agentWorkspace')
  const [tasks, setTasks] = useState(cached?.tasks ?? [])
  const [activeTask, setActiveTask] = useState(cached?.activeTask ?? null)
  const [actions, setActions] = useState(cached?.actions ?? [])
  const [briefing, setBriefing] = useState(cached?.briefing ?? null)
  const [runtimeStatus, setRuntimeStatus] = useState(cached?.runtimeStatus ?? null)
  const [running, setRunning] = useState(false)
  const [selectedAction, setSelectedAction] = useState(null)
  const [showEmailModal, setShowEmailModal] = useState(false)
  const [refreshMarketData, setRefreshMarketData] = useState(false)
  const [floorPct, setFloorPct] = useState(cached?.floorPct ?? 15)
  const terminalEndRef = useRef(null)
  const liveRuntime = runtimeStatus?.agent?.live_runtime
  const liveActivity = liveRuntime?.activity || []
  const agentBusy = running || Boolean(runtimeStatus?.agent?.is_running)
  const agentRoster = [
    { key: 'orchestrator', label: 'Orchestrator', role: 'Coordinates the decision cycle' },
    { key: 'market_observer', label: 'Market Observer', role: 'Collects and normalizes market signals' },
    { key: 'margin_guardian', label: 'Margin Guardian', role: 'Checks price and margin safety' },
    { key: 'supplier_negotiator', label: 'Supplier Negotiator', role: 'Prepares cost-protection actions' },
  ]

  const fetchHistory = async () => {
    try {
      const [tasksRes, actionsRes, briefingRes, runtimeRes, configRes] = await Promise.all([
        axios.get(`${API_BASE_URL}/agent/tasks?limit=10`),
        axios.get(`${API_BASE_URL}/agent/actions?limit=50`),
        axios.get(`${API_BASE_URL}/agent/briefing?limit=4`),
        axios.get(`${API_BASE_URL}/agent/runtime-status`),
        axios.get(`${API_BASE_URL}/agent/config`).catch(() => null),
      ])

      if (configRes?.data?.min_margin != null) {
        setFloorPct(configRes.data.min_margin * 100)
      }
      setTasks(tasksRes.data)
      setActions(actionsRes.data)
      setBriefing(briefingRes.data)
      setRuntimeStatus(runtimeRes.data)
      setCache('agentWorkspace', {
        tasks: tasksRes.data,
        actions: actionsRes.data,
        briefing: briefingRes.data,
        runtimeStatus: runtimeRes.data,
        activeTask: tasksRes.data[0] ?? null,
        floorPct: configRes?.data?.min_margin != null ? configRes.data.min_margin * 100 : floorPct,
      })

      if (tasksRes) {
        setTasks(tasksRes.data)
        const active = tasksRes.data.find((task) => task.status === 'Running' || task.status === 'Pending')
        if (active) {
          setActiveTask(active)
          setRunning(true)
        } else {
          setRunning(false)
          if (tasksRes.data.length > 0) {
            setActiveTask(tasksRes.data[0])
          }
        }
      }
      if (actionsRes) {
        setActions(actionsRes.data)
      }
      if (briefingRes) {
        setBriefing(briefingRes.data)
      }
      if (runtimeRes) {
        setRuntimeStatus(runtimeRes.data)
        if (runtimeRes.data?.agent?.is_running) {
          setRunning(true)
        } else if (!tasksRes?.data?.some((task) => task.status === 'Running' || task.status === 'Pending')) {
          setRunning(false)
        }
      }
    } catch (err) {
      console.error('Error fetching agent history', err)
    }
  }

  const fetchRuntimeStatus = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/agent/runtime-status`)
      setRuntimeStatus(res.data)
      setRunning(Boolean(res.data?.agent?.is_running))
    } catch (err) {
      console.error('Error polling live agent runtime', err)
    }
  }

  useEffect(() => {
    fetchHistory()
    const interval = setInterval(fetchHistory, 8000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    fetchRuntimeStatus()
    const interval = setInterval(fetchRuntimeStatus, 1000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (!running || !activeTask) return

    const pollInterval = setInterval(async () => {
      try {
        const res = await axios.get(`${API_BASE_URL}/agent/tasks/${activeTask.id}`)
        setActiveTask(res.data)
        if (res.data.status !== 'Running' && res.data.status !== 'Pending') {
          setRunning(false)
          fetchHistory()
        }
      } catch (err) {
        console.error('Error polling agent task', err)
      }
    }, 1000)

    return () => clearInterval(pollInterval)
  }, [running, activeTask?.id])

  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [activeTask?.logs])

  const handleRunAgent = async () => {
    try {
      setRunning(true)
      const res = await axios.post(`${API_BASE_URL}/agent/run`, {
        refresh_market_data: refreshMarketData,
      })
      setActiveTask(res.data)
    } catch (err) {
      if (err.response?.status === 409) {
        alert('The agent is already running in the background.')
      } else {
        alert('Unable to start the agent.')
        setRunning(false)
      }
    }
  }

  const handleOpenActionDetails = (action) => {
    if (action.action_type !== 'SUPPLIER_EMAIL_DRAFT') {
      return
    }

    try {
      const emailData = parseActionPayload(action.data)
      setSelectedAction({ ...action, email: emailData })
      setShowEmailModal(true)
    } catch (err) {
      console.error('Failed to parse email data', err)
    }
  }

  const handleApproveAction = async (actionId) => {
    try {
      await axios.post(`${API_BASE_URL}/agent/actions/${actionId}/approve`)
      alert('Price match approved and applied to Guardian pricing.')
      fetchHistory()
    } catch (err) {
      alert(err.response?.data?.detail || 'Error while approving the action.')
    }
  }

  const handleRejectAction = async (actionId) => {
    try {
      await axios.post(`${API_BASE_URL}/agent/actions/${actionId}/reject`)
      alert('Action rejected and the related alert was dismissed.')
      fetchHistory()
    } catch (err) {
      alert(err.response?.data?.detail || 'Error while rejecting the action.')
    }
  }

  return (
    <div className="page-stack">
      <section className="header">
        <div className="header-title">
          <h1>Decision Desk</h1>
          <p>
            Review margin-safe recommendations, inspect decision evidence, and approve or reject every commercial
            action before execution.
          </p>
        </div>
        <div className="workspace-controls">
          <label className="toggle-row">
            <input
              type="checkbox"
              checked={refreshMarketData}
              onChange={(event) => setRefreshMarketData(event.target.checked)}
              disabled={agentBusy}
            />
            <span>Refresh live market data before the decision cycle</span>
          </label>
          <button className="btn btn-accent" onClick={handleRunAgent} disabled={agentBusy}>
            <Bot size={16} className={agentBusy ? 'pulse' : ''} />
            {agentBusy ? 'Cycle running...' : 'Run decision cycle'}
          </button>
        </div>
      </section>

      <div className="agent-console-container">
        <section className="terminal-shell">
          <div className="terminal-header">
            <div className="terminal-buttons">
              <span className="term-btn red" />
              <span className="term-btn yellow" />
              <span className="term-btn green" />
            </div>
            <div className="terminal-title">guardian-agent / {formatAgentName(liveRuntime?.active_agent || 'orchestrator')}</div>
            <Terminal size={14} style={{ color: 'var(--text-muted)' }} />
          </div>
          <div className="terminal-body">
            <div className="terminal-prompt">guardian-agent run --refresh-market-data={String(refreshMarketData)}</div>
            {activeTask ? (
              <>
                <div>Objective: {activeTask.objective}</div>
                <div>Started: {new Date(activeTask.started_at).toLocaleString('en-GB')}</div>
                <div className={`terminal-status terminal-status-${activeTask.status?.toLowerCase()}`}>
                  Status: [{activeTask.status}]
                </div>
                <div className="terminal-live-strip">
                  <span className={`status-pill ${agentBusy ? 'live' : 'muted'}`}>{agentBusy ? 'Live' : 'Idle'}</span>
                  <span>Agent: {formatAgentName(liveRuntime?.active_agent)}</span>
                  <span>Phase: {formatPhaseName(liveRuntime?.phase)}</span>
                  <span>Tool: {formatToolName(liveRuntime?.current_tool, liveRuntime?.tool_status)}</span>
                  {liveRuntime?.progress?.total ? (
                    <span>
                      Progress: {liveRuntime.progress.completed}/{liveRuntime.progress.total}
                    </span>
                  ) : null}
                </div>
                {liveRuntime?.current_product ? (
                  <div className="terminal-product-line">
                    SKU: {liveRuntime.current_product.name} | Product #{liveRuntime.current_product.id}
                  </div>
                ) : null}
                {liveRuntime?.current_thought ? (
                  <div className="terminal-thought-line">
                    THOUGHT: {liveRuntime.current_thought}
                  </div>
                ) : null}
                <div className="terminal-divider" />
                <div className="terminal-log-copy">{activeTask.logs}</div>
                {agentBusy ? <div className="blink">Coordinating tools and action proposals...</div> : null}
              </>
            ) : (
              <div className="terminal-empty">
                The agent is idle. Start a run to refresh pricing, reason over alerts, and open an approval queue.
              </div>
            )}
            <div ref={terminalEndRef} />
          </div>
        </section>

        <section className="actions-sidebar">
          <div className="section-card glass">
            <div className="section-header">
              <div className="section-title">Live agent state</div>
              <span className={`badge ${agentBusy ? 'badge-warning' : 'badge-info'}`}>{agentBusy ? 'Running' : 'Standby'}</span>
            </div>

            <div className="live-runtime-grid">
              <div className="live-runtime-card">
                <div className="live-runtime-label">
                  <Bot size={14} />
                  Active agent
                </div>
                <strong>{formatAgentName(liveRuntime?.active_agent)}</strong>
                <span>{formatPhaseName(liveRuntime?.phase)}</span>
              </div>
              <div className="live-runtime-card">
                <div className="live-runtime-label">
                  <Wrench size={14} />
                  Current tool
                </div>
                <strong>{formatToolName(liveRuntime?.current_tool, liveRuntime?.tool_status)}</strong>
                <span>{formatToolStatus(liveRuntime?.tool_status)}</span>
              </div>
            </div>

            <div className="live-thought-box">
              <div className="live-runtime-label">
                <Sparkles size={14} />
                Current thought
              </div>
              <p>{liveRuntime?.current_thought || 'No live reasoning message yet.'}</p>
            </div>

            <div className="live-tools-list">
              {(liveRuntime?.recent_tools || []).length > 0 ? (
                liveRuntime.recent_tools
                  .slice()
                  .reverse()
                  .map((toolEvent, index) => (
                    <div className="live-tool-row" key={`${toolEvent.name}-${toolEvent.at}-${index}`}>
                      <strong>{toolEvent.name}</strong>
                      <span className={`status-pill ${toolEvent.status === 'success' ? 'good' : toolEvent.status === 'error' ? 'bad' : 'warn'}`}>
                        {toolEvent.status}
                      </span>
                    </div>
                  ))
              ) : (
                <div className="empty-note">No tool execution captured yet.</div>
              )}
            </div>

            <div className="live-roster">
              <div className="live-runtime-label">Agent roster</div>
              {agentRoster.map((agent) => {
                const state = liveRuntime?.agent_states?.[agent.key]
                const status = state?.status || 'idle'
                return (
                  <div className="live-agent-row" key={agent.key}>
                    <span className={`agent-status-dot ${status}`} />
                    <div>
                      <strong>{agent.label}</strong>
                      <span>{status === 'active' ? formatPhaseName(state?.phase) : agent.role}</span>
                    </div>
                    <em>{statusLabel(status)}</em>
                  </div>
                )
              })}
            </div>

            <div className="live-timeline">
              <div className="live-runtime-label">Execution timeline</div>
              {liveActivity.length > 0 ? (
                liveActivity
                  .slice()
                  .reverse()
                  .slice(0, 8)
                  .map((item, index) => (
                    <div className="live-activity-row" key={`${item.at}-${index}`}>
                      <span className={`activity-marker ${item.status}`} />
                      <div>
                        <strong>{item.label}</strong>
                        <span>
                          {formatAgentName(item.agent)} | {formatPhaseName(item.phase)} | {formatShortTime(item.at)}
                        </span>
                      </div>
                    </div>
                  ))
              ) : (
                <div className="empty-note">Run the cycle to capture the live execution timeline.</div>
              )}
            </div>
          </div>

          <div className="section-card glass section-fill">
            <div className="section-header">
              <div className="section-title">Decision evidence & trace</div>
              {runtimeStatus?.agent?.last_trace_url ? (
                <a
                  className="inline-link-button"
                  href={runtimeStatus.agent.last_trace_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  <ExternalLink size={13} />
                  Open Langfuse trace
                </a>
              ) : (
                <span className="badge badge-info">Trace pending</span>
              )}
            </div>

            <div className="scroll-stack reasoning-stack">
              {briefing?.priority_queue?.length > 0 ? (
                briefing.priority_queue.map((item) => (
                  <article className="reasoning-card" key={item.alert_id}>
                    <div className="reasoning-card-top">
                      <strong>{item.product_name}</strong>
                      <span className={`status-pill ${item.strategy === 'match' ? 'good' : 'warn'}`}>
                        {item.strategy}
                      </span>
                    </div>
                    <div className="reasoning-card-top">
                      <span className={`status-pill ${qualityTone(item.confidence_label)}`}>
                        {item.confidence_label} evidence {formatPct(item.data_quality_pct)}
                      </span>
                    </div>
                    <p className="reasoning-copy">{item.rationale}</p>
                    <div className="reasoning-metrics">
                      <span>Gap {formatPct(item.price_gap_pct)}</span>
                      <span>Current {formatPct(item.current_margin_pct)}</span>
                      <span>If matched {formatPct(item.margin_if_matched_pct)}</span>
                    </div>
                    <div className="reasoning-footer">
                      <span>{item.competitor_name}</span>
                      <span>{item.recommended_action}</span>
                    </div>
                  </article>
                ))
              ) : (
                <div className="empty-note">No decision evidence yet. Run a cycle or wait for fresh alerts.</div>
              )}
            </div>
          </div>

          <div className="section-card glass section-fill">
            <div className="section-header">
              <div className="section-title">Action queue</div>
              <span className="badge badge-info">{actions.length} records</span>
            </div>

            <div className="scroll-stack">
              {actions.length > 0 ? (
                actions.map((action) => {
                  const payload = parseActionPayload(action.data)
                  const decisionSummary = payload?.decision_summary

                  return (
                    <div className="action-card-item" key={action.id}>
                      <div className="action-card-header">
                        <span className={`action-type-badge ${action.action_type === 'AUTO_PRICE_MATCH' ? 'match' : 'draft'}`}>
                          {action.action_type === 'AUTO_PRICE_MATCH' ? 'Price alignment' : 'Supplier draft'}
                        </span>
                        <span className="action-card-time">
                          {new Date(action.created_at).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>

                      <div className="action-status-line">
                        <span className={`status-pill ${mapActionStatusTone(action.status)}`}>{action.status}</span>
                      </div>

                      <p className="action-card-desc">{action.description}</p>

                      {decisionSummary ? (
                        <MarginExplainer summary={decisionSummary} floorPct={floorPct} />
                      ) : null}

                      {action.action_type === 'SUPPLIER_EMAIL_DRAFT' ? (
                        <button className="inline-link-button" onClick={() => handleOpenActionDetails(action)}>
                          <Mail size={13} />
                          Open draft
                        </button>
                      ) : null}

                      {action.status === 'Pending' && action.action_type === 'AUTO_PRICE_MATCH' ? (
                        <div className="action-approval-row">
                          <button className="btn btn-accent btn-compact" onClick={() => handleApproveAction(action.id)}>
                            <CheckCircle2 size={14} />
                            Approve
                          </button>
                          <button className="btn btn-secondary btn-compact" onClick={() => handleRejectAction(action.id)}>
                            <XCircle size={14} />
                            Reject
                          </button>
                        </div>
                      ) : null}
                    </div>
                  )
                })
              ) : (
                <div className="empty-note">No actions have been created yet.</div>
              )}
            </div>
          </div>
        </section>
      </div>

      <section className="section-card glass">
        <div className="section-header">
          <div className="section-title">Recent task history</div>
        </div>
        <div className="history-grid">
          {tasks.length > 0 ? (
            tasks.map((task) => (
              <div key={task.id} className="history-card">
                <div className="history-card-top">
                  <strong>Run #{task.id}</strong>
                  <span className={`status-pill ${mapActionStatusTone(task.status)}`}>{task.status}</span>
                </div>
                <p>{task.objective}</p>
                <span>{new Date(task.started_at).toLocaleString('en-GB')}</span>
              </div>
            ))
          ) : (
            <div className="empty-note">No agent tasks yet.</div>
          )}
        </div>
      </section>

      {showEmailModal && selectedAction ? (
        <div className="modal-overlay">
          <div className="modal-content glass">
            <div className="modal-header">
              <h3>Supplier support draft</h3>
              <button className="modal-close" onClick={() => setShowEmailModal(false)}>
                ×
              </button>
            </div>

            <div className="email-draft-container">
              {selectedAction.email.decision_summary ? (
                <MarginExplainer summary={selectedAction.email.decision_summary} floorPct={floorPct} />
              ) : null}
              <div className="email-field">
                <span className="email-field-label">Subject</span>
                <span className="email-field-val">
                  <strong>{selectedAction.email.subject}</strong>
                </span>
              </div>
              <div className="email-field">
                <span className="email-field-label">Recipient</span>
                <span className="email-field-val">{selectedAction.email.recipient || 'Supplier account owner'}</span>
              </div>
              <div className="email-body-text">{selectedAction.email.body}</div>
            </div>

            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setShowEmailModal(false)}>
                Close
              </button>
              <button
                className="btn btn-accent"
                onClick={() => {
                  alert('Draft marked as ready for supplier outreach.')
                  setShowEmailModal(false)
                }}
              >
                <Send size={14} />
                Mark ready
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}

function MarginExplainer({ summary, floorPct }) {
  const current = summary.current_margin_pct
  const matched = summary.margin_if_matched_pct
  const floor = typeof floorPct === 'number' ? floorPct : 15
  const isMatch = summary.strategy === 'match'
  const belowFloor = typeof matched === 'number' && matched < floor

  const values = [current, matched, floor].filter((v) => typeof v === 'number')
  const scaleMax = Math.max(1, ...values.map((v) => Math.abs(v)))
  const widthOf = (v) => (typeof v === 'number' ? `${Math.max(0, (v / scaleMax) * 100)}%` : '0%')

  const rows = [
    { key: 'current', label: 'Biên hiện tại', value: current, tone: 'neutral' },
    { key: 'floor', label: `Sàn tối thiểu (${floor.toFixed(0)}%)`, value: floor, tone: 'floor' },
    {
      key: 'matched',
      label: 'Biên nếu match giá',
      value: matched,
      tone: belowFloor ? 'bad' : 'good',
    },
  ]

  const conclusion = isMatch
    ? `Match giá vẫn giữ biên ${formatPct(matched)} (trên sàn ${floor.toFixed(0)}%) → ĐỀ XUẤT MATCH`
    : `Match giá sẽ kéo biên xuống ${formatPct(matched)} (dưới sàn ${floor.toFixed(0)}%) → ĐÀM PHÁN NCC`

  return (
    <div className={`margin-explainer ${isMatch ? 'is-match' : 'is-negotiate'}`}>
      {summary.product_name ? <div className="margin-explainer-product">{summary.product_name}</div> : null}
      <div className="margin-explainer-head">
        <strong>Vì sao {isMatch ? 'MATCH' : 'NEGOTIATE'}?</strong>
        <span>{summary.competitor_name}</span>
      </div>
      <div className="margin-bars">
        {rows.map((row) => (
          <div className="margin-bar-row" key={row.key}>
            <span className="margin-bar-label">{row.label}</span>
            <div className="margin-bar-track">
              <span className={`margin-bar-fill tone-${row.tone}`} style={{ width: widthOf(row.value) }} />
            </div>
            <span className={`margin-bar-value tone-${row.tone}`}>
              {formatPct(row.value)}
              {row.key === 'matched' && belowFloor ? ' ✗' : ''}
            </span>
          </div>
        ))}
      </div>
      <p className={`margin-conclusion ${belowFloor ? 'bad' : 'good'}`}>{conclusion}</p>
      <div className="margin-explainer-foot">
        <span>Guardian {formatCurrency(summary.guardian_price)}</span>
        <span>Đối thủ {formatCurrency(summary.competitor_price)}</span>
        {typeof summary.price_gap_pct === 'number' ? <span>Chênh giá {formatPct(summary.price_gap_pct)}</span> : null}
      </div>
    </div>
  )
}

function mapActionStatusTone(status) {
  if (status === 'Approved' || status === 'Completed' || status === 'Executed') return 'good'
  if (status === 'Pending' || status === 'Running') return 'warn'
  if (status === 'Rejected' || status === 'Failed') return 'bad'
  return 'muted'
}

function qualityTone(label) {
  if (label === 'High') return 'good'
  if (label === 'Medium') return 'warn'
  return 'bad'
}

function formatPct(value) {
  if (typeof value !== 'number') return '--'
  return `${value.toFixed(1)}%`
}

function formatCurrency(value) {
  if (typeof value !== 'number') return '--'
  return `${value.toLocaleString('en-GB')} VND`
}

function parseActionPayload(rawData) {
  if (!rawData) return null
  try {
    return JSON.parse(rawData)
  } catch (err) {
    return null
  }
}

function formatAgentName(value) {
  if (!value) return 'Waiting'
  return value
    .split('_')
    .map((part) => `${part.charAt(0).toUpperCase()}${part.slice(1)}`)
    .join(' ')
}

function formatPhaseName(value) {
  if (!value) return 'Idle'
  return value
    .split('_')
    .map((part) => `${part.charAt(0).toUpperCase()}${part.slice(1)}`)
    .join(' ')
}

function formatToolName(name, status) {
  if (!name) return status === 'success' ? 'Completed' : 'Waiting'
  return name
    .split('_')
    .map((part) => `${part.charAt(0).toUpperCase()}${part.slice(1)}`)
    .join(' ')
}

function formatToolStatus(value) {
  if (!value) return 'No tool in flight'
  if (value === 'running') return 'Tool executing now'
  if (value === 'success') return 'Latest tool completed'
  if (value === 'error') return 'Latest tool failed'
  return value
}

function statusLabel(value) {
  if (value === 'active') return 'Working'
  if (value === 'completed') return 'Done'
  return 'Standby'
}

function formatShortTime(value) {
  if (!value) return '--:--:--'
  return new Date(value).toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

export default AgentWorkspace
