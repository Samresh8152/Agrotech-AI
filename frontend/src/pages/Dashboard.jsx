import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  LuMapPin, LuPencil, LuPlus, LuSun, LuCloud, LuCloudRain, LuCloudLightning, LuDroplets, LuWind,
  LuMicroscope, LuMessagesSquare, LuSprout, LuTrash2, LuCheck, LuRotateCcw, LuShovel, LuChartColumn,
  LuFlaskConical, LuCloudSun, LuHistory, LuX,
} from 'react-icons/lu'
import toast from 'react-hot-toast'
import api from '../services/api'
import { useAuth } from '../contexts/AuthContext'

const COMMON_PLANTS = [
  'Tomato', 'Potato', 'Onion', 'Rice', 'Wheat', 'Maize', 'Cotton', 'Sugarcane', 'Soybean', 'Groundnut', 'Chilli',
  'Brinjal', 'Okra', 'Cabbage', 'Cauliflower', 'Cucumber', 'Bottle gourd', 'Bitter gourd', 'Pumpkin', 'Mustard',
  'Chickpea', 'Pigeon pea (Tur)', 'Moong', 'Bajra', 'Jowar', 'Ragi', 'Turmeric', 'Ginger', 'Garlic', 'Coriander',
  'Banana', 'Mango', 'Grape', 'Pomegranate', 'Papaya', 'Guava', 'Orange', 'Coconut', 'Tea', 'Coffee', 'Marigold', 'Rose',
]

const KIND = {
  sowing: { label: 'Sowing', cls: 'badge-success' },
  harvest: { label: 'Harvest', cls: 'badge-orange' },
  disease_scan: { label: 'Disease scan', cls: 'badge-danger' },
  soil_test: { label: 'Soil test', cls: 'badge-orange' },
  crop_recommendation: { label: 'Crop advice', cls: 'badge-info' },
  yield_prediction: { label: 'Yield estimate', cls: 'badge-info' },
  fertilizer: { label: 'Fertilizer plan', cls: 'badge-warning' },
  farm: { label: 'Farm', cls: 'badge-neutral' },
}

const TOOLS = [
  { to: '/disease-prediction', icon: LuMicroscope, label: 'Check a plant' },
  { to: '/soil-prediction', icon: LuShovel, label: 'Soil health' },
  { to: '/crop-recommendation', icon: LuSprout, label: 'What to sow' },
  { to: '/fertilizer', icon: LuFlaskConical, label: 'Fertilizer plan' },
  { to: '/yield-prediction', icon: LuChartColumn, label: 'Yield estimate' },
  { to: '/weather', icon: LuCloudSun, label: 'Full weather' },
]

const toDate = (ts) => new Date(/[zZ]|[+-]\d\d:\d\d$/.test(ts) ? ts : ts + 'Z')
const todayISO = () => new Date().toISOString().slice(0, 10)
const fmtDay = (iso) => new Date(iso + 'T00:00:00').toLocaleDateString(undefined, { weekday: 'short' })
const fmtDate = (iso) => new Date(iso + 'T00:00:00').toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
const plural = (n, unit) => `${n} ${unit}${n === 1 ? '' : 's'}`

function greeting() {
  const h = new Date().getHours()
  return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening'
}

function SkyIcon({ desc = '', size = 22 }) {
  const d = desc.toLowerCase()
  const I = d.includes('thunder') ? LuCloudLightning : d.includes('rain') || d.includes('drizzle') ? LuCloudRain : d.includes('cloud') ? LuCloud : LuSun
  return <I size={size} strokeWidth={1.6} />
}

