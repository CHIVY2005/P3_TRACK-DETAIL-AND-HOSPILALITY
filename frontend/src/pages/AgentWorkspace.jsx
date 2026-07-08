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

  const [refreshMarketData, setRefreshMarketData] = useState(false)

  const handleRunAgent = async () => {
    try {
      setRunning(true)
      const res = await axios.post(`${API_BASE_URL}/agent/run`, {
        refresh_market_data: refreshMarketData
      })
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

  const handleApproveAction = async (actionId) => {
    try {
      await axios.post(`${API_BASE_URL}/agent/actions/${actionId}/approve`)
      alert('Đã phê duyệt hành động khớp giá thành công! Giá của Guardian đã được đồng bộ.')
      fetchHistory()
    } catch (err) {
      alert(err.response?.data?.detail || 'Lỗi khi phê duyệt hành động.')
    }
  }

  const handleRejectAction = async (actionId) => {
    try {
      await axios.post(`${API_BASE_URL}/agent/actions/${actionId}/reject`)
      alert('Đã từ chối hành động. Cảnh báo đã được đóng.')
      fetchHistory()
    } catch (err) {
      alert(err.response?.data?.detail || 'Lỗi khi từ chối hành động.')
    }
  }

  return (
    <div>
      {/* Header */}
      <div className="header">
        <div className="header-title">
          <h1>AI Agent Workspace</h1>
          <p>Agent tự refresh dữ liệu thị trường, phân tích biên lợi nhuận, rồi đề xuất hành động giá để con người duyệt.</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: 'var(--text-muted)', cursor: 'pointer', userSelect: 'none' }}>
            <input 
              type="checkbox" 
              checked={refreshMarketData} 
              onChange={(e) => setRefreshMarketData(e.target.checked)} 
              disabled={running}
              style={{ cursor: 'pointer' }}
            />
            Cào lại dữ liệu thị trường thực tế (chậm)
          </label>
          <button 
            className="btn btn-accent"
            onClick={handleRunAgent}
            disabled={running}
            style={{ padding: '12px 24px' }}
          >
            <Cpu size={18} className={running ? 'pulse' : ''} />
            {running ? 'Agent đang chạy...' : 'Chạy autonomous agent'}
          </button>
        </div>
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
              guardian-agent run --refresh-market-data
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
                Hệ thống Agent đang ở chế độ chờ. Hãy bấm "Chạy autonomous agent" để agent tự cào, tự phân tích, và tạo action queue.
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
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '4px 0' }}>
                      <span className={`action-status-badge ${act.status.toLowerCase()}`} style={{
                        fontSize: '10px',
                        padding: '2px 6px',
                        borderRadius: '4px',
                        fontWeight: '700',
                        textTransform: 'uppercase',
                        background: act.status === 'Pending' ? 'rgba(245, 158, 11, 0.1)' : act.status === 'Approved' ? 'rgba(16, 185, 129, 0.1)' : act.status === 'Rejected' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(107, 114, 128, 0.1)',
                        color: act.status === 'Pending' ? '#f59e0b' : act.status === 'Approved' ? '#10b981' : act.status === 'Rejected' ? '#ef4444' : '#9ca3af'
                      }}>
                        {act.status === 'Pending' ? 'Chờ Duyệt' : act.status === 'Approved' ? 'Đã Duyệt' : act.status === 'Rejected' ? 'Từ Chối' : 'Đã Chạy'}
                      </span>
                    </div>
                    <p className="action-card-desc" style={{ color: 'var(--text-main)', fontSize: '13px', marginTop: '6px' }}>
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
                    {act.status === 'Pending' && act.action_type === 'AUTO_PRICE_MATCH' && (
                      <div style={{ display: 'flex', gap: '8px', marginTop: '10px' }}>
                        <button 
                          className="btn btn-accent" 
                          style={{ padding: '6px 12px', fontSize: '11px', borderRadius: '4px', background: 'var(--primary)', color: '#0f172a' }}
                          onClick={() => handleApproveAction(act.id)}
                        >
                          Duyệt Khớp Giá
                        </button>
                        <button 
                          className="btn btn-secondary" 
                          style={{ padding: '6px 12px', fontSize: '11px', borderRadius: '4px', borderColor: 'var(--danger)', color: 'var(--danger)' }}
                          onClick={() => handleRejectAction(act.id)}
                        >
                          Từ Chối
                        </button>
                      </div>
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
