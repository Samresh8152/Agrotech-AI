import { useState, useRef, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { LuImagePlus, LuX, LuMessagesSquare, LuLeaf } from 'react-icons/lu'
import api from '../services/api'
import toast from 'react-hot-toast'

const COMMON_PLANTS = [
  'Tomato','Potato','Rice','Wheat','Corn (Maize)','Cotton','Sugarcane','Soybean','Chilli','Bell Pepper',
  'Brinjal (Eggplant)','Okra','Onion','Cabbage','Cauliflower','Cucumber','Pumpkin','Groundnut','Mustard',
  'Chickpea','Banana','Mango','Apple','Grape','Orange','Papaya','Guava','Pomegranate','Strawberry','Peach',
  'Cherry','Tea','Coffee','Coconut','Rose','Tulsi',
]

const SEVERITY_BADGE = { High: 'badge-danger', Medium: 'badge-warning', Low: 'badge-info' }

const SOURCE_LABEL = { ensemble: 'Gemini + our model', gemini: 'Gemini', local_model: 'Our model (offline)' }

const AGREEMENT = {
  agree: { cls: 'alert-success', text: 'Both models reached the same diagnosis.' },
  gemini_preferred: { cls: 'alert-info', text: 'The two models disagreed. Gemini was more certain, so its answer is shown. Our model\'s answer is below.' },
  cnn_preferred: { cls: 'alert-warning', text: 'The two models disagreed. Our model was more certain, so its answer is shown — please confirm with a closer photo or an expert.' },
  gemini_only: { cls: 'alert-info', text: 'This condition is outside what our model was trained on, so Gemini\'s diagnosis is used.' },
}

function InfoBlock({ title, items }) {
  if (!items?.length) return null
  return (
    <div className="info-block">
      <h4>{title}</h4>
      <ul>{items.map((t, i) => <li key={i}>{t}</li>)}</ul>
    </div>
  )
}

export default function DiseasePrediction() {
  const [image, setImage] = useState(null)
  const [preview, setPreview] = useState(null)
  const location = useLocation()
  const [plantName, setPlantName] = useState(location.state?.plant || '')
  const [result, setResult] = useState(null)
  const [warnings, setWarnings] = useState([])
  const [loading, setLoading] = useState(false)
  const [drag, setDrag] = useState(false)
  const [support, setSupport] = useState({ gemini_enabled: true, local_model_plants: [] })
  const fileRef = useRef()
  const navigate = useNavigate()

  useEffect(() => {
    api.get('/disease/plants').then(({ data }) => data.success && setSupport(data)).catch(() => {})
  }, [])

  const handleFile = (file) => {
    if (!file) return
    setImage(file)
    setPreview(URL.createObjectURL(file))
    setResult(null)
    setWarnings([])
  }

  const reset = () => { setImage(null); setPreview(null); setResult(null); setWarnings([]) }

  const handlePredict = async () => {
    if (!plantName.trim()) return toast.error('Enter the plant name first')
    if (!image) return toast.error('Add a photo of the leaf')
    setLoading(true)
    try {
      const fd = new FormData()
      fd.append('image', image)
      fd.append('plant_name', plantName.trim())
      const { data } = await api.post('/disease/predict', fd, { headers:{'Content-Type':'multipart/form-data'}, timeout: 90000 })
      if (data.success) { setResult(data.prediction); setWarnings(data.warnings || []) }
      else toast.error(data.message)
    } catch (e) { toast.error(e.response?.data?.message || 'Prediction failed') }
    finally { setLoading(false) }
  }

  const local = result?.local_model
  const showLocalOpinion = result?.source === 'gemini' && local && !result.ensemble
  const ens = result?.ensemble

  const askAssistant = () => navigate('/assistant', { state: { prompt:
    `My ${result.plant_identified || result.plant} was just diagnosed with ${result.disease} (${result.severity} severity). ` +
    'Please give me a step-by-step treatment and care plan for the next 2 weeks, based on my farm details.' } })

  return (
    <div className="page-container fade-in">
      <header className="page-header">
        <div className="page-eyebrow">Diagnose</div>
        <h1 className="page-title">Plant disease check</h1>
        <p className="page-subtitle">Tell us the plant and add a clear photo of the affected leaf. Gemini checks every plant; for the crops listed at the bottom, our own trained model gives a second opinion.</p>
      </header>

      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(320px,1fr))',gap:'24px',alignItems:'start'}}>
        {/* Input */}
        <div className="card" style={{padding:'24px'}}>
          <div className="form-group">
            <label className="form-label" htmlFor="plant">1. Plant name</label>
            <input
              id="plant"
              className="form-input"
              list="plant-options"
              placeholder="e.g. Tomato, tamatar, rice, mango"
              value={plantName}
              onChange={e => setPlantName(e.target.value)}
              maxLength={60}
            />
            <datalist id="plant-options">
              {COMMON_PLANTS.map(p => <option key={p} value={p} />)}
            </datalist>
          </div>

          <label className="form-label">2. Leaf photo</label>
          <div
            className={`upload-zone${drag ? ' drag-over' : ''}`}
            onClick={() => fileRef.current.click()}
            onDragOver={e => { e.preventDefault(); setDrag(true) }}
            onDragLeave={() => setDrag(false)}
            onDrop={e => { e.preventDefault(); setDrag(false); handleFile(e.dataTransfer.files[0]) }}
            role="button"
            tabIndex={0}
            onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && fileRef.current.click()}
          >
            {preview ? (
              <img src={preview} alt="Selected leaf" style={{maxHeight:240,borderRadius:8,objectFit:'cover',width:'100%'}} />
            ) : (
              <>
                <div className="upload-icon"><LuImagePlus size={30} /></div>
                <p style={{fontWeight:500}}>Drop a photo here or click to choose</p>
                <p className="muted" style={{fontSize:'0.85rem',marginTop:4}}>A close, well-lit photo of the affected part works best. JPG, PNG or WebP.</p>
              </>
            )}
          </div>
          <input ref={fileRef} type="file" accept="image/png,image/jpeg,image/webp" onChange={e => handleFile(e.target.files[0])} style={{display:'none'}} />

          <div style={{display:'flex',gap:'10px',marginTop:'16px'}}>
            <button className="btn btn-primary btn-lg" onClick={handlePredict} disabled={loading || !image} style={{flex:1,justifyContent:'center'}}>
              {loading ? 'Checking the leaf…' : 'Check for disease'}
            </button>
            {preview && <button className="btn btn-secondary btn-lg" onClick={reset} aria-label="Remove photo"><LuX size={18} /></button>}
          </div>
        </div>

        {/* Result */}
        <div className="card" style={{padding:'24px'}}>
          <div className="card-title">Result</div>
          {loading && <div className="loading-screen"><div className="spinner"/><p>Looking at your {plantName || 'plant'}… this can take up to a minute.</p></div>}
          {!loading && !result && (
            <div className="empty-state">
              <LuLeaf size={34} />
              <p>The diagnosis will appear here.</p>
            </div>
          )}
          {!loading && result && (
            <div className="fade-in">
              {warnings.map((w,i) => <div key={i} className="alert alert-info">{w}</div>)}

              {result.is_plant_image === false ? (
                <div className="alert alert-danger">
                  <strong>We couldn't find a plant in this photo.</strong> {result.description}
                </div>
              ) : (
                <>
                  {!result.plant_matches_input && (
                    <div className="alert alert-warning">
                      You entered <strong>{plantName}</strong>, but the photo looks like <strong>{result.plant_identified}</strong>. The diagnosis is based on the photo.
                    </div>
                  )}

                  <div className={`diagnosis-head ${result.is_healthy ? 'healthy' : 'sick'}`}>
                    <div className="plant">{result.plant_identified || result.plant}</div>
                    <h2>{result.disease}</h2>
                    {result.scientific_name && <div className="sci">{result.scientific_name}</div>}
                    <div className="tags">
                      <span className={`badge ${result.is_healthy ? 'badge-success' : (SEVERITY_BADGE[result.severity] || 'badge-info')}`}>
                        {result.is_healthy ? 'Healthy' : `${result.severity} severity`}
                      </span>
                      {!result.is_healthy && result.pathogen_type && result.pathogen_type !== 'None' && (
                        <span className="badge badge-orange">{result.pathogen_type}</span>
                      )}
                      <span className="badge badge-neutral">{result.confidence}% confident</span>
                      <span className="badge badge-neutral">{SOURCE_LABEL[result.source]}</span>
                    </div>
                  </div>

                  {ens && (
                    <div style={{marginBottom:'14px'}}>
                      {AGREEMENT[ens.agreement] && <div className={`alert ${AGREEMENT[ens.agreement].cls}`}>{AGREEMENT[ens.agreement].text}</div>}
                      <div className="opinion-grid">
                        {[['Gemini', ens.gemini, ens.weights.gemini], ['Our model', ens.cnn, ens.weights.cnn]].map(([label, o, w]) => (
                          <div key={label} className="opinion">
                            <div className="who">{label} · weight {Math.round(w * 100)}%</div>
                            <div className="what">{o.disease}</div>
                            <div className="num">{o.confidence}%</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {result.description && <p style={{fontSize:'0.92rem',margin:'4px 0 10px'}}>{result.description}</p>}
                  <InfoBlock title="Symptoms" items={result.symptoms} />
                  <InfoBlock title="Causes" items={result.causes} />
                  <InfoBlock title="Organic treatment" items={result.organic_treatment} />
                  <InfoBlock title="Chemical treatment" items={result.chemical_treatment} />
                  {!result.organic_treatment?.length && !result.chemical_treatment?.length && result.treatment && !result.is_healthy && (
                    <div className="info-block"><h4>Treatment</h4><p style={{fontSize:'0.9rem'}}>{result.treatment}</p></div>
                  )}
                  <InfoBlock title="Prevention" items={result.prevention} />
                  {result.image_quality_note && <div className="alert alert-info" style={{marginTop:10}}>{result.image_quality_note}</div>}

                  {result.top_predictions?.length > 1 && (
                    <div className="info-block">
                      <h4>Other possibilities</h4>
                      {result.top_predictions.map((p,i) => (
                        <div key={i} style={{display:'flex',justifyContent:'space-between',padding:'5px 0',fontSize:'0.86rem'}}>
                          <span>{p.disease}</span>
                          <span style={{fontFamily:'var(--font-mono)',color:'var(--ink-3)'}}>{p.confidence}%</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {showLocalOpinion && (
                    <div className="info-block" style={{fontSize:'0.86rem',color:'var(--ink-2)'}}>
                      Our model's second opinion: <strong>{local.disease}</strong> ({local.confidence}%){local.uncertain && ' – low confidence'}
                    </div>
                  )}

                  {!result.is_healthy && (
                    <button className="btn btn-secondary" onClick={askAssistant} style={{width:'100%',justifyContent:'center',marginTop:'12px'}}>
                      <LuMessagesSquare size={17} /> Ask Krishi Mitra for a treatment plan
                    </button>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="card" style={{padding:'20px 24px',marginTop:'24px'}}>
        <div className="card-title" style={{marginBottom:8}}>Crops our own model knows</div>
        <p className="muted" style={{fontSize:'0.88rem',marginBottom:'12px'}}>
          {support.gemini_enabled
            ? 'Any plant can be checked. For these crops our trained model also gives an answer, and it keeps working without internet.'
            : 'Gemini is not set up, so only these crops can be checked right now.'}
        </p>
        <div style={{display:'flex',flexWrap:'wrap',gap:'6px'}}>
          {support.local_model_plants.map(p => <span key={p} className="badge badge-neutral">{p}</span>)}
        </div>
      </div>
    </div>
  )
}
