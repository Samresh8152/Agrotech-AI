import { useState, useEffect, useRef, Fragment } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import api from '../services/api'
import toast from 'react-hot-toast'
import { useAuth } from '../contexts/AuthContext'
import { LuEraser, LuSendHorizontal, LuX } from 'react-icons/lu'

const SUGGESTIONS = [
  'What should I sow this season on my farm?',
  'How do I treat the disease from my last scan?',
  'Mere gehun ki fasal mein peele patte aa rahe hain, kya karun?',
  'Make a weekly care plan for my crops',
]

const ACTIVITY_LABEL = {
  disease_scan: 'Disease scan', soil_test: 'Soil test', crop_recommendation: 'Crop advice', yield_prediction: 'Yield', fertilizer: 'Fertilizer',
}

// Render **bold** inside a line
function inline(text) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith('**') && part.endsWith('**')
      ? <strong key={i}>{part.slice(2, -2)}</strong>
      : <Fragment key={i}>{part}</Fragment>
  )
}

// Minimal markdown: headings, bullet / numbered lists, bold, paragraphs
function RichText({ text }) {
  const blocks = []
  let list = null
  text.split('\n').forEach((raw, i) => {
    const line = raw.trimEnd()
    const bullet = line.match(/^\s*(?:[-*•]|\d+[.)])\s+(.*)/)
    if (bullet) {
      if (!list) { list = []; blocks.push(<ul key={`ul${i}`} style={{margin:'4px 0 8px 18px',padding:0}}>{list}</ul>) }
      list.push(<li key={i} style={{marginBottom:'3px'}}>{inline(bullet[1])}</li>)
      return
    }
    list = null
    if (!line.trim()) return
    const heading = line.match(/^#{1,4}\s+(.*)/)
    blocks.push(heading
      ? <p key={i} style={{fontWeight:700,margin:'8px 0 4px'}}>{inline(heading[1])}</p>
      : <p key={i} style={{margin:'0 0 6px'}}>{inline(line)}</p>)
  })
  return <>{blocks}</>
}

