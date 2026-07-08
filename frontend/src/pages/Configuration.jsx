import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { API_BASE_URL } from '../App.jsx'
import { Save, RefreshCw, Sliders, Play, AlertCircle } from 'lucide-react'

function Configuration() {
  const [underpriceThreshold, setUnderpriceThreshold] = useState(10)
  const [overpriceThreshold, setOverpriceThreshold] = useState(10)
  const [minMargin, setMinMargin] = useState(15)
  const [customInstruction, setCustomInstruction] = useState('')
  const [loading, setLoading] = useState(false)
  const [seeding, setSeeding] = useState(false)
  const [csvFile, setCsvFile] = useState(null)
  const [uploading, setUploading] = useState(false)

  // Fetch config on mount
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const res = await axios.get(`${API_BASE_URL}/agent/config`)
        setUnderpriceThreshold(Math.round(res.data.underprice_threshold * 100))
        setOverpriceThreshold(Math.round(res.data.overprice_threshold * 100))
        setMinMargin(Math.round(res.data.min_margin * 100))
        setCustomInstruction(res.data.custom_instruction || '')
      } catch (err) {
        console.error('Error loading config', err)
      }
    }
    fetchConfig()
  }, [])

  const handleSaveConfig = async (e) => {
    e.preventDefault()
    try {
      setLoading(true)
      await axios.post(`${API_BASE_URL}/agent/config`, {
        underprice_threshold: underpriceThreshold / 100.0,
        overprice_threshold: overpriceThreshold / 100.0,
        min_margin: minMargin / 100.0,
        custom_instruction: customInstruction
      })
      alert('Đã lưu cấu hình tham số AI Agent & Chỉ số Cảnh báo thành công persistent!')
    } catch (err) {
      alert('Không thể lưu cấu hình.')
    } finally {
      setLoading(false)
    }
  }

  const handleFileChange = (e) => {
    setCsvFile(e.target.files[0])
  }

  const handleUploadCsv = async (e) => {
    e.preventDefault()
    if (!csvFile) {
      alert('Vui lòng chọn tệp tin .csv trước!')
      return
    }

    const formData = new FormData()
    formData.append('file', csvFile)

    try {
      setUploading(true)
      const res = await axios.post(`${API_BASE_URL}/products/import-csv`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })
      alert(res.data.message)
      setCsvFile(null)
      document.getElementById('csv-file-input').value = ''
    } catch (err) {
      alert(err.response?.data?.detail || 'Lỗi khi tải lên file CSV.')
    } finally {
      setUploading(false)
    }
  }

  const handleResetDatabase = async () => {
    const confirmReset = window.confirm('Reload the hackathon demo dataset? This replaces current products, competitor prices, alerts, and agent actions.')
    if (!confirmReset) return

    try {
      setSeeding(true)
      const res = await axios.post(`${API_BASE_URL}/products/seed-demo`)
      alert(res.data.message)
    } catch (err) {
      alert(err.response?.data?.detail || 'Unable to seed demo dataset.')
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

            <div className="form-group" style={{ marginTop: '16px' }}>
              <label>Chỉ thị Tùy chỉnh cho AI Agent (LLM Custom Instruction)</label>
              <textarea
                className="form-control"
                style={{ height: '80px', padding: '10px', resize: 'vertical', background: 'var(--bg-input)', border: '1px solid var(--border-color)', color: 'white', borderRadius: '6px', width: '100%', outline: 'none' }}
                placeholder="Ví dụ: Ưu tiên bảo vệ biên lợi nhuận cao ở các dòng Skincare và giảm giá cạnh tranh mạnh ở Shopee."
                value={customInstruction}
                onChange={(e) => setCustomInstruction(e.target.value)}
              />
              <span style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginTop: '6px' }}>
                Chỉ thị này sẽ được gửi trực tiếp đến OpenAI GPT-4o để tùy biến luồng tư duy đưa ra quyết định của AI Agent.
              </span>
            </div>

            <button type="submit" className="btn btn-primary" style={{ marginTop: '12px' }}>
              <Save size={16} />
              {loading ? 'Đang lưu...' : 'Lưu cấu hình quy tắc'}
            </button>
          </form>
        </div>

        {/* Database Management & Dynamic Importer */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* CSV Importer Card */}
          <div className="section-card glass" style={{ padding: '28px' }}>
            <div className="section-header" style={{ marginBottom: '16px' }}>
              <div className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--primary)' }}>
                <RefreshCw size={18} />
                Nạp Danh Sách SKU Động (Dynamic CSV Importer)
              </div>
            </div>
            
            <p style={{ fontSize: '13px', lineHeight: 1.5, color: 'var(--text-muted)', marginBottom: '16px' }}>
              Nạp danh sách sản phẩm thật của Ban tổ chức vào hệ thống. Tệp tin cần chứa các cột: 
              <code style={{ fontFamily: 'var(--font-mono)', background: 'var(--bg-input)', padding: '2px 4px', borderRadius: '4px', marginLeft: '4px' }}>
                barcode, name, category, guardian_price, cost_price
              </code>
            </p>

            <form onSubmit={handleUploadCsv} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <input
                id="csv-file-input"
                type="file"
                accept=".csv"
                onChange={handleFileChange}
                className="form-control"
                style={{ padding: '8px 12px' }}
              />
              <button 
                type="submit" 
                className="btn btn-accent" 
                style={{ alignSelf: 'flex-start' }}
                disabled={uploading}
              >
                {uploading ? 'Đang tải lên...' : 'Tải lên & Khởi tạo CSDL'}
              </button>
            </form>
          </div>

          {/* Reset System Card */}
          <div className="section-card glass" style={{ padding: '28px' }}>
            <div className="section-header" style={{ marginBottom: '16px' }}>
              <div className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--danger)' }}>
                <AlertCircle size={18} />
                Tái lập Hệ thống
              </div>
            </div>

            <p style={{ fontSize: '13px', lineHeight: 1.5, color: 'var(--text-muted)', marginBottom: '16px' }}>
              Xóa sạch cơ sở dữ liệu hiện tại và tải lại 200 SKU giả lập mẫu ban đầu phục vụ cho demo thuyết trình.
            </p>

            <button 
              className="btn btn-secondary" 
              style={{ borderColor: 'var(--danger)', color: 'var(--danger)' }}
              onClick={handleResetDatabase}
              disabled={seeding}
            >
              <RefreshCw size={16} className={seeding ? 'spin' : ''} />
              {seeding ? 'Đang Reset CSDL...' : 'Reset & Re-seed CSDL mẫu'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Configuration
