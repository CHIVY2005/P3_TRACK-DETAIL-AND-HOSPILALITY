import React, { useEffect, useState } from 'react'
import axios from 'axios'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { ExternalLink, Search } from 'lucide-react'
import { API_BASE_URL } from '../App.jsx'

function ProductInsights() {
  const [products, setProducts] = useState([])
  const [selectedProductId, setSelectedProductId] = useState('')
  const [productDetail, setProductDetail] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(true)

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

  const filteredProducts = products.filter(
    (product) =>
      product.name.toLowerCase().includes(searchQuery.toLowerCase()) || product.barcode.includes(searchQuery)
  )

  const chartData = getChartData(productDetail)
  const currentCPI = products.find((product) => product.id === Number(selectedProductId))?.competitor_index || 100

  return (
    <div className="page-stack">
      <section className="header">
        <div className="header-title">
          <h1>SKU Insights</h1>
          <p>
            Drill down into a single barcode, compare effective competitor net price, and see whether the latest
            scraped signal is safe, suspicious, or out of stock.
          </p>
        </div>
      </section>

      <div className="agent-console-container" style={{ gridTemplateColumns: '1fr 2.4fr', height: 'auto' }}>
        <section className="section-card glass sku-picker">
          <div style={{ position: 'relative', marginBottom: '16px' }}>
            <input
              type="text"
              placeholder="Search name or barcode..."
              className="form-control"
              style={{ paddingLeft: '40px' }}
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
            />
            <Search size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          </div>

          <div className="scroll-stack">
            {loading ? (
              <div className="empty-note">Loading SKU list...</div>
            ) : filteredProducts.length > 0 ? (
              filteredProducts.map((product) => (
                <button
                  key={product.id}
                  type="button"
                  className={`sku-list-item ${selectedProductId === product.id ? 'active' : ''}`}
                  onClick={() => setSelectedProductId(product.id)}
                >
                  <div className="sku-list-head">
                    <strong>{product.name}</strong>
                    <span className={`badge ${product.competitor_index > 110 ? 'badge-danger' : product.competitor_index < 90 ? 'badge-success' : 'badge-info'}`}>
                      CPI {product.competitor_index}%
                    </span>
                  </div>
                  <span>{product.barcode}</span>
                </button>
              ))
            ) : (
              <div className="empty-note">No SKU matched the search.</div>
            )}
          </div>
        </section>

        <div className="page-stack">
          {productDetail ? (
            <>
              <section className="section-card glass product-summary-card">
                <img src={productDetail.image_url} alt={productDetail.name} className="detail-img" />

                <div>
                  <h2>{productDetail.name}</h2>
                  <div className="product-meta-row">
                    <span>Barcode {productDetail.barcode}</span>
                    <span>{productDetail.category}</span>
                  </div>
                  <p className="card-copy">{productDetail.description}</p>
                </div>

                <div className="product-kv-grid">
                  <Metric label="Guardian price" value={`${productDetail.guardian_price.toLocaleString()}đ`} tone="accent" />
                  <Metric label="Cost price" value={`${(productDetail.cost_price || 0).toLocaleString()}đ`} />
                  <Metric
                    label="Margin"
                    value={
                      productDetail.cost_price
                        ? `${Math.round(((productDetail.guardian_price - productDetail.cost_price) / productDetail.guardian_price) * 100)}%`
                        : 'N/A'
                    }
                    tone="good"
                  />
                  <Metric
                    label="CPI"
                    value={`${currentCPI}%`}
                    tone={currentCPI > 110 ? 'bad' : currentCPI < 90 ? 'good' : 'neutral'}
                  />
                </div>
              </section>

              <section className="section-card glass">
                <div className="section-header">
                  <div className="section-title">Competitor net-price table</div>
                </div>
                <div className="data-table-container">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Channel</th>
                        <th>Raw</th>
                        <th>Discount</th>
                        <th>Voucher</th>
                        <th>Promo</th>
                        <th>Net price</th>
                        <th>Gap vs Guardian</th>
                        <th>Source</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="guardian-row">
                        <td><strong>Guardian</strong></td>
                        <td>{productDetail.guardian_price.toLocaleString()}đ</td>
                        <td>-</td>
                        <td>-</td>
                        <td>-</td>
                        <td><strong>{productDetail.guardian_price.toLocaleString()}đ</strong></td>
                        <td>-</td>
                        <td>-</td>
                      </tr>

                      {productDetail.competitor_prices?.slice(0, 8).map((priceRow) => {
                        const isOos = priceRow.stock_status === 'OUT_OF_STOCK' || priceRow.net_price === null
                        const isSuspicious = priceRow.is_suspicious
                        const diff = isOos || isSuspicious ? null : priceRow.net_price - productDetail.guardian_price
                        const diffPct = isOos || isSuspicious ? null : (diff / productDetail.guardian_price) * 100

                        return (
                          <tr key={priceRow.id}>
                            <td><strong>{priceRow.competitor_name}</strong></td>
                            <td>{priceRow.raw_price ? `${priceRow.raw_price.toLocaleString()}đ` : '-'}</td>
                            <td>{priceRow.discount ? `${priceRow.discount.toLocaleString()}đ` : '-'}</td>
                            <td>{priceRow.voucher_details || '-'}</td>
                            <td>{priceRow.promo_mechanics || '-'}</td>
                            <td>
                              {isOos ? (
                                <span className="badge badge-danger">Out of stock</span>
                              ) : isSuspicious ? (
                                <span className="badge badge-warning">Suspicious</span>
                              ) : (
                                <strong>{priceRow.net_price.toLocaleString()}đ</strong>
                              )}
                            </td>
                            <td className={diff === null ? '' : diff < 0 ? 'price-bad' : 'price-good'}>
                              {isOos
                                ? 'Inventory advantage'
                                : isSuspicious
                                  ? 'Noise filtered'
                                  : diff === 0
                                    ? 'On parity'
                                    : `${diff > 0 ? '+' : ''}${diff.toLocaleString()}đ (${Math.round(diffPct)}%)`}
                            </td>
                            <td>
                              {priceRow.url ? (
                                <a href={priceRow.url} target="_blank" rel="noreferrer" className="inline-link-button">
                                  <ExternalLink size={13} />
                                  Open
                                </a>
                              ) : (
                                '-'
                              )}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </section>

              <section className="section-card glass">
                <div className="section-header">
                  <div className="section-title">7-day price history</div>
                </div>
                <div style={{ width: '100%', height: 300 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData} margin={{ top: 5, right: 18, left: 8, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(47, 79, 79, 0.12)" />
                      <XAxis dataKey="date" stroke="var(--text-muted)" fontSize={12} />
                      <YAxis stroke="var(--text-muted)" fontSize={11} tickFormatter={(val) => `${Math.round(val / 1000)}k`} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'rgba(255,255,255,0.98)',
                          borderColor: 'rgba(15, 23, 42, 0.08)',
                          color: 'var(--text-main)',
                          borderRadius: '12px',
                        }}
                        formatter={(value) => [`${value.toLocaleString()} VND`]}
                      />
                      <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: '13px' }} />
                      <Line type="monotone" dataKey="Guardian" stroke="var(--accent-strong)" strokeWidth={3} activeDot={{ r: 7 }} />
                      <Line type="monotone" dataKey="Shopee" stroke="#ee6c4d" strokeWidth={1.5} dot={{ r: 3 }} />
                      <Line type="monotone" dataKey="Lazada" stroke="#2563eb" strokeWidth={1.5} dot={{ r: 3 }} />
                      <Line type="monotone" dataKey="TikTok Shop" stroke="#111827" strokeWidth={1.5} dot={{ r: 3 }} />
                      <Line type="monotone" dataKey="GrabMart" stroke="#0f9f72" strokeWidth={1.5} dot={{ r: 3 }} />
                      <Line type="monotone" dataKey="Hasaki" stroke="#d97706" strokeWidth={1.5} dot={{ r: 3 }} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </section>
            </>
          ) : (
            <section className="section-card glass">
              <div className="empty-note">Choose a SKU from the left column to inspect pricing detail.</div>
            </section>
          )}
        </div>
      </div>
    </div>
  )
}

function Metric({ label, value, tone = 'neutral' }) {
  return (
    <div className={`product-kv product-kv-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function getChartData(productDetail) {
  if (!productDetail?.competitor_prices) return []

  const dateGroups = {}
  productDetail.competitor_prices.forEach((row) => {
    const dateStr = new Date(row.scraped_at).toLocaleDateString('en-GB', { month: '2-digit', day: '2-digit' })
    if (!dateGroups[dateStr]) {
      dateGroups[dateStr] = {
        date: dateStr,
        Guardian: productDetail.guardian_price,
      }
    }
    dateGroups[dateStr][row.competitor_name] = row.net_price
  })

  return Object.values(dateGroups).sort((a, b) => a.date.localeCompare(b.date))
}

export default ProductInsights
