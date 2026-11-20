import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import api from '../services/api'
import toast from 'react-hot-toast'
import AuthLayout from '../components/AuthLayout'

export default function Login() {
  const [form, setForm] = useState({ email: '', password: '' })
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      const { data } = await api.post('/auth/login', form)
      if (data.success) {
        login(data.access_token, data.user)
        toast.success(`Welcome back, ${data.user.name.split(' ')[0]}`)
        navigate('/dashboard')
      } else {
        if (data.needs_verification) {
          toast.error('Email not verified. We sent a new code.')
          navigate(`/register?email=${form.email}&step=otp`)
        } else toast.error(data.message)
      }
    } catch (err) {
      toast.error(err.response?.data?.message || 'Login failed')
    } finally { setLoading(false) }
  }

  return (
    <AuthLayout>
      <h1>Sign in</h1>
      <p className="auth-sub">Welcome back. Enter your details to continue.</p>

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label className="form-label" htmlFor="email">Email</label>
          <input id="email" className="form-input" type="email" placeholder="you@example.com" autoComplete="email"
            value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} required />
        </div>
        <div className="form-group">
          <label className="form-label" htmlFor="password">Password</label>
          <input id="password" className="form-input" type="password" autoComplete="current-password"
            value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} required />
        </div>
        <button className="btn btn-primary btn-lg" type="submit" disabled={loading} style={{ width: '100%', justifyContent: 'center' }}>
          {loading ? 'Signing in…' : 'Sign in'}
        </button>
      </form>

      <p className="auth-foot">New here? <Link to="/register" className="link">Create an account</Link></p>

      <div className="demo-note">
        Demo account: <strong>demo@agri.com</strong> / <strong>Demo@12345</strong>
      </div>
    </AuthLayout>
  )
}
