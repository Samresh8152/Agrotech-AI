import { useState, useEffect } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import api from '../services/api'
import toast from 'react-hot-toast'
import AuthLayout from '../components/AuthLayout'

export default function Register() {
  const [step, setStep] = useState('register') // register | otp
  const [form, setForm] = useState({ name:'', email:'', password:'', phone:'', location:'' })
  const [otp, setOtp] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()

  useEffect(() => {
    if (params.get('step') === 'otp' && params.get('email')) {
      setForm(f => ({...f, email: params.get('email')}))
      setStep('otp')
    }
  }, [params])

  const handleRegister = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      const { data } = await api.post('/auth/register', form)
      if (data.success) {
        toast.success('We emailed you a 6-digit code')
        setStep('otp')
      } else toast.error(data.message)
    } catch (err) { toast.error(err.response?.data?.message || 'Registration failed') }
    finally { setLoading(false) }
  }

  const handleVerifyOtp = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      const { data } = await api.post('/auth/verify-otp', { email: form.email, otp })
      if (data.success) {
        login(data.access_token, data.user)
        toast.success('Email verified. Welcome to AgroTech AI')
        navigate('/dashboard')
      } else toast.error(data.message)
    } catch (err) { toast.error(err.response?.data?.message || 'OTP verification failed') }
    finally { setLoading(false) }
  }

  const resendOtp = async () => {
    try {
      await api.post('/auth/resend-otp', { email: form.email })
      toast.success('Code sent again')
    } catch { toast.error('Could not resend the code') }
  }

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  if (step === 'otp') return (
    <AuthLayout>
      <h1>Check your email</h1>
      <p className="auth-sub">Enter the 6-digit code we sent to <strong style={{color:'var(--ink)'}}>{form.email}</strong>.</p>
      <form onSubmit={handleVerifyOtp}>
        <div className="form-group">
          <label className="form-label" htmlFor="otp">Verification code</label>
          <input id="otp" className="form-input" type="text" inputMode="numeric" autoComplete="one-time-code" placeholder="000000" maxLength={6}
            value={otp} onChange={e => setOtp(e.target.value.replace(/\D/g,''))} required
            style={{textAlign:'center',fontSize:'1.5rem',letterSpacing:'0.5em',fontFamily:'var(--font-mono)'}} />
        </div>
        <button className="btn btn-primary btn-lg" type="submit" disabled={loading || otp.length!==6} style={{width:'100%',justifyContent:'center'}}>
          {loading ? 'Verifying…' : 'Verify and continue'}
        </button>
      </form>
      <p className="auth-foot">Didn't get it? <button onClick={resendOtp} className="link">Send the code again</button></p>
    </AuthLayout>
  )

  return (
    <AuthLayout>
      <h1>Create your account</h1>
      <p className="auth-sub">It takes a minute. We'll email you a code to confirm.</p>
      <form onSubmit={handleRegister}>
        <div className="input-row">
          <div className="form-group">
            <label className="form-label" htmlFor="name">Full name</label>
            <input id="name" className="form-input" type="text" autoComplete="name" value={form.name} onChange={set('name')} required />
          </div>
          <div className="form-group">
            <label className="form-label" htmlFor="phone">Phone <span className="muted">(optional)</span></label>
            <input id="phone" className="form-input" type="tel" autoComplete="tel" placeholder="+91" value={form.phone} onChange={set('phone')} />
          </div>
        </div>
        <div className="form-group">
          <label className="form-label" htmlFor="email">Email</label>
          <input id="email" className="form-input" type="email" autoComplete="email" placeholder="you@example.com" value={form.email} onChange={set('email')} required />
        </div>
        <div className="form-group">
          <label className="form-label" htmlFor="password">Password</label>
          <input id="password" className="form-input" type="password" autoComplete="new-password" value={form.password} onChange={set('password')} required minLength={6} />
          <div className="form-hint">At least 6 characters.</div>
        </div>
        <div className="form-group">
          <label className="form-label" htmlFor="location">Village / district</label>
          <input id="location" className="form-input" type="text" placeholder="e.g. Nashik, Maharashtra" value={form.location} onChange={set('location')} />
          <div className="form-hint">Used for weather and local advice.</div>
        </div>
        <button className="btn btn-primary btn-lg" type="submit" disabled={loading} style={{width:'100%',justifyContent:'center'}}>
          {loading ? 'Sending code…' : 'Create account'}
        </button>
      </form>
      <p className="auth-foot">Already registered? <Link to="/login" className="link">Sign in</Link></p>
    </AuthLayout>
  )
}
