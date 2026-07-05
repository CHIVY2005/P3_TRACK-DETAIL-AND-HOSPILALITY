import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { API_BASE_URL } from '../App.jsx'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { Search, ExternalLink, ShieldCheck, AlertTriangle } from 'lucide-react'

function ProductInsights() {
  const [products, setProducts] = useState([])
  const [selectedProductId, setSelectedProductId] = useState('')
  const [productDetail, setProductDetail] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(true)

  // 1. Fetch all products on load
  useEffect(() => {
    const fetchProducts = async () => {
      try {
        setLoading(true)
        const res = await axios.get(`${API_BASE_URL}/pricing/cpi-index`)
        setProducts(res.data)
        if (res.data.length > 0) {
          setSelectedProductId(res.data[0].id)
        }
      } catch (err) {
        console.error('Error fetching product list', err)
      } finally {
        setLoading(false)
      }
    }
    fetchProducts()
  }, [])

  // 2. Fetch selected product detail
  useEffect(() => {
    if (!selectedProductId) return

    const fetchProductDetail = async () => {
      try {
        const res = await axios.get(`${API_BASE_URL}/products/${selectedProductId}`)
        setProductDetail(res.data)
      } catch (err) {
        console.error('Error fetching product detail', err)
      }
    }
    fetchProductDetail()
  }, [selectedProductId])

  const filteredProducts = products.filter(p => 
    p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.barcode.includes(searchQuery)
  )

  const handleSelectProduct = (id) => {
    setSelectedProductId(id)
  }

  // Process data for the Recharts line graph
  const getChartData = () => {
    if (!productDetail || !productDetail.competitor_prices) return []

    // Group competitor prices by date
    const dateGroups = {}
    
    // Add guardian price as reference
    // We group competitor prices by day (YYYY-MM-DD)
    productDetail.competitor_prices.forEach(cp => {
      const dateStr = new Date(cp.scraped_at).toLocaleDateString('vi-VN', { month: '2-digit', day: '2-digit' })
      if (!dateGroups[dateStr]) {
        dateGroups[dateStr] = { 
          date: dateStr,
          'Guardian': productDetail.guardian_price
        }
      }
      dateGroups[dateStr][cp.competitor_name] = cp.net_price
    })

    // Sort by date key
    return Object.values(dateGroups).sort((a, b) => a.date.localeCompare(b.date))
  }

  const chartData = getChartData()
  const currentCPI = products.find(p => p.id === Number(selectedProductId))?.competitor_index || 100

  return (
    <div>
      {/* Header */}
      <div className="header">
        <div className="header-title">
          <h1>Phân tích Chi tiết SKU</h1>
          <p>Phân tích chênh lệch giá Net Price và theo dõi lịch sử biến động giá của từng sản phẩm.</p>
        </div>
      </div>

      <div className="agent-console-container" style={{ gridTemplateColumns: '1fr 3fr' }}>
        {/* Left Side: Product Picker */}
        <div className="section-card glass" style={{ height: 'calc(100vh - 180px)', display: 'flex', flexDirection: 'column', padding: '16px' }}>
          <div style={{ position: 'relative', marginBottom: '16px' }}>
            <input
              type="text"
              placeholder="Tìm tên hoặc barcode..."
              className="form-control"
              style={{ paddingLeft: '40px' }}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <Search size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          </div>

          <div style={{ flexGrow: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {filteredProducts.map(p => (
              <div
                key={p.id}
                className={`action-card-item ${selectedProductId === p.id ? 'active' : ''}`}
                style={{ 
                  cursor: 'pointer', 
                  margin: 0, 
                  background: selectedProductId === p.id ? 'rgba(240, 137, 19, 0.08)' : 'rgba(255, 255, 255, 0.01)',
                  borderColor: selectedProductId === p.id ? 'var(--primary)' : 'var(--border-color)'
                }}
                onClick={() => handleSelectProduct(p.id)}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ fontWeight: '600', fontSize: '13px', color: selectedProductId === p.id ? 'white' : 'var(--text-main)' }}>
                    {p.name}
                  </div>
                  <span className={`badge ${p.competitor_index > 110 ? 'badge-danger' : p.competitor_index < 90 ? 'badge-success' : 'badge-info'}`} style={{ fontSize: '10px', padding: '2px 4px' }}>
                    CPI {p.competitor_index}%
                  </span>
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px', fontFamily: 'var(--font-mono)' }}>
                  {p.barcode}
                </div>
              </div>
            ))}
            {filteredProducts.length === 0 && (
              <div style={{ color: 'var(--text-muted)', textAlign: 'center', marginTop: '20px' }}>Không tìm thấy SKU.</div>
            )}
          </div>
        </div>

        {/* Right Side: Product Details & Pricing Charts */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', height: 'calc(100vh - 180px)', overflowY: 'auto', paddingRight: '4px' }}>
          {productDetail ? (
            <>
              {/* Product Info Cards */}
              <div className="section-card glass" style={{ display: 'grid', gridTemplateColumns: '120px 1fr 1fr', gap: '24px', alignItems: 'center' }}>
                <img src={productDetail.image_url} alt={productDetail.name} style={{ width: '120px', height: '120px', borderRadius: '12px', objectFit: 'cover', border: '1px solid var(--border-color)' }} />
                
                <div>
                  <h2 style={{ fontSize: '20px', fontWeight: '700', fontFamily: 'Outfit, sans-serif' }}>{productDetail.name}</h2>
                  <div style={{ display: 'flex', gap: '16px', marginTop: '8px', fontSize: '13px', color: 'var(--text-muted)' }}>
                    <span>Barcode: <strong style={{ fontFamily: 'var(--font-mono)' }}>{productDetail.barcode}</strong></span>
                    <span>•</span>
                    <span>Phân mục: <strong>{productDetail.category}</strong></span>
                  </div>
                  <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '12px', lineHeight: 1.4 }}>{productDetail.description}</p>
                </div>

                <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', borderRadius: '12px', padding: '16px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Giá Guardian</span>
                    <div style={{ fontSize: '16px', fontWeight: '700', color: 'var(--primary)' }}>{productDetail.guardian_price.toLocaleString()}đ</div>
                  </div>
                  <div>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Giá Vốn (Cost)</span>
                    <div style={{ fontSize: '16px', fontWeight: '600' }}>{(productDetail.cost_price || 0).toLocaleString()}đ</div>
                  </div>
                  <div>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Biên Lợi Nhuận</span>
                    <div style={{ fontSize: '16px', fontWeight: '600', color: '#10b981' }}>
                      {productDetail.cost_price 
                        ? `${Math.round(((productDetail.guardian_price - productDetail.cost_price)/productDetail.guardian_price)*100)}%`
                        : 'N/A'}
                    </div>
                  </div>
                  <div>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Chỉ Số Giá CPI</span>
                    <div style={{ fontSize: '16px', fontWeight: '700', color: currentCPI > 110 ? 'var(--danger)' : currentCPI < 90 ? 'var(--success)' : 'var(--info)' }}>
                      {currentCPI}%
                    </div>
                  </div>
                </div>
              </div>

              {/* Price comparison list */}
              <div className="section-card glass">
                <div className="section-title" style={{ marginBottom: '16px' }}>Bảng Giá So Sánh Net Price Thực Tế</div>
                <div className="data-table-container">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Đối Thủ</th>
                        <th>Giá Gốc (Raw)</th>
                        <th>Khuyến Mãi (Discount)</th>
                        <th>Mã Vouchers</th>
                        <th>Cơ Chế Phụ (Combo/Flash)</th>
                        <th>Giá Thực Tế (Net Price)</th>
                        <th>Chênh lệch</th>
                        <th>Link</th>
                      </tr>
                    </thead>
                    <tbody>
                      {/* Guardian price line for comparison */}
                      <tr style={{ background: 'rgba(240, 137, 19, 0.05)' }}>
                        <td><strong>Guardian (Hiện tại)</strong></td>
                        <td>{productDetail.guardian_price.toLocaleString()}đ</td>
                        <td>-</td>
                        <td>-</td>
                        <td>-</td>
                        <td><strong style={{ color: 'var(--primary)' }}>{productDetail.guardian_price.toLocaleString()}đ</strong></td>
                        <td>-</td>
                        <td>-</td>
                      </tr>

                      {/* Competitor prices */}
                      {productDetail.competitor_prices && 
                       productDetail.competitor_prices.slice(0, 5).map(cp => {
                         const diff = cp.net_price - productDetail.guardian_price
                         const diffPct = (diff / productDetail.guardian_price) * 100
                         return (
                           <tr key={cp.id}>
                             <td>
                               <span className={`competitor-dot ${cp.competitor_name.toLowerCase().replace(' ', '')}`} style={{ display: 'inline-flex', marginRight: '8px', cursor: 'default' }}>
                                 {cp.competitor_name[0]}
                               </span>
                               <strong>{cp.competitor_name}</strong>
                             </td>
                             <td>{cp.raw_price.toLocaleString()}đ</td>
                             <td>{cp.discount > 0 ? `${cp.discount.toLocaleString()}đ` : '-'}</td>
                             <td><span style={{ color: 'var(--primary)' }}>{cp.voucher_details || '-'}</span></td>
                             <td>{cp.promo_mechanics || '-'}</td>
                             <td><strong>{cp.net_price.toLocaleString()}đ</strong></td>
                             <td style={{ color: diff > 0 ? '#10b981' : diff < 0 ? '#ef4444' : 'var(--text-muted)', fontWeight: '600' }}>
                               {diff > 0 ? `+${diff.toLocaleString()}đ (+${Math.round(diffPct)}%)` : 
                                diff < 0 ? `${diff.toLocaleString()}đ (${Math.round(diffPct)}%)` : 
                                'Bằng giá'}
                             </td>
                             <td>
                               <a href={cp.url} target="_blank" rel="noreferrer" className="alert-resolve-btn" style={{ display: 'inline-block' }}>
                                 <ExternalLink size={14} />
                               </a>
                             </td>
                           </tr>
                         )
                       })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Price history chart */}
              <div className="section-card glass">
                <div className="section-title" style={{ marginBottom: '16px' }}>Biểu Đồ Lịch Sử Biến Động Giá Net Price (7 ngày qua)</div>
                <div style={{ width: '100%', height: 300 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                      <XAxis dataKey="date" stroke="var(--text-muted)" fontSize={12} />
                      <YAxis stroke="var(--text-muted)" fontSize={11} tickFormatter={(val) => `${val/1000}k`} />
                      <Tooltip 
                        contentStyle={{ backgroundColor: 'var(--bg-input)', borderColor: 'var(--border-color)', color: 'white' }}
                        formatter={(val) => [`${val.toLocaleString()} VND`]}
                      />
                      <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: '13px' }} />
                      <Line type="monotone" dataKey="Guardian" stroke="var(--primary)" strokeWidth={3} activeDot={{ r: 8 }} />
                      <Line type="monotone" dataKey="Shopee" stroke="#f04b29" strokeWidth={1.5} dot={{ r: 3 }} />
                      <Line type="monotone" dataKey="Lazada" stroke="#3b82f6" strokeWidth={1.5} dot={{ r: 3 }} />
                      <Line type="monotone" dataKey="TikTok Shop" stroke="#00f2fe" strokeWidth={1.5} dot={{ r: 3 }} />
                      <Line type="monotone" dataKey="GrabMart" stroke="#00b14f" strokeWidth={1.5} dot={{ r: 3 }} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </>
          ) : (
            <div className="section-card glass" style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-muted)' }}>
              Vui lòng chọn một sản phẩm ở cột danh sách bên trái để xem phân tích.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default ProductInsights