/* ── City ─────────────────────────────────────────────── */
function CityForm({ initial = '', onSaved, onCancel }) {
  const [city, setCity] = useState(initial)
  const [saving, setSaving] = useState(false)
  const save = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const { data } = await api.put('/farm/city', { city })
      if (data.success) onSaved(data)
      else toast.error(data.message)
    } catch (err) { toast.error(err.response?.data?.message || 'Could not save the location') }
    finally { setSaving(false) }
  }
  return (
    <form onSubmit={save} style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
      <input className="form-input" style={{ flex: '1 1 220px' }} autoFocus placeholder="Village, town or district — e.g. Nashik"
        value={city} onChange={e => setCity(e.target.value)} maxLength={100} />
      <button className="btn btn-primary" disabled={saving || !city.trim()}>{saving ? 'Checking…' : 'Save'}</button>
      {onCancel && <button type="button" className="btn btn-secondary" onClick={onCancel}>Cancel</button>}
    </form>
  )
}

/* ── Crops ────────────────────────────────────────────── */
function CropForm({ onSaved, onCancel }) {
  const [f, setF] = useState({ crop: '', variety: '', area: '', area_unit: 'acre', field_name: '', sown_on: todayISO() })
  const [saving, setSaving] = useState(false)
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const save = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const { data } = await api.post('/farm/crops', f)
      if (data.success) { toast.success(`${data.crop.crop} added to your farm`); onSaved() }
      else toast.error(data.message)
    } catch (err) { toast.error(err.response?.data?.message || 'Could not add the crop') }
    finally { setSaving(false) }
  }
  return (
    <form onSubmit={save} className="card" style={{ padding: 18, marginBottom: 14, background: 'var(--surface-2)' }}>
      <div className="input-row">
        <div className="form-group">
          <label className="form-label" htmlFor="crop">Crop or plant</label>
          <input id="crop" className="form-input" list="crop-options" placeholder="Any plant — e.g. Tomato, Tur, Marigold" value={f.crop} onChange={set('crop')} required maxLength={80} autoFocus />
          <datalist id="crop-options">{COMMON_PLANTS.map(p => <option key={p} value={p} />)}</datalist>
        </div>
        <div className="form-group">
          <label className="form-label" htmlFor="variety">Variety <span className="muted">(optional)</span></label>
          <input id="variety" className="form-input" placeholder="e.g. Arka Rakshak" value={f.variety} onChange={set('variety')} maxLength={80} />
        </div>
      </div>
      <div className="input-row-3">
        <div className="form-group">
          <label className="form-label" htmlFor="sown">Sown on</label>
          <input id="sown" className="form-input" type="date" max={todayISO()} value={f.sown_on} onChange={set('sown_on')} />
        </div>
        <div className="form-group">
          <label className="form-label" htmlFor="area">Area <span className="muted">(optional)</span></label>
          <div style={{ display: 'flex', gap: 6 }}>
            <input id="area" className="form-input" type="number" min="0" step="0.1" value={f.area} onChange={set('area')} style={{ minWidth: 0 }} />
            <select className="form-select" value={f.area_unit} onChange={set('area_unit')} style={{ width: 110 }} aria-label="Area unit">
              <option value="acre">acres</option><option value="hectare">hectares</option>
              <option value="guntha">guntha</option><option value="bigha">bigha</option>
            </select>
          </div>
        </div>
        <div className="form-group">
          <label className="form-label" htmlFor="field">Field / plot <span className="muted">(optional)</span></label>
          <input id="field" className="form-input" placeholder="e.g. Near the well" value={f.field_name} onChange={set('field_name')} maxLength={80} />
        </div>
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        <button className="btn btn-primary" disabled={saving || !f.crop.trim()}>{saving ? 'Saving…' : 'Add crop'}</button>
        <button type="button" className="btn btn-secondary" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  )
}

