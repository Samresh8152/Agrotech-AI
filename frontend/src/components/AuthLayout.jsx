import { LuCheck } from 'react-icons/lu'
import { BrandMark } from './Sidebar'

// Two-column frame for the login / register screens: brand panel on the left, form on the right.
export default function AuthLayout({ children }) {
  return (
    <div className="auth-page">
      <aside className="auth-aside">
        <BrandMark />
        <div>
          <h2>Advice for your field, not just any field.</h2>
          <p>Photograph a sick leaf, ask about your crop in your own words, and plan what to sow — with an assistant that remembers your farm.</p>
          <ul className="auth-points">
            <li><LuCheck size={16} /> Disease check for any plant, with a second opinion from our own trained model</li>
            <li><LuCheck size={16} /> Answers in English, Hindi or Hinglish</li>
            <li><LuCheck size={16} /> Local weather and alerts for the crops you have sown</li>
          </ul>
        </div>
        <small style={{ color: '#a9c0a5', position: 'relative', zIndex: 1 }}>Department of Information Technology, VESIT</small>
      </aside>
      <main className="auth-main">
        <div className="auth-card fade-in">{children}</div>
      </main>
    </div>
  )
}
