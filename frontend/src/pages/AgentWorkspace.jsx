import React, { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import { API_BASE_URL } from '../App.jsx'
import { Cpu, Terminal, CheckCircle2, AlertTriangle, FileText, Send, Mail } from 'lucide-react'

function AgentWorkspace() {
  const [tasks, setTasks] = useState([])
  const [activeTask, setActiveTask] = useState(null)
  const [actions, setActions] = useState([])
  const [running, setRunning] = useState(false)
  const [selectedAction, setSelectedAction] = useState(null)
  const [showEmailModal, setShowEmailModal] = useState(false)
  const terminalEndRef = useRef(null)

  const fetchHistory = async () => {
    try {
      const tasksRes = await axios.get(`${API_BASE_URL}/agent/tasks?limit=10`)
      setTasks(tasksRes.data)
      
      const actionsRes = await axios.get(`${API_BASE_URL}/agent/actions?limit=50`)
      setActions(actionsRes.data)

      // Find if there is an active running/pending task
      const active = tasksRes.data.find(t => t.status === 'Running' || t.status === 'Pending')
      if (active) {
        setActiveTask(active)
        setRunning(true)
      } else {
        setRunning(false)
        if (tasksRes.data.length > 0 && !activeTask) {
          setActiveTask(tasksRes.data[0])
        }
      }
    } catch (err) {
      console.error('Error fetching agent history', err)
    }
  }

  // 1. Initial Load and periodic status check
  useEffect(() => {
    fetchHistory()
    const interval = setInterval(fetchHistory, 3000)
    return () => clearInterval(interval)
  }, [])

  // 2. Poll the active task details while it's running
  useEffect(() => {
    if (!running || !activeTask) return

    let pollInterval = setInterval(async () => {
      try {
        const res = await axios.get(`${API_BASE_URL}/agent/tasks/${activeTask.id}`)
        setActiveTask(res.data)
        if (res.data.status !== 'Running' && res.data.status !== 'Pending') {
          setRunning(false)
          fetchHistory() // Refresh full history
        }
      } catch (err) {
        console.error('Error polling agent task', err)
      }
    }, 1000)

    return () => clearInterval(pollInterval)
  }, [running, activeTask?.id])

  // Scroll to bottom of terminal logs
  useEffect(() => {
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [activeTask?.logs])

  const handleRunAgent = async () => {
    try {
      setRunning(true)
      const res = await axios.post(`${API_BASE_URL}/agent/run`)
      setActiveTask(res.data)
    } catch (err) {
      if (err.response && err.response.status === 409) {
        alert('Agent đang chạy trong background rồi!')
      } else {
        alert('Không thể kích hoạt Agent.')
        setRunning(false)
      }
    }
  }

  const handleOpenActionDetails = (action) => {
    if (action.action_type === 'SUPPLIER_EMAIL_DRAFT') {
      try {
        const emailData = JSON.parse(action.data)
        setSelectedAction({
          ...action,
          email: emailData
        })
        setShowEmailModal(true)
      } catch (e) {
        console.error('Failed to parse email data', e)
      }
    } else {
      alert(`Hành động tối ưu giá tự động: ${action.description}`)
    }
  }

  return (
    <div>
      {/* Header */}
      <div className="header">
        <div className="header-title">
          <h1>AI Agent Workspace</h1>
          <p>Kích hoạt và giám sát các tác vụ định giá, tính toán biên lợi nhuận, và soạn thảo thư thương lượng tự động.</p>
        </div>
        <button 
          className="btn btn-accent"
          onClick={handleRunAgent}
          disabled={running}
          style={{ padding: '12px 24px' }}
        >
          <Cpu size={18} className={running ? 'pulse' : ''} />
          {running ? 'Agent đang chạy...' : 'Kích hoạt Pricing Agent'}
        </button>
      </div>

      {/* Terminal Grid */}
      <div className="agent-console-container">
        {/* Terminal Screen */}
        <div className="terminal">
          <div className="terminal-header">
            <div className="terminal-buttons">
              <span className="term-btn red" />
              <span className="term-btn yellow" />
              <span className="term-btn green" />
            </div>
            <div className="terminal-title">CM-PRICING-AGENT-SHELL</div>
            <Terminal size={14} style={{ color: 'var(--text-muted)' }} />
          </div>
          <div className="terminal-body">
            <div className="terminal-prompt" style={{ marginBottom: '8px' }}>
              systemctl start guardian-pricing-agent.service
            </div>
            {activeTask ? (
              <>
                <div>Tác vụ: {activeTask.objective}</div>
                <div>Bắt đầu: {new Date(activeTask.started_at).toLocaleString('vi-VN')}</div>
                <div style={{ color: activeTask.status === 'Completed' ? '#10b981' : activeTask.status === 'Failed' ? '#ef4444' : '#f59e0b', fontWeight: 'bold', margin: '4px 0' }}>
                  Trạng thái: [{activeTask.status}]
                </div>
                <div style={{ borderBottom: '1px dashed var(--border-color)', margin: '12px 0' }} />
                <div style={{ whiteSpace: 'pre-wrap', color: '#cbd5e1' }}>
                  {activeTask.logs}
                </div>
                {running && (
                  <div className="blink" style={{ color: 'var(--primary)', marginTop: '8px' }}>
                    █ Đang phân tích và đưa ra Tool Call...
                  </div>
                )}
              </>
            ) : (
              <div style={{ color: 'var(--text-muted)', paddingTop: '20px' }}>
                Hệ thống Agent đang ở chế độ chờ. Hãy bấm "Kích hoạt Pricing Agent" ở trên để khởi chạy chu trình tối ưu.
              </div>
            )}
            <div ref={terminalEndRef} />
          </div>
        </div>

        {/* Sidebar Actions log */}
        <div className="actions-sidebar">
          <div className="section-card glass" style={{ flexGrow: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <div className="section-header" style={{ marginBottom: '16px' }}>
              <div className="section-title">Hành Động Đã Thực Hiện</div>
              <span className="badge badge-info">{actions.length} Actions</span>
            </div>

            <div style={{ flexGrow: 1, overflowY: 'auto', paddingRight: '4px' }}>
              {actions.length > 0 ? (
                actions.map((act) => (
                  <div className="action-card-item" key={act.id}>
                    <div className="action-card-header">
                      <span className={`action-type-badge ${act.action_type === 'AUTO_PRICE_MATCH' ? 'match' : 'draft'}`}>
                        {act.action_type === 'AUTO_PRICE_MATCH' ? 'Match Giá Tự Động' : 'Thư Thương Lượng'}
                      </span>
                      <span className="action-card-time">
                        {new Date(act.created_at).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <p className="action-card-desc" style={{ color: 'var(--text-main)', fontSize: '13px' }}>
                      {act.description}
                    </p>
                    {act.action_type === 'SUPPLIER_EMAIL_DRAFT' && (
                      <button 
                        className="action-card-details-btn"
                        onClick={() => handleOpenActionDetails(act)}
                      >
                        <Mail size={12} />
                        Xem Thư Đề Xuất
                      </button>
                    )}
                  </div>
                ))
              ) : (
                <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '40px 0' }}>
                  Chưa ghi nhận hành động nào từ Agent.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Supplier Email Modal Overlay */}
      {showEmailModal && selectedAction && (
        <div className="modal-overlay">
          <div className="modal-content glass">
            <div className="modal-header">
              <h3 style={{ fontSize: '18px', fontWeight: '700', fontFamily: 'Outfit' }}>Thư Đề Xuất Hỗ Trợ Giá Gửi Nhà Cung Cấp</h3>
              <button className="modal-close" onClick={() => setShowEmailModal(false)} style={{ fontSize: '20px' }}>✕</button>
            </div>
            
            <div className="email-draft-container">
              <div className="email-field">
                <span className="email-field-label">Tiêu đề:</span>
                <span className="email-field-val"><strong>{selectedAction.email.subject}</strong></span>
              </div>
              <div className="email-field">
                <span className="email-field-label">Người nhận:</span>
                <span className="email-field-val">Supplier Account Manager (Auto-allocated)</span>
              </div>
              <div style={{ borderBottom: '1px solid var(--border-color)', margin: '12px 0' }} />
              <div className="email-body-text">{selectedAction.email.body}</div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '20px' }}>
              <button className="btn btn-secondary" onClick={() => setShowEmailModal(false)}>Đóng</button>
              <button 
                className="btn btn-accent" 
                onClick={() => {
                  alert('Đã gửi email đề xuất chi phí đến đại diện Supplier thành công!')
                  setShowEmailModal(false)
                }}
              >
                <Send size={14} />
                Gửi Email
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default AgentWorkspace
