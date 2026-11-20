import { NavLink, useNavigate } from 'react-router-dom'
import {
  LuLayoutDashboard, LuMessagesSquare, LuMicroscope, LuShovel, LuCloudSun, LuSprout, LuChartColumn,
  LuFlaskConical, LuStore, LuShoppingCart, LuPackage, LuWarehouse, LuLogOut,
} from 'react-icons/lu'
import { useAuth } from '../contexts/AuthContext'
import { useCart } from '../contexts/CartContext'
import toast from 'react-hot-toast'
import { FEATURES } from '../config'

const NAV = [
  { section: null, items: [
    { to: '/dashboard', icon: LuLayoutDashboard, label: 'My farm' },
    { to: '/assistant', icon: LuMessagesSquare, label: 'Krishi Mitra' },
  ]},
  { section: 'Diagnose', items: [
    { to: '/disease-prediction', icon: LuMicroscope, label: 'Plant disease' },
    { to: '/soil-prediction', icon: LuShovel, label: 'Soil health' },
    { to: '/weather', icon: LuCloudSun, label: 'Weather' },
  ]},
  { section: 'Plan', items: [
    { to: '/crop-recommendation', icon: LuSprout, label: 'What to sow' },
    { to: '/yield-prediction', icon: LuChartColumn, label: 'Yield estimate' },
    { to: '/fertilizer', icon: LuFlaskConical, label: 'Fertilizer plan' },
  ]},
  FEATURES.marketplace && { section: 'Market', items: [
    { to: '/marketplace', icon: LuStore, label: 'Marketplace' },
    { to: '/cart', icon: LuShoppingCart, label: 'Cart' },
    { to: '/orders', icon: LuPackage, label: 'Orders' },
    { to: '/seller', icon: LuWarehouse, label: 'My listings' },
  ]},
].filter(Boolean)

export function BrandMark({ size = 18 }) {
  return (
    <span className="brand-mark">
      <span className="mark"><LuSprout size={size} /></span>
      AgroTech AI
    </span>
  )
}

export default function Sidebar({ open = false, onNavigate }) {
  const { user, logout } = useAuth()
  const { cartCount } = useCart()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    toast.success('Signed out')
    navigate('/login')
  }

  return (
    <aside className={`sidebar${open ? ' open' : ''}`}>
      <div className="sidebar-logo"><BrandMark /></div>

      <nav className="sidebar-nav">
        {NAV.map((group, gi) => (
          <div key={gi}>
            {group.section && <div className="nav-section-label">{group.section}</div>}
            {group.items.map(({ to, icon: Icon, label }) => (
              <NavLink key={to} to={to} onClick={onNavigate} className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
                <span className="nav-icon"><Icon size={18} /></span>
                <span>{label}</span>
                {to === '/cart' && cartCount > 0 && <span className="nav-count">{cartCount}</span>}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      {user && (
        <div className="sidebar-footer">
          <div className="user-card">
            <div className="user-avatar">{user.name?.[0]?.toUpperCase()}</div>
            <div style={{ minWidth: 0 }}>
              <div className="user-name">{user.name}</div>
              <div className="user-role">{user.location || user.role}</div>
            </div>
            <button className="btn-ghost btn logout" onClick={handleLogout} title="Sign out" aria-label="Sign out">
              <LuLogOut size={17} />
            </button>
          </div>
        </div>
      )}
    </aside>
  )
}