function CropRow({ c, onChange }) {
  const navigate = useNavigate()
  const update = async (body, msg) => {
    try {
      const { data } = await api.patch(`/farm/crops/${c.id}`, body)
      if (data.success) { toast.success(msg); onChange() } else toast.error(data.message)
    } catch (err) { toast.error(err.response?.data?.message || 'Could not update') }
  }
  const remove = async () => {
    if (!window.confirm(`Remove ${c.crop} from your farm? Its history stays.`)) return
    await api.delete(`/farm/crops/${c.id}`)
    onChange()
  }
  const meta = [
    c.variety,
    c.area ? plural(c.area, c.area_unit) : null,
    c.field_name,
    c.sown_on ? `sown ${fmtDate(c.sown_on)}` : 'sowing date not set',
  ].filter(Boolean).join(' · ')
  const growing = c.status === 'growing'
  return (
    <div className="crop-row">
      <div className="crop-day">
        {c.days_since_sowing != null ? <><strong>{c.days_since_sowing}</strong><span>{c.days_since_sowing === 1 ? 'day' : 'days'}</span></> : <span>—</span>}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="crop-name">
          {c.crop}
          {!growing && <span className="badge badge-neutral">Harvested{c.harvested_on ? ` ${fmtDate(c.harvested_on)}` : ''}</span>}
          {c.source === 'assistant' && <span className="badge badge-info" title="Added from your chat with Krishi Mitra">from chat</span>}
        </div>
        <div className="crop-meta">{meta}</div>
        {c.last_scan && (
          <div className="crop-meta" style={{ marginTop: 4 }}>
            Last scan: <span style={{ color: /healthy/i.test(c.last_scan.disease) ? 'var(--brand)' : 'var(--danger)', fontWeight: 500 }}>{c.last_scan.disease}</span>
            {' '}({toDate(c.last_scan.created_at).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })})
          </div>
        )}
      </div>
      <div className="crop-actions">
        {growing ? <>
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/disease-prediction', { state: { plant: c.crop } })} title="Check this crop for disease"><LuMicroscope size={15} /> Scan</button>
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/assistant', { state: { prompt: `My ${c.crop}${c.days_since_sowing != null ? ` is ${c.days_since_sowing} days after sowing` : ''}. What should I do for it this week?` } })} title="Ask Krishi Mitra about this crop"><LuMessagesSquare size={15} /> Ask</button>
          <button className="btn btn-ghost btn-sm" onClick={() => update({ status: 'harvested' }, `${c.crop} marked as harvested`)} title="Mark as harvested"><LuCheck size={15} /> Harvested</button>
        </> : (
          <button className="btn btn-ghost btn-sm" onClick={() => update({ status: 'growing' }, `${c.crop} is growing again`)} title="Undo harvest"><LuRotateCcw size={15} /> Undo</button>
        )}
        <button className="icon-btn" onClick={remove} title="Remove" aria-label={`Remove ${c.crop}`}><LuTrash2 size={15} /></button>
      </div>
    </div>
  )
}

/* ── History ──────────────────────────────────────────── */
function History() {
  const [items, setItems] = useState(null)
  const [counts, setCounts] = useState({})
  const [kind, setKind] = useState('')
  const [shown, setShown] = useState(15)

  useEffect(() => {
    setItems(null)
    api.get('/farm/history', { params: { kind: kind || undefined, limit: 500 } })
      .then(({ data }) => { setItems(data.history || []); if (!kind) setCounts(data.counts || {}) })
      .catch(() => setItems([]))
  }, [kind])

  const groups = useMemo(() => {
    const g = []
    ;(items || []).slice(0, shown).forEach(a => {
      const d = toDate(a.created_at)
      const key = d.toDateString()
      if (!g.length || g[g.length - 1].key !== key) g.push({ key, label: d.toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }), items: [] })
      g[g.length - 1].items.push({ ...a, time: d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }) })
    })
    return g
  }, [items, shown])

  const total = Object.values(counts).reduce((s, n) => s + n, 0)

  return (
    <section style={{ marginTop: 32 }}>
      <div className="section-head">
        <h2 className="section-title" style={{ marginBottom: 0 }}>Farm history</h2>
        <span className="muted" style={{ fontSize: '0.85rem' }}>{total} {total === 1 ? 'entry' : 'entries'}</span>
      </div>
      <div className="filter-row">
        <button className={`chip${kind === '' ? ' on' : ''}`} onClick={() => { setKind(''); setShown(15) }}>All</button>
        {Object.entries(counts).sort((a, b) => b[1] - a[1]).map(([k, n]) => (
          <button key={k} className={`chip${kind === k ? ' on' : ''}`} onClick={() => { setKind(k); setShown(15) }}>
            {KIND[k]?.label || k} <span className="muted">{n}</span>
          </button>
        ))}
      </div>
      <div className="card" style={{ padding: '4px 20px' }}>
        {items === null && <div className="loading-screen" style={{ minHeight: 120 }}><div className="spinner" /></div>}
        {items?.length === 0 && (
          <div className="empty-state" style={{ padding: '28px 8px' }}>
            <LuHistory size={28} />
            <p>Everything you do — sowing, scans, soil tests, plans and harvests — is recorded here.</p>
          </div>
        )}
        {groups.map(g => (
          <div key={g.key} className="history-day">
            <div className="history-date">{g.label}</div>
            {g.items.map(a => (
              <div key={a.id} className="history-item">
                <span className="history-time">{a.time}</span>
                <span className={`badge ${KIND[a.kind]?.cls || 'badge-neutral'}`}>{KIND[a.kind]?.label || a.kind}</span>
                <span className="history-text">{a.title}</span>
              </div>
            ))}
          </div>
        ))}
        {items && items.length > shown && (
          <div style={{ textAlign: 'center', padding: '12px 0 14px' }}>
            <button className="btn btn-secondary btn-sm" onClick={() => setShown(s => s + 30)}>Show older entries ({items.length - shown} more)</button>
          </div>
        )}
      </div>
    </section>
  )
}