export default function Assistant() {
  const { user } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const [messages, setMessages] = useState([])
  const [memories, setMemories] = useState([])
  const [activity, setActivity] = useState([])
  const [enabled, setEnabled] = useState(true)
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const [newFact, setNewFact] = useState('')
  const endRef = useRef()
  const prefillSent = useRef(false)

  const load = async () => {
    try {
      const { data } = await api.get('/assistant/history')
      if (data.success) {
        setMessages(data.messages); setMemories(data.memories); setActivity(data.activity); setEnabled(data.gemini_enabled)
      }
    } catch { toast.error('Could not load assistant history') }
    finally { setLoaded(true) }
  }

  useEffect(() => { load() }, [])
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, sending])

  const send = async (text) => {
    const msg = (text ?? input).trim()
    if (!msg || sending) return
    setInput('')
    setSending(true)
    const pending = { id: `p${Date.now()}`, role: 'user', content: msg }
    setMessages(m => [...m, pending])
    try {
      const { data } = await api.post('/assistant/chat', { message: msg }, { timeout: 90000 })
      if (data.success) {
        setMessages(m => [...m.filter(x => x.id !== pending.id), data.user_message, data.reply])
        if (data.crops_added?.length) toast.success(`Added to your farm: ${data.crops_added.join(', ')}`)
        if (data.city_set) toast.success(`Farm location saved: ${data.city_set}`)
        if (data.new_facts?.length) {
          toast.success(`Remembered: ${data.new_facts[0]}${data.new_facts.length > 1 ? ` (+${data.new_facts.length - 1})` : ''}`)
          load()
        }
      } else throw new Error(data.message)
    } catch (e) {
      setMessages(m => m.filter(x => x.id !== pending.id))
      setInput(msg)
      toast.error(e.response?.data?.message || e.message || 'Assistant failed')
    } finally { setSending(false) }
  }

  // A question handed over from another page (e.g. "Ask assistant" on a disease result)
  useEffect(() => {
    const prompt = location.state?.prompt
    if (loaded && prompt && !prefillSent.current) {
      prefillSent.current = true
      navigate(location.pathname, { replace: true, state: null })
      send(prompt)
    }
  }, [loaded])

  const clearChat = async () => {
    if (!window.confirm('Clear the whole conversation? Remembered facts are kept.')) return
    await api.delete('/assistant/history')
    setMessages([])
  }

  const forget = async (id) => {
    await api.delete(`/assistant/memory/${id}`)
    setMemories(m => m.filter(x => x.id !== id))
  }

  const remember = async (e) => {
    e.preventDefault()
    if (!newFact.trim()) return
    await api.post('/assistant/memory', { fact: newFact })
    setNewFact('')
    load()
  }

  return (
    <div className="page-container fade-in">
      <header className="page-header">
        <div className="page-eyebrow">Assistant</div>
        <h1 className="page-title">Krishi Mitra</h1>
        <p className="page-subtitle">Ask about your crops, pests, soil, fertilizer or weather. It remembers your farm and your recent scans, so you don't have to repeat yourself.</p>
      </header>

      {!enabled && (
        <div className="alert alert-warning">The assistant needs a Gemini API key. Add <code>GEMINI_API_KEY</code> to the backend <code>.env</code> file.</div>
      )}

      <div className="assistant-grid">
        {/* Chat */}
        <div className="card" style={{padding:'18px 20px',minWidth:0,display:'flex',flexDirection:'column'}}>
          <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:'10px'}}>
            <div className="card-title" style={{marginBottom:0}}>Conversation</div>
            {messages.length > 0 && <button className="btn btn-ghost btn-sm" onClick={clearChat}><LuEraser size={15} /> Clear</button>}
          </div>

          <div className="chat-log">
            {loaded && messages.length === 0 && (
              <div style={{padding:'28px 8px',color:'var(--ink-2)'}}>
                <p style={{fontFamily:'var(--font-display)',fontSize:'1.25rem',color:'var(--ink)'}}>Namaste {user?.name?.split(' ')[0]}.</p>
                <p className="muted" style={{margin:'4px 0 16px'}}>Try one of these, or type your own question:</p>
                <div style={{display:'flex',flexWrap:'wrap',gap:'8px'}}>
                  {SUGGESTIONS.map(s => (
                    <button key={s} className="chip" onClick={() => send(s)} disabled={!enabled}>{s}</button>
                  ))}
                </div>
              </div>
            )}
            {messages.map(m => (
              <div key={m.id} className={`msg ${m.role === 'user' ? 'user' : 'bot'}`}>
                {m.role === 'user'
                  ? <span style={{whiteSpace:'pre-wrap'}}>{m.content}</span>
                  : <><div className="who">Krishi Mitra</div><RichText text={m.content} /></>}
              </div>
            ))}
            {sending && (
              <div className="msg bot" aria-label="Krishi Mitra is typing"><div className="typing"><span/><span/><span/></div></div>
            )}
            <div ref={endRef} />
          </div>

          <form onSubmit={e => { e.preventDefault(); send() }} className="chat-form">
            <textarea
              className="form-input"
              rows={2}
              style={{resize:'none',flex:1}}
              placeholder="Type in English or Hindi. Enter to send, Shift+Enter for a new line."
              value={input}
              maxLength={2000}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
              disabled={!enabled}
            />
            <button className="btn btn-primary btn-lg" type="submit" disabled={sending || !input.trim() || !enabled} aria-label="Send">
              <LuSendHorizontal size={18} />
            </button>
          </form>
        </div>

        {/* Context panel */}
        <div style={{display:'flex',flexDirection:'column',gap:'20px',minWidth:0}}>
          <div className="card" style={{padding:'18px 20px'}}>
            <div className="card-title" style={{marginBottom:4}}>What it remembers</div>
            <p className="muted" style={{fontSize:'0.82rem',marginBottom:'8px'}}>Picked up from your chats. Remove anything that's wrong.</p>
            {memories.length === 0 && <p className="muted" style={{fontSize:'0.86rem',padding:'6px 0'}}>Nothing yet. Tell it about your farm — crops, acres, irrigation.</p>}
            {memories.map(m => (
              <div key={m.id} className="fact-row">
                <span>{m.fact}</span>
                <button className="icon-btn" onClick={() => forget(m.id)} title="Forget this" aria-label="Forget this"><LuX size={15} /></button>
              </div>
            ))}
            <form onSubmit={remember} style={{display:'flex',gap:'8px',marginTop:'12px'}}>
              <input className="form-input" style={{flex:1,padding:'7px 10px',fontSize:'0.88rem'}} placeholder="e.g. I grow sugarcane on 5 acres" value={newFact} onChange={e => setNewFact(e.target.value)} maxLength={300} />
              <button className="btn btn-secondary btn-sm" type="submit">Add</button>
            </form>
          </div>

          <div className="card" style={{padding:'18px 20px'}}>
            <div className="card-title" style={{marginBottom:4}}>Recent activity</div>
            {activity.length === 0 && <p className="muted" style={{fontSize:'0.86rem',padding:'6px 0'}}>Disease scans, soil tests and plans you run will show up here.</p>}
            <ul className="timeline">
              {activity.map(a => (
                <li key={a.id}>
                  <span className="badge badge-neutral" style={{marginRight:6}}>{ACTIVITY_LABEL[a.kind] || a.kind}</span>
                  {a.title}
                  <div className="when">{new Date(/[zZ]|[+-]\d\d:\d\d$/.test(a.created_at) ? a.created_at : a.created_at + 'Z').toLocaleString()}</div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
