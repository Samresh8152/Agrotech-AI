import { useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { LuMenu } from 'react-icons/lu'
import { AuthProvider } from './contexts/AuthContext'
import { CartProvider } from './contexts/CartContext'
import ProtectedRoute from './components/ProtectedRoute'
import Sidebar, { BrandMark } from './components/Sidebar'
import { FEATURES } from './config'

// Pages
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import DiseasePrediction from './pages/DiseasePrediction'
import SoilPrediction from './pages/SoilPrediction'
import WeatherForecast from './pages/WeatherForecast'
import CropRecommendation from './pages/CropRecommendation'
import YieldPrediction from './pages/YieldPrediction'
import FertilizerRecommendation from './pages/FertilizerRecommendation'
import Marketplace from './pages/Marketplace'
import Cart from './pages/Cart'
import Orders from './pages/Orders'
import SellerDashboard from './pages/SellerDashboard'
import Assistant from './pages/Assistant'

function AppLayout() {
  const [menuOpen, setMenuOpen] = useState(false)
  return (
    <div className="app-layout">
      <Sidebar open={menuOpen} onNavigate={() => setMenuOpen(false)} />
      {menuOpen && <div className="sidebar-scrim" onClick={() => setMenuOpen(false)} />}
      <div className="main-content">
        <div className="mobile-bar">
          <button className="btn btn-ghost" onClick={() => setMenuOpen(true)} aria-label="Open menu"><LuMenu size={20} /></button>
          <BrandMark size={16} />
        </div>
        <Outlet />
      </div>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <CartProvider>
          <Toaster
            position="top-right"
            toastOptions={{
              style: {
                background: '#ffffff',
                color: '#1c2a20',
                border: '1px solid #e3dfd2',
                borderRadius: '8px',
                fontSize: '0.9rem',
                boxShadow: '0 4px 16px rgba(28,42,32,0.08)',
              },
              success: { iconTheme: { primary: '#2e6b3f', secondary: '#fff' } },
              error: { iconTheme: { primary: '#b3261e', secondary: '#fff' } },
            }}
          />
          <Routes>
            {/* Public routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/" element={<Navigate to="/dashboard" replace />} />

            {/* Protected routes with sidebar layout */}
            <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/assistant" element={<Assistant />} />
              <Route path="/disease-prediction" element={<DiseasePrediction />} />
              <Route path="/soil-prediction" element={<SoilPrediction />} />
              <Route path="/weather" element={<WeatherForecast />} />
              <Route path="/crop-recommendation" element={<CropRecommendation />} />
              <Route path="/yield-prediction" element={<YieldPrediction />} />
              <Route path="/fertilizer" element={<FertilizerRecommendation />} />
              {FEATURES.marketplace && <>
                <Route path="/marketplace" element={<Marketplace />} />
                <Route path="/cart" element={<Cart />} />
                <Route path="/orders" element={<Orders />} />
                <Route path="/seller" element={<SellerDashboard />} />
              </>}
            </Route>

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </CartProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}