/* ── Page ─────────────────────────────────────────────── */
export default function Dashboard() {
  const { user, updateUser } = useAuth()
  const [data, setData] = useState(null)
  const [editCity, setEditCity] = useState(false)
  const [adding, setAdding] = useState(false)
  const [showHarvested, setShowHarvested] = useState(false)
  const [historyKey, setHistoryKey] = useState(0)

  const load = () => api.get('/farm/overview').then(({ data }) => data.success && setData(data)).catch(() => setData({ crops: [], weather: {}, error: true }))
  const refresh = () => { load(); setHistoryKey(k => k + 1) }
  useEffect(() => { load() }, [])

  const growing = (data?.crops || []).filter(c => c.status === 'growing')
  const harvested = (data?.crops || []).filter(c => c.status !== 'growing')
  const w = data?.weather || {}
  const cur = w.current

  const citySaved = (res) => {
    updateUser(res.user)
    setEditCity(false)
    toast.success(`Farm location set to ${res.city}`)
    refresh()
  }

  const today = new Date().toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long' })

  return (
    <div className="page-container fade-in">
      <header className="page-header">
        <div className="page-eyebrow">{today}</div>
        <h1 className="page-title">{greeting()}, {user?.name?.split(' ')[0]}</h1>
        <div className="page-subtitle" style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          {data?.city && !editCity && <>
            <LuMapPin size={15} /> Farm in <strong style={{ color: 'var(--ink)' }}>{data.city}</strong>
            <button className="btn btn-ghost btn-sm" onClick={() => setEditCity(true)}><LuPencil size={13} /> Change</button>
          </>}
          {data && !data.city && !editCity && 'Add where your farm is to see local weather and alerts.'}
        </div>
        {editCity && <div style={{ marginTop: 12, maxWidth: 520 }}><CityForm initial={data?.city || ''} onSaved={citySaved} onCancel={() => setEditCity(false)} /></div>}
      </header>

      {!data && <div className="loading-screen"><div className="spinner" /><p>Loading your farm…</p></div>}

      {data && <>
        {/* Weather + alerts */}
        {!data.city ? (
          <div className="card" style={{ padding: 22, marginBottom: 24 }}>
            <div className="card-title"><LuMapPin size={18} /> Where is your farm?</div>
            <p className="muted" style={{ marginBottom: 14, fontSize: '0.9rem' }}>We'll remember it and show the weather and field alerts for your area every time you open the app.</p>
            <div style={{ maxWidth: 520 }}><CityForm onSaved={citySaved} /></div>
          </div>
        ) : (
          <div className="farm-top">
            <div className="card weather-card">
              {w.error && <div className="alert alert-warning" style={{ margin: 0 }}>{w.error}</div>}
              {cur && <>
                <div className="weather-now">
                  <div style={{ color: 'var(--ink-3)' }}><SkyIcon desc={cur.description} size={44} /></div>
                  <div>
                    <div className="weather-now-temp">{Math.round(cur.temperature)}°C</div>
                    <div className="muted" style={{ fontSize: '0.88rem' }}>{cur.description} · feels like {Math.round(cur.feels_like)}°</div>
                  </div>
                  <div className="weather-now-stats">
                    <span><LuDroplets size={14} /> {cur.humidity}% humidity</span>
                    <span><LuWind size={14} /> {cur.wind_speed} km/h wind</span>
                    <span><LuCloudRain size={14} /> {cur.rainfall_1h} mm rain (1 h)</span>
                  </div>
                </div>
                <div className="forecast-strip">
                  {w.days.map((d, i) => (
                    <div key={d.date} className="forecast-day">
                      <div className="fd-name">{i === 0 ? 'Today' : fmtDay(d.date)}</div>
                      <div style={{ color: 'var(--ink-3)', margin: '4px 0' }}><SkyIcon desc={d.rain_mm > 0.5 ? 'rain' : d.description} size={22} /></div>
                      <div className="fd-temp"><strong>{Math.round(d.temp_max)}°</strong> <span className="muted">{Math.round(d.temp_min)}°</span></div>
                      <div className="fd-rain">{d.rain_mm > 0 ? `${d.rain_mm} mm` : `${d.rain_chance}%`}</div>
                    </div>
                  ))}
                </div>
              </>}
            </div>

            <div className="card" style={{ padding: '18px 20px' }}>
              <div className="card-title">This week in your field</div>
              {(w.alerts || []).map((a, i) => (
                <div key={i} className={`alert alert-${a.level === 'success' ? 'success' : a.level}`} style={{ marginBottom: 10 }}>
                  <strong>{a.title}</strong>
                  <div style={{ fontSize: '0.86rem', marginTop: 2, color: 'var(--ink-2)' }}>{a.text}</div>
                </div>
              ))}
              {!w.alerts?.length && !w.error && <p className="muted" style={{ fontSize: '0.88rem' }}>No alerts right now.</p>}
            </div>
          </div>
        )}

        {/* Crops */}
        <section>
          <div className="section-head">
            <h2 className="section-title" style={{ marginBottom: 0 }}>What's growing</h2>
            {!adding && <button className="btn btn-primary btn-sm" onClick={() => setAdding(true)}><LuPlus size={15} /> Add a crop</button>}
          </div>
          {adding && <CropForm onSaved={() => { setAdding(false); refresh() }} onCancel={() => setAdding(false)} />}
          <div className="card">
            {growing.length === 0 && !adding && (
              <div className="empty-state" style={{ padding: '30px 16px' }}>
                <LuSprout size={30} />
                <p>Add the crops you have sown — any plant. You can also just tell Krishi Mitra “I sowed onion last week” and it will add it.</p>
              </div>
            )}
            {growing.map(c => <CropRow key={c.id} c={c} onChange={refresh} />)}
          </div>
          {harvested.length > 0 && (
            <div style={{ marginTop: 10 }}>
              <button className="btn btn-ghost btn-sm" onClick={() => setShowHarvested(s => !s)}>
                {showHarvested ? <LuX size={14} /> : <LuHistory size={14} />} {showHarvested ? 'Hide' : 'Show'} harvested crops ({harvested.length})
              </button>
              {showHarvested && <div className="card" style={{ marginTop: 8 }}>{harvested.map(c => <CropRow key={c.id} c={c} onChange={refresh} />)}</div>}
            </div>
          )}
        </section>

        {/* Tools */}
        <div className="tool-chips">
          {TOOLS.map(({ to, icon: Icon, label }) => (
            <Link key={to} to={to} className="chip"><Icon size={15} /> {label}</Link>
          ))}
          <Link to="/assistant" className="chip"><LuMessagesSquare size={15} /> Ask Krishi Mitra</Link>
        </div>

        <History key={historyKey} />
      </>}
    </div>
  )
}
