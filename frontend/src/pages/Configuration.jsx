import React, { useEffect, useState } from 'react'
import axios from 'axios'
import { Database, RefreshCw, Save, SlidersHorizontal, UploadCloud } from 'lucide-react'
import { API_BASE_URL } from '../api.js'

function Configuration() {
  const [underpriceThreshold, setUnderpriceThreshold] = useState(10)
  const [overpriceThreshold, setOverpriceThreshold] = useState(10)
  const [minMargin, setMinMargin] = useState(15)
  const [customInstruction, setCustomInstruction] = useState('')
  const [loading, setLoading] = useState(false)
  const [seeding, setSeeding] = useState(false)
  const [datasetFile, setDatasetFile] = useState(null)
  const [uploading, setUploading] = useState(false)

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

  const handleSaveConfig = async (event) => {
    event.preventDefault()
    try {
      setLoading(true)
      await axios.post(`${API_BASE_URL}/agent/config`, {
        underprice_threshold: underpriceThreshold / 100.0,
        overprice_threshold: overpriceThreshold / 100.0,
        min_margin: minMargin / 100.0,
        custom_instruction: customInstruction,
      })
      alert('Agent configuration saved successfully.')
    } catch (err) {
      alert('Unable to save the configuration.')
    } finally {
      setLoading(false)
    }
  }

  const handleUploadDataset = async (event) => {
    event.preventDefault()
    if (!datasetFile) {
      alert('Select a CSV or JSON file first.')
      return
    }

    const formData = new FormData()
    formData.append('file', datasetFile)

    try {
      setUploading(true)
      const res = await axios.post(`${API_BASE_URL}/products/import-dataset`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      alert(res.data.message)
      setDatasetFile(null)
      const input = document.getElementById('dataset-file-input')
      if (input) input.value = ''
    } catch (err) {
      alert(err.response?.data?.detail || 'Dataset upload failed.')
    } finally {
      setUploading(false)
    }
  }

  const handleResetDatabase = async () => {
    const confirmReset = window.confirm(
      'Reload the demo dataset? This replaces products, competitor prices, alerts, tasks, actions, and imported competitor links.'
    )
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
    <div className="page-stack">
      <section className="header">
        <div className="header-title">
          <h1>Operations Configuration</h1>
          <p>
            This screen now supports dynamic CSV and JSON ingestion, preserves the demo reset path, and lets us tune
            the thresholds that drive the Margin Guardian decision flow.
          </p>
        </div>
      </section>

      <div className="config-grid">
        <section className="section-card glass">
          <div className="section-header">
            <div className="section-title section-title-inline">
              <SlidersHorizontal size={18} />
              <span>Decision thresholds</span>
            </div>
          </div>

          <form onSubmit={handleSaveConfig}>
            <div className="form-group">
              <label>Overpriced threshold</label>
              <div className="input-inline">
                <input
                  type="number"
                  className="form-control"
                  value={overpriceThreshold}
                  onChange={(event) => setOverpriceThreshold(Number(event.target.value))}
                  min="1"
                  max="50"
                />
                <span>%</span>
              </div>
              <small>Raise a pricing alert when Guardian is higher than market by this margin.</small>
            </div>

            <div className="form-group">
              <label>Underpriced threshold</label>
              <div className="input-inline">
                <input
                  type="number"
                  className="form-control"
                  value={underpriceThreshold}
                  onChange={(event) => setUnderpriceThreshold(Number(event.target.value))}
                  min="1"
                  max="50"
                />
                <span>%</span>
              </div>
              <small>Flag margin leakage when Guardian is meaningfully below competitor pricing.</small>
            </div>

            <div className="form-group">
              <label>Minimum safe margin</label>
              <div className="input-inline">
                <input
                  type="number"
                  className="form-control"
                  value={minMargin}
                  onChange={(event) => setMinMargin(Number(event.target.value))}
                  min="5"
                  max="50"
                />
                <span>%</span>
              </div>
              <small>If matching would push margin below this point, the agent drafts supplier outreach instead.</small>
            </div>

            <div className="form-group">
              <label>Custom instruction for the agent</label>
              <textarea
                className="form-control form-textarea"
                placeholder="Example: protect skincare margin first, but stay aggressive on Shopee."
                value={customInstruction}
                onChange={(event) => setCustomInstruction(event.target.value)}
              />
            </div>

            <button type="submit" className="btn btn-accent">
              <Save size={16} />
              {loading ? 'Saving...' : 'Save rules'}
            </button>
          </form>
        </section>

        <div className="config-stack">
          <section className="section-card glass">
            <div className="section-header">
              <div className="section-title section-title-inline">
                <UploadCloud size={18} />
                <span>Dynamic dataset import</span>
              </div>
            </div>

            <p className="card-copy">
              Upload `csv` or `json`. The importer auto-maps common product fields and also registers optional
              competitor URLs such as `shopee_url`, `hasaki_url`, or `lazada_url` when they are present.
            </p>

            <form onSubmit={handleUploadDataset} className="upload-form">
              <input
                id="dataset-file-input"
                type="file"
                accept=".csv,.json"
                onChange={(event) => setDatasetFile(event.target.files?.[0] || null)}
                className="form-control"
              />
              <button type="submit" className="btn btn-secondary" disabled={uploading}>
                <UploadCloud size={16} />
                {uploading ? 'Importing...' : 'Import dataset'}
              </button>
            </form>
          </section>

          <section className="section-card glass">
            <div className="section-header">
              <div className="section-title section-title-inline">
                <Database size={18} />
                <span>Demo recovery</span>
              </div>
            </div>

            <p className="card-copy">
              Reset back to the demo catalog, competitor history, and alert workflow. This is useful right before a
              presentation or after a heavy import experiment.
            </p>

            <button className="btn btn-secondary" onClick={handleResetDatabase} disabled={seeding}>
              <RefreshCw size={16} className={seeding ? 'spin' : ''} />
              {seeding ? 'Reloading demo...' : 'Reload demo dataset'}
            </button>
          </section>
        </div>
      </div>
    </div>
  )
}

export default Configuration
