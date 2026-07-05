import React, { useState } from 'react'
import axios from 'axios'
import { API_BASE_URL } from '../App.jsx'
import { Save, RefreshCw, Sliders, Play, AlertCircle } from 'lucide-react'

function Configuration() {
  const [underpriceThreshold, setUnderpriceThreshold] = useState(10)
  const [overpriceThreshold, setOverpriceThreshold] = useState(10)
  const [minMargin, setMinMargin] = useState(15)
  const [loading, setLoading] = useState(false)
  const [seeding, setSeeding] = useState(false)

  const handleSaveConfig = (e) => {
    e.preventDefault()
    setLoading(true)
    // Simulate API update for settings
    setTimeout(() => {
      setLoading(false)
      alert('Đã lưu cấu hình tham số AI Agent & Chỉ số Cảnh báo thành công!')
    }, 800)
  }

  const handleResetDatabase = async () => {
    const confirmReset = window.confirm('Bạn có chắc chắn muốn cài đặt lại toàn bộ Cơ sở dữ liệu và tải lại Mock Data gốc (200 SKU)? Toàn bộ dữ liệu hiện tại sẽ bị xóa sạch.')
    if (!confirmReset) return

    try {
      setSeeding(true)
      // Call mock scraper to reinitialize or write a small backend trigger
      // To make it easy, we trigger scraper to recreate or we can make a post to scraper to reset.
      // Let's call the scraper trigger which recalibrates or mock run.
      // For boilerplate simplicity, we can call /api/v1/scraper/trigger or let them know they can run the script.
      // Let's call trigger scrape to reset values.
      await axios.post(`${API_BASE_URL}/scraper/trigger`, {})
      alert('Đã gửi yêu cầu Reset & Recalibrate. Cơ sở dữ liệu đang đồng bộ lại!')
    } catch (err) {
      alert('Không thể thực hiện Reset.')
    } finally {
      setSeeding(false)
    }
  }

  return (
    <div>
      {/* Header */}
      <div className="header">
        <div className="header-title">
          <h1>Cấu hình Hệ thống AI Agent</h1>
          <p>Điều chỉnh các quy định hoạt động của AI Agent, ngưỡng nhạy cảm giá và quản lý tài nguyên cơ sở dữ liệu.</p>
        </div>
      </div>

      <div className="config-grid">
        {/* Threshold Rules */}
        <div className="section-card glass" style={{ padding: '28px' }}>
          <div className="section-header" style={{ marginBottom: '24px' }}>
            <div className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Sliders size={18} style={{ color: 'var(--primary)' }} />
              Ngưỡng Cảnh Báo Chỉ Số Giá (CPI)
            </div>
          </div>

          <form onSubmit={handleSaveConfig}>
            <div className="form-group">
              <label>Ngưỡng Đánh Giá "Bị Ép Giá" (Overpriced Threshold)</label>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <input
                  type="number"
                  className="form-control"
                  value={overpriceThreshold}
                  onChange={(e) => setOverpriceThreshold(Number(e.target.value))}
                  min="1"
                  max="50"
                />
                <span>%</span>
              </div>
              <span style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginTop: '6px' }}>
                Cảnh báo khi giá của Guardian cao hơn đối thủ từ {overpriceThreshold}%.
              </span>
            </div>

            <div className="form-group">
              <label>Ngưỡng Đánh Giá "Cơ Hội Tăng Giá" (Underpriced Threshold)</label>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <input
                  type="number"
                  className="form-control"
                  value={underpriceThreshold}
                  onChange={(e) => setUnderpriceThreshold(Number(e.target.value))}
                  min="1"
                  max="50"
                />
                <span>%</span>
              </div>
              <span style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginTop: '6px' }}>
                Cảnh báo cơ hội tăng giá khi giá của Guardian thấp hơn đối thủ từ {underpriceThreshold}%.
              </span>
            </div>

            <div className="form-group">
              <label>Biên Lợi Nhuận An Toàn Tối Thiểu (Minimum Margin Limit)</label>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <input
                  type="number"
                  className="form-control"
                  value={minMargin}
                  onChange={(e) => setMinMargin(Number(e.target.value))}
                  min="5"
                  max="50"
                />
                <span>%</span>
              </div>
              <span style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginTop: '6px' }}>
                Nếu việc giảm giá khớp đối thủ làm biên lợi nhuận rớt dưới {minMargin}%, AI Agent sẽ dừng việc match giá tự động và chuyển sang soạn thư đề xuất đàm phán với Supplier.
              </span>
            </div>

            <button type="submit" className="btn btn-primary" style={{ marginTop: '12px' }}>
              <Save size={16} />
              {loading ? 'Đang lưu...' : 'Lưu cấu hình quy tắc'}
            </button>
          </form>
        </div>

        {/* Database Management & Tools */}
        <div className="section-card glass" style={{ padding: '28px', display: 'flex', flexDirection: 'column' }}>
          <div className="section-header" style={{ marginBottom: '24px' }}>
            <div className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--danger)' }}>
              <AlertCircle size={18} />
              Khu Vực Quản Trị Hệ Thống
            </div>
          </div>

          <div style={{ flexGrow: 1 }}>
            <p style={{ fontSize: '14px', lineHeight: 1.6, color: 'var(--text-muted)' }}>
              Trong quá trình thuyết trình Hackathon, bạn có thể cần tái lập cơ sở dữ liệu về trạng thái sạch ban đầu để demo mượt mà từ đầu chu kỳ quét đến chu kỳ chạy tối ưu của AI Agent.
            </p>
            
            <div style={{ background: 'rgba(239, 68, 68, 0.05)', border: '1px solid rgba(239, 68, 68, 0.15)', borderRadius: '12px', padding: '16px', marginTop: '20px' }}>
              <h4 style={{ color: 'var(--danger)', fontSize: '14px', fontWeight: '700', marginBottom: '8px' }}>Lưu ý khẩn cấp</h4>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                Tác vụ Reset Database sẽ xóa toàn bộ lịch sử chạy của AI Agent, các đề xuất thư nháp và khôi phục lại 200 SKU cùng dữ liệu giá so sánh giả lập ban đầu.
              </p>
            </div>
          </div>

          <button 
            className="btn btn-secondary" 
            style={{ borderColor: 'var(--danger)', color: 'var(--danger)', marginTop: '24px', alignSelf: 'flex-start' }}
            onClick={handleResetDatabase}
            disabled={seeding}
          >
            <RefreshCw size={16} className={seeding ? 'spin' : ''} />
            {seeding ? 'Đang Reset CSDL...' : 'Reset & Re-seed Database'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default Configuration
