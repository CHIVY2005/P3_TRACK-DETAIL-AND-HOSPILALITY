import React, { useEffect, useRef, useState } from 'react'
import axios from 'axios'
import { Bot, CheckCircle2, ExternalLink, Mail, Send, Terminal, XCircle } from 'lucide-react'
import { API_BASE_URL } from '../api.js'

function AgentWorkspace() {
  const [tasks, setTasks] = useState([])
  const [activeTask, setActiveTask] = useState(null)
  const [actions, setActions] = useState([])
  const [briefing, setBriefing] = useState(null)
  const [runtimeStatus, setRuntimeStatus] = useState(null)
  const [running, setRunning] = useState(false)
  const [selectedAction, setSelectedAction] = useState(null)
  const [showEmailModal, setShowEmailModal] = useState(false)
  const [refreshMarketData, setRefreshMarketData] = useState(false)
  const terminalEndRef = useRef(null)

  const fetchHistory = async () => {
    try {
      const results = await Promise.allSettled([
        axios.get(`${API_BASE_URL}/agent/tasks?limit=10`),
        axios.get(`${API_BASE_URL}/agent/actions?limit=50`),
        axios.get(`${API_BASE_URL}/agent/briefing?limit=4`),
        axios.get(`${API_BASE_URL}/agent/runtime-status`),
      ])

      const tasksRes = results[0].status === 'fulfilled' ? results[0].value : null
      const actionsRes = results[1].status === 'fulfilled' ? results[1].value : null
      const briefingRes = results[2].status === 'fulfilled' ? results[2].value : null
      const runtimeRes = results[3].status === 'fulfilled' ? results[3].value : null

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
      }
    } catch (err) {
      console.error('Error fetching agent history', err)
    }
  }

  useEffect(() => {
    fetchHistory()
    const interval = setInterval(fetchHistory, 3000)
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
              disabled={running}
            />
            <span>Refresh live market data before the decision cycle</span>
          </label>
          <button className="btn btn-accent" onClick={handleRunAgent} disabled={running}>
            <Bot size={16} className={running ? 'pulse' : ''} />
            {running ? 'Cycle running...' : 'Run decision cycle'}
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
            <div className="terminal-title">guardian-agent / orchestrator</div>
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
                <div className="terminal-divider" />
                <div className="terminal-log-copy">{activeTask.logs}</div>
                {running ? <div className="blink">Coordinating tools and action proposals...</div> : null}
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
                        <div className="action-reasoning-box">
                          <strong>{decisionSummary.strategy === 'match' ? 'Why match' : 'Why negotiate'}</strong>
                          <p>{decisionSummary.reason}</p>
                          <div className="action-reasoning-metrics">
                            <span>{decisionSummary.competitor_name}</span>
                            <span>Guardian {formatCurrency(decisionSummary.guardian_price)}</span>
                            <span>Competitor {formatCurrency(decisionSummary.competitor_price)}</span>
                            <span>Margin if matched {formatPct(decisionSummary.margin_if_matched_pct)}</span>
                          </div>
                        </div>
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
                <div className="action-reasoning-box">
                  <strong>{selectedAction.email.decision_summary.strategy === 'match' ? 'Why match' : 'Why negotiate'}</strong>
                  <p>{selectedAction.email.decision_summary.reason}</p>
                  <div className="action-reasoning-metrics">
                    <span>{selectedAction.email.decision_summary.competitor_name}</span>
                    <span>Guardian {formatCurrency(selectedAction.email.decision_summary.guardian_price)}</span>
                    <span>Competitor {formatCurrency(selectedAction.email.decision_summary.competitor_price)}</span>
                    <span>Margin if matched {formatPct(selectedAction.email.decision_summary.margin_if_matched_pct)}</span>
                  </div>
                </div>
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

function mapActionStatusTone(status) {
  if (status === 'Approved' || status === 'Completed' || status === 'Executed') return 'good'
  if (status === 'Pending' || status === 'Running') return 'warn'
  if (status === 'Rejected' || status === 'Failed') return 'bad'
  return 'muted'
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

export default AgentWorkspace
