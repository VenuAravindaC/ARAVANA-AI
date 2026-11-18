# CRM Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a web-based CRM dashboard where ARVANA clients can view leads, manage bookings, control bot behavior, and update their availability schedule.

**Architecture:** React SPA with Vite, communicating with existing FastAPI backend via REST API. Uses Supabase for authentication and data queries. Responsive design with Tailwind CSS. Calendar component for booking management. Real-time lead classification display (HOT/WARM/COLD/NEW).

**Tech Stack:** React 18, Vite, Tailwind CSS, React Router, Supabase JS Client, FullCalendar (for calendar view), Recharts (for analytics)

**Spec:** This plan implements the CRM requirements from the conversation:
- View all leads categorized by HOT/WARM/COLD/NEW
- See booking calendar with availability management
- Pause/resume bot for human handoff
- View conversation history per lead
- Update broker availability schedule
- Dashboard analytics (lead counts, conversion rate)

## Global Constraints

- React 18.2.0+
- Vite 5.0.0+
- Node.js 18+
- Tailwind CSS 3.4.0+
- Must work on mobile and desktop (responsive design)
- Authentication via Supabase Auth
- All API calls to existing FastAPI backend at `http://localhost:8000`
- Color scheme: HOT=red, WARM=orange, COLD=blue, NEW=gray
- Must handle loading states and errors gracefully

---

## Task 1: Project Setup & Configuration

**Files:**
- Create: `crm/package.json`
- Create: `crm/vite.config.js`
- Create: `crm/tailwind.config.js`
- Create: `crm/postcss.config.js`
- Create: `crm/index.html`
- Create: `crm/src/main.jsx`
- Create: `crm/src/App.jsx`
- Create: `crm/.env.example`
- Create: `crm/.gitignore`
- Create: `crm/README.md`

**Interfaces:**
- Consumes: Nothing (first task)
- Produces: Working Vite + React + Tailwind project scaffold

---

- [ ] **Step 1: Create project directory and initialize package.json**

```bash
cd E:/BUISNESS/ARVANA
mkdir crm
cd crm
npm init -y
```

- [ ] **Step 2: Install dependencies**

```bash
npm install react@18.2.0 react-dom@18.2.0 react-router-dom@6.20.0
npm install -D vite@5.0.0 @vitejs/plugin-react@4.2.0
npm install -D tailwindcss@3.4.0 postcss@8.4.32 autoprefixer@10.4.16
npm install @supabase/supabase-js@2.39.0
npm install @fullcalendar/react@6.1.10 @fullcalendar/daygrid@6.1.10 @fullcalendar/interaction@6.1.10
npm install recharts@2.10.3
npm install lucide-react@0.294.0
```

- [ ] **Step 3: Create vite.config.js**

```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
})
```

- [ ] **Step 4: Initialize Tailwind CSS**

```bash
npx tailwindcss init -p
```

- [ ] **Step 5: Configure tailwind.config.js**

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'lead-hot': '#EF4444',
        'lead-warm': '#F97316',
        'lead-cold': '#3B82F6',
        'lead-new': '#6B7280'
      }
    },
  },
  plugins: [],
}
```

- [ ] **Step 6: Create index.html**

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>ARVANA CRM Dashboard</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

- [ ] **Step 7: Create src/main.jsx**

```jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

- [ ] **Step 8: Create src/index.css**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
```

- [ ] **Step 9: Create basic src/App.jsx**

```jsx
import React from 'react'

function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto py-6 px-4">
          <h1 className="text-3xl font-bold text-gray-900">
            ARVANA CRM Dashboard
          </h1>
        </div>
      </header>
      <main className="max-w-7xl mx-auto py-6 px-4">
        <p className="text-gray-600">CRM Dashboard Loading...</p>
      </main>
    </div>
  )
}

export default App
```

- [ ] **Step 10: Create .env.example**

```bash
VITE_SUPABASE_URL=your_supabase_project_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
VITE_API_URL=http://localhost:8000
```

- [ ] **Step 11: Create .gitignore**

```
# Dependencies
node_modules/
.pnp
.pnp.js

# Testing
coverage/

# Production
build/
dist/

# Misc
.DS_Store
.env
.env.local
.env.development.local
.env.test.local
.env.production.local

# Logs
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Editor
.vscode/
.idea/
```

- [ ] **Step 12: Create README.md**

```markdown
# ARVANA CRM Dashboard

Multi-tenant CRM dashboard for ARVANA AI lead management system.

## Setup

1. Copy `.env.example` to `.env` and fill in your Supabase credentials
2. Install dependencies: `npm install`
3. Run dev server: `npm run dev`
4. Build for production: `npm run build`

## Features

- Lead management (HOT/WARM/COLD/NEW classification)
- Booking calendar with availability management
- Bot pause/resume for human handoff
- Conversation history viewer
- Real-time analytics dashboard
```

- [ ] **Step 13: Update package.json scripts**

Edit `crm/package.json` to add:

```json
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  }
}
```

- [ ] **Step 14: Test dev server runs**

```bash
cd E:/BUISNESS/ARVANA/crm
npm run dev
```

Expected: Server starts on http://localhost:3000 and shows "ARVANA CRM Dashboard"

- [ ] **Step 15: Commit project setup**

```bash
git add crm/
git commit -m "feat(crm): initialize React + Vite + Tailwind project

- Add Vite config with API proxy to FastAPI backend
- Configure Tailwind with custom lead classification colors
- Add FullCalendar and Recharts dependencies
- Create basic App scaffold

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

## Task 2: API Client & Supabase Integration

**Files:**
- Create: `crm/src/lib/supabase.js`
- Create: `crm/src/lib/api.js`
- Create: `crm/src/hooks/useAuth.js`
- Create: `crm/.env`

**Interfaces:**
- Consumes: Nothing
- Produces:
  - `supabaseClient` (Supabase client instance)
  - `api.getLeads(clientId)` → Promise<Array<Lead>>
  - `api.getBookings(clientId, startDate, endDate)` → Promise<Array<Booking>>
  - `api.pauseBot(conversationId)` → Promise<{status: string}>
  - `api.resumeBot(conversationId)` → Promise<{status: string}>
  - `api.updateAvailability(clientId, date, time, status)` → Promise<{status: string}>
  - `useAuth()` → {user, loading, signIn, signOut}

---

- [ ] **Step 1: Create .env file**

```bash
cd E:/BUISNESS/ARVANA/crm
cp .env.example .env
```

Then manually edit `.env` and add your actual Supabase credentials.

- [ ] **Step 2: Create src/lib/supabase.js**

```javascript
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error('Missing Supabase environment variables')
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
```

- [ ] **Step 3: Create src/lib/api.js**

```javascript
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function fetchAPI(endpoint, options = {}) {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers
    },
    ...options
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Request failed' }))
    throw new Error(error.message || `HTTP ${response.status}`)
  }

  return response.json()
}

export const api = {
  // Get all leads for a client
  getLeads: (clientId) => {
    return fetchAPI(`/leads?client_id=${clientId}`)
  },

  // Get bookings for date range
  getBookings: (clientId, startDate, endDate) => {
    const params = new URLSearchParams({
      client_id: clientId,
      start_date: startDate || '',
      end_date: endDate || ''
    })
    return fetchAPI(`/calendar/bookings?${params}`)
  },

  // Pause bot for conversation (human handoff)
  pauseBot: (conversationId) => {
    return fetchAPI(`/conversation/${conversationId}/pause`, { method: 'POST' })
  },

  // Resume bot for conversation
  resumeBot: (conversationId) => {
    return fetchAPI(`/conversation/${conversationId}/resume`, { method: 'POST' })
  },

  // Update broker availability
  updateAvailability: (clientId, date, time, status) => {
    return fetchAPI('/calendar/availability/update', {
      method: 'POST',
      body: JSON.stringify({ client_id: clientId, date, time, status })
    })
  },

  // Get available slots
  getAvailableSlots: (clientId, date = null, daysAhead = 7) => {
    const params = new URLSearchParams({
      client_id: clientId,
      days_ahead: daysAhead
    })
    if (date) params.append('date', date)
    return fetchAPI(`/calendar/availability?${params}`)
  },

  // Get conversation history
  getConversationHistory: (conversationId) => {
    return fetchAPI(`/conversation/${conversationId}/history`)
  }
}
```

- [ ] **Step 4: Create src/hooks/useAuth.js**

```javascript
import { useState, useEffect } from 'react'
import { supabase } from '../lib/supabase'

export function useAuth() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check active session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null)
      setLoading(false)
    })

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null)
      setLoading(false)
    })

    return () => subscription.unsubscribe()
  }, [])

  const signIn = async (email, password) => {
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password
    })
    if (error) throw error
    return data
  }

  const signUp = async (email, password) => {
    const { data, error } = await supabase.auth.signUp({
      email,
      password
    })
    if (error) throw error
    return data
  }

  const signOut = async () => {
    const { error } = await supabase.auth.signOut()
    if (error) throw error
  }

  return {
    user,
    loading,
    signIn,
    signUp,
    signOut
  }
}
```

- [ ] **Step 5: Test API client in browser console**

Start dev server (`npm run dev`), open browser console, and test:

```javascript
import { api } from './lib/api'
// Should not throw error
console.log('API client loaded')
```

Expected: No errors in console

- [ ] **Step 6: Commit API client**

```bash
git add crm/src/lib/ crm/src/hooks/ crm/.env.example
git commit -m "feat(crm): add API client and Supabase auth integration

- Create fetchAPI wrapper with error handling
- Add all backend API endpoints (leads, bookings, bot control, availability)
- Implement useAuth hook with Supabase Auth
- Add environment variable validation

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

## Task 3: Authentication Pages

**Files:**
- Create: `crm/src/pages/Login.jsx`
- Create: `crm/src/pages/ProtectedRoute.jsx`
- Modify: `crm/src/App.jsx`

**Interfaces:**
- Consumes:
  - `useAuth()` from Task 2
- Produces:
  - `<Login />` component
  - `<ProtectedRoute>` wrapper component
  - Updated App.jsx with routing

---

- [ ] **Step 1: Create src/pages/Login.jsx**

```jsx
import React, { useState } from 'react'
import { useAuth } from '../hooks/useAuth'
import { useNavigate } from 'react-router-dom'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { signIn } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await signIn(email, password)
      navigate('/dashboard')
    } catch (err) {
      setError(err.message || 'Failed to sign in')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            ARVANA CRM
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Sign in to access your dashboard
          </p>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="rounded-md bg-red-50 p-4">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}
          <div className="rounded-md shadow-sm -space-y-px">
            <div>
              <label htmlFor="email" className="sr-only">Email address</label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                placeholder="Email address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div>
              <label htmlFor="password" className="sr-only">Password</label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={loading}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
            >
              {loading ? 'Signing in...' : 'Sign in'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Create src/pages/ProtectedRoute.jsx**

```jsx
import React from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-600">Loading...</div>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return children
}
```

- [ ] **Step 3: Update src/App.jsx with routing**

```jsx
import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import ProtectedRoute from './pages/ProtectedRoute'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <div className="min-h-screen bg-gray-50">
                <header className="bg-white shadow">
                  <div className="max-w-7xl mx-auto py-6 px-4">
                    <h1 className="text-3xl font-bold text-gray-900">
                      Dashboard
                    </h1>
                  </div>
                </header>
                <main className="max-w-7xl mx-auto py-6 px-4">
                  <p className="text-gray-600">Dashboard content coming soon...</p>
                </main>
              </div>
            </ProtectedRoute>
          }
        />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
```

- [ ] **Step 4: Test login flow**

```bash
npm run dev
```

Navigate to http://localhost:3000
Expected: Redirects to /login page, shows sign-in form

- [ ] **Step 5: Commit authentication pages**

```bash
git add crm/src/pages/ crm/src/App.jsx
git commit -m "feat(crm): add authentication pages and protected routes

- Create login page with email/password form
- Add ProtectedRoute wrapper for authenticated pages
- Set up React Router with /login and /dashboard routes
- Add loading states and error handling

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

## Task 4: Dashboard Layout & Navigation

**Files:**
- Create: `crm/src/components/DashboardLayout.jsx`
- Create: `crm/src/components/Sidebar.jsx`
- Create: `crm/src/pages/Dashboard.jsx`
- Create: `crm/src/pages/Leads.jsx`
- Create: `crm/src/pages/Calendar.jsx`
- Create: `crm/src/pages/Conversations.jsx`
- Modify: `crm/src/App.jsx`

**Interfaces:**
- Consumes:
  - `useAuth()` from Task 2
- Produces:
  - `<DashboardLayout>` component with sidebar navigation
  - `<Sidebar>` component with navigation links
  - Empty page components (Dashboard, Leads, Calendar, Conversations)

---

- [ ] **Step 1: Create src/components/Sidebar.jsx**

```jsx
import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, Users, Calendar, MessageSquare, LogOut } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'

export default function Sidebar() {
  const location = useLocation()
  const { signOut } = useAuth()

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Leads', href: '/leads', icon: Users },
    { name: 'Calendar', href: '/calendar', icon: Calendar },
    { name: 'Conversations', href: '/conversations', icon: MessageSquare }
  ]

  const isActive = (href) => location.pathname === href

  return (
    <div className="flex flex-col w-64 bg-gray-800">
      <div className="flex items-center h-16 flex-shrink-0 px-4 bg-gray-900">
        <h1 className="text-white text-xl font-bold">ARVANA CRM</h1>
      </div>
      <div className="flex-1 flex flex-col overflow-y-auto">
        <nav className="flex-1 px-2 py-4 space-y-1">
          {navigation.map((item) => {
            const Icon = item.icon
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`${
                  isActive(item.href)
                    ? 'bg-gray-900 text-white'
                    : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                } group flex items-center px-2 py-2 text-sm font-medium rounded-md`}
              >
                <Icon className="mr-3 h-5 w-5" />
                {item.name}
              </Link>
            )
          })}
        </nav>
        <div className="flex-shrink-0 flex border-t border-gray-700 p-4">
          <button
            onClick={signOut}
            className="flex-shrink-0 w-full group block text-left"
          >
            <div className="flex items-center">
              <LogOut className="inline-block h-5 w-5 text-gray-400 group-hover:text-gray-300 mr-3" />
              <div className="text-sm font-medium text-gray-300 group-hover:text-white">
                Sign out
              </div>
            </div>
          </button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Create src/components/DashboardLayout.jsx**

```jsx
import React from 'react'
import Sidebar from './Sidebar'

export default function DashboardLayout({ children, title }) {
  return (
    <div className="min-h-screen flex bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <header className="bg-white shadow">
          <div className="py-6 px-8">
            <h1 className="text-3xl font-bold text-gray-900">{title}</h1>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto">
          <div className="py-6 px-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Create src/pages/Dashboard.jsx**

```jsx
import React from 'react'
import DashboardLayout from '../components/DashboardLayout'

export default function Dashboard() {
  return (
    <DashboardLayout title="Dashboard">
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="rounded-md bg-lead-hot p-3">
                  <div className="h-6 w-6 text-white">🔥</div>
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">HOT Leads</dt>
                  <dd className="text-lg font-medium text-gray-900">0</dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="rounded-md bg-lead-warm p-3">
                  <div className="h-6 w-6 text-white">🌡️</div>
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">WARM Leads</dt>
                  <dd className="text-lg font-medium text-gray-900">0</dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="rounded-md bg-lead-cold p-3">
                  <div className="h-6 w-6 text-white">❄️</div>
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">COLD Leads</dt>
                  <dd className="text-lg font-medium text-gray-900">0</dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="rounded-md bg-lead-new p-3">
                  <div className="h-6 w-6 text-white">📝</div>
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">NEW Leads</dt>
                  <dd className="text-lg font-medium text-gray-900">0</dd>
                </dl>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-8">
        <p className="text-gray-600">Dashboard analytics coming soon...</p>
      </div>
    </DashboardLayout>
  )
}
```

- [ ] **Step 4: Create src/pages/Leads.jsx**

```jsx
import React from 'react'
import DashboardLayout from '../components/DashboardLayout'

export default function Leads() {
  return (
    <DashboardLayout title="Leads">
      <p className="text-gray-600">Leads table coming soon...</p>
    </DashboardLayout>
  )
}
```

- [ ] **Step 5: Create src/pages/Calendar.jsx**

```jsx
import React from 'react'
import DashboardLayout from '../components/DashboardLayout'

export default function Calendar() {
  return (
    <DashboardLayout title="Calendar">
      <p className="text-gray-600">Calendar view coming soon...</p>
    </DashboardLayout>
  )
}
```

- [ ] **Step 6: Create src/pages/Conversations.jsx**

```jsx
import React from 'react'
import DashboardLayout from '../components/DashboardLayout'

export default function Conversations() {
  return (
    <DashboardLayout title="Conversations">
      <p className="text-gray-600">Conversations list coming soon...</p>
    </DashboardLayout>
  )
}
```

- [ ] **Step 7: Update src/App.jsx with new routes**

```jsx
import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import ProtectedRoute from './pages/ProtectedRoute'
import Dashboard from './pages/Dashboard'
import Leads from './pages/Leads'
import Calendar from './pages/Calendar'
import Conversations from './pages/Conversations'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/leads"
          element={
            <ProtectedRoute>
              <Leads />
            </ProtectedRoute>
          }
        />
        <Route
          path="/calendar"
          element={
            <ProtectedRoute>
              <Calendar />
            </ProtectedRoute>
          }
        />
        <Route
          path="/conversations"
          element={
            <ProtectedRoute>
              <Conversations />
            </ProtectedRoute>
          }
        />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
```

- [ ] **Step 8: Test navigation**

```bash
npm run dev
```

Navigate to http://localhost:3000 and verify:
- Sidebar appears with all navigation links
- Clicking each link navigates to correct page
- Sign out button works

Expected: All routes load, navigation works

- [ ] **Step 9: Commit dashboard layout**

```bash
git add crm/src/components/ crm/src/pages/ crm/src/App.jsx
git commit -m "feat(crm): add dashboard layout with sidebar navigation

- Create reusable DashboardLayout component
- Add sidebar with navigation links (Dashboard, Leads, Calendar, Conversations)
- Create placeholder pages for all sections
- Add stat cards on dashboard for lead counts
- Implement sign out functionality

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

## Task 5: Leads Page with Classification

**Files:**
- Modify: `crm/src/pages/Leads.jsx`
- Create: `crm/src/components/LeadCard.jsx`
- Create: `crm/src/components/LeadFilters.jsx`
- Create: `crm/src/hooks/useLeads.js`

**Interfaces:**
- Consumes:
  - `api.getLeads(clientId)` from Task 2
  - `supabase.auth.getUser()` from Task 2
- Produces:
  - `useLeads(clientId)` → {leads, loading, error, refetch}
  - `<LeadCard lead={...} />` component
  - `<LeadFilters onFilterChange={...} />` component
  - Updated Leads.jsx with full lead management

---

- [ ] **Step 1: Create src/hooks/useLeads.js**

```javascript
import { useState, useEffect } from 'react'
import { api } from '../lib/api'

export function useLeads(clientId) {
  const [leads, setLeads] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchLeads = async () => {
    if (!clientId) return
    
    setLoading(true)
    setError(null)
    
    try {
      const data = await api.getLeads(clientId)
      setLeads(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLeads()
  }, [clientId])

  return {
    leads,
    loading,
    error,
    refetch: fetchLeads
  }
}
```

- [ ] **Step 2: Create src/components/LeadFilters.jsx**

```jsx
import React from 'react'

const CLASSIFICATIONS = ['ALL', 'HOT', 'WARM', 'COLD', 'NEW']

export default function LeadFilters({ selectedClassification, onFilterChange }) {
  const getColor = (classification) => {
    switch (classification) {
      case 'HOT': return 'bg-lead-hot text-white'
      case 'WARM': return 'bg-lead-warm text-white'
      case 'COLD': return 'bg-lead-cold text-white'
      case 'NEW': return 'bg-lead-new text-white'
      default: return 'bg-gray-200 text-gray-700'
    }
  }

  return (
    <div className="flex gap-2 mb-6">
      {CLASSIFICATIONS.map((classification) => (
        <button
          key={classification}
          onClick={() => onFilterChange(classification)}
          className={`px-4 py-2 rounded-md font-medium transition-colors ${
            selectedClassification === classification
              ? getColor(classification)
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          {classification}
        </button>
      ))}
    </div>
  )
}
```

- [ ] **Step 3: Create src/components/LeadCard.jsx**

```jsx
import React from 'react'
import { Phone, Calendar, MessageSquare } from 'lucide-react'

export default function LeadCard({ lead, onViewConversation }) {
  const getClassificationColor = (classification) => {
    switch (classification) {
      case 'HOT': return 'bg-lead-hot'
      case 'WARM': return 'bg-lead-warm'
      case 'COLD': return 'bg-lead-cold'
      case 'NEW': return 'bg-lead-new'
      default: return 'bg-gray-400'
    }
  }

  return (
    <div className="bg-white shadow rounded-lg p-6 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <h3 className="text-lg font-semibold text-gray-900">
              {lead.name || 'Unknown'}
            </h3>
            <span
              className={`px-3 py-1 rounded-full text-xs font-medium text-white ${getClassificationColor(
                lead.classification
              )}`}
            >
              {lead.classification}
            </span>
          </div>
          
          <div className="space-y-2 text-sm text-gray-600">
            <div className="flex items-center gap-2">
              <Phone className="h-4 w-4" />
              <span>{lead.customer_phone}</span>
            </div>
            
            {lead.budget && (
              <div>
                <span className="font-medium">Budget:</span> {lead.budget}
              </div>
            )}
            
            {lead.timeline && (
              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4" />
                <span>{lead.timeline}</span>
              </div>
            )}
            
            {lead.inquiry_type && (
              <div>
                <span className="font-medium">Inquiry:</span> {lead.inquiry_type}
              </div>
            )}
          </div>
          
          {lead.ai_summary && (
            <p className="mt-3 text-sm text-gray-700 line-clamp-2">
              {lead.ai_summary}
            </p>
          )}
        </div>
      </div>
      
      <div className="mt-4 flex gap-2">
        <button
          onClick={() => onViewConversation(lead.conversation_id)}
          className="flex items-center gap-1 px-3 py-1.5 text-sm bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
        >
          <MessageSquare className="h-4 w-4" />
          View Conversation
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Update src/pages/Leads.jsx**

```jsx
import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import DashboardLayout from '../components/DashboardLayout'
import LeadCard from '../components/LeadCard'
import LeadFilters from '../components/LeadFilters'
import { useLeads } from '../hooks/useLeads'

// TODO: Get actual client ID from logged-in user
const TEMP_CLIENT_ID = '00000000-0000-0000-0000-000000000001'

export default function Leads() {
  const [selectedClassification, setSelectedClassification] = useState('ALL')
  const { leads, loading, error } = useLeads(TEMP_CLIENT_ID)
  const navigate = useNavigate()

  const filteredLeads = selectedClassification === 'ALL'
    ? leads
    : leads.filter(lead => lead.classification === selectedClassification)

  const handleViewConversation = (conversationId) => {
    navigate(`/conversations/${conversationId}`)
  }

  if (loading) {
    return (
      <DashboardLayout title="Leads">
        <div className="flex items-center justify-center h-64">
          <p className="text-gray-600">Loading leads...</p>
        </div>
      </DashboardLayout>
    )
  }

  if (error) {
    return (
      <DashboardLayout title="Leads">
        <div className="bg-red-50 p-4 rounded-md">
          <p className="text-red-800">Error loading leads: {error}</p>
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout title="Leads">
      <LeadFilters
        selectedClassification={selectedClassification}
        onFilterChange={setSelectedClassification}
      />

      {filteredLeads.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-500">
            {selectedClassification === 'ALL'
              ? 'No leads yet'
              : `No ${selectedClassification} leads`}
          </p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-1 lg:grid-cols-2">
          {filteredLeads.map((lead) => (
            <LeadCard
              key={lead.id}
              lead={lead}
              onViewConversation={handleViewConversation}
            />
          ))}
        </div>
      )}
    </DashboardLayout>
  )
}
```

- [ ] **Step 5: Test leads page**

```bash
npm run dev
```

Navigate to /leads and verify:
- Filter buttons appear (ALL, HOT, WARM, COLD, NEW)
- Leads load from API (or show "No leads yet")
- Clicking filters works
- Lead cards show all information

Expected: Leads page functional with filtering

- [ ] **Step 6: Commit leads page**

```bash
git add crm/src/pages/Leads.jsx crm/src/components/LeadCard.jsx crm/src/components/LeadFilters.jsx crm/src/hooks/useLeads.js
git commit -m "feat(crm): implement leads page with classification filters

- Create useLeads hook to fetch leads from API
- Add LeadFilters component with HOT/WARM/COLD/NEW buttons
- Build LeadCard component showing lead details
- Implement lead filtering by classification
- Add navigation to conversation view

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

## Task 6: Calendar & Booking Management

**Files:**
- Modify: `crm/src/pages/Calendar.jsx`
- Create: `crm/src/hooks/useBookings.js`
- Create: `crm/src/components/AvailabilityEditor.jsx`

**Interfaces:**
- Consumes:
  - `api.getBookings(clientId, startDate, endDate)` from Task 2
  - `api.updateAvailability(clientId, date, time, status)` from Task 2
- Produces:
  - `useBookings(clientId)` → {bookings, loading, error, refetch}
  - `<AvailabilityEditor />` component for schedule management
  - Updated Calendar.jsx with FullCalendar integration

---

- [ ] **Step 1: Create src/hooks/useBookings.js**

```javascript
import { useState, useEffect } from 'react'
import { api } from '../lib/api'

export function useBookings(clientId, startDate = null, endDate = null) {
  const [bookings, setBookings] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchBookings = async () => {
    if (!clientId) return
    
    setLoading(true)
    setError(null)
    
    try {
      const data = await api.getBookings(clientId, startDate, endDate)
      setBookings(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchBookings()
  }, [clientId, startDate, endDate])

  return {
    bookings,
    loading,
    error,
    refetch: fetchBookings
  }
}
```

- [ ] **Step 2: Create src/components/AvailabilityEditor.jsx**

```jsx
import React, { useState } from 'react'
import { api } from '../lib/api'

const TIME_SLOTS = [
  '10:00 AM', '11:00 AM', '12:00 PM',
  '02:00 PM', '03:00 PM', '04:00 PM', '05:00 PM', '06:00 PM'
]

export default function AvailabilityEditor({ clientId, selectedDate, onUpdate }) {
  const [updating, setUpdating] = useState(false)
  const [error, setError] = useState(null)

  const handleToggleSlot = async (time) => {
    setUpdating(true)
    setError(null)

    try {
      // Toggle between AVAILABLE and BLOCKED
      await api.updateAvailability(clientId, selectedDate, time, 'BLOCKED')
      onUpdate()
    } catch (err) {
      setError(err.message)
    } finally {
      setUpdating(false)
    }
  }

  return (
    <div className="bg-white shadow rounded-lg p-6">
      <h3 className="text-lg font-semibold mb-4">
        Manage Availability for {selectedDate}
      </h3>

      {error && (
        <div className="mb-4 bg-red-50 p-3 rounded text-red-800 text-sm">
          {error}
        </div>
      )}

      <div className="grid grid-cols-2 gap-2">
        {TIME_SLOTS.map((time) => (
          <button
            key={time}
            onClick={() => handleToggleSlot(time)}
            disabled={updating}
            className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50"
          >
            {time}
          </button>
        ))}
      </div>

      <p className="mt-4 text-sm text-gray-600">
        Click a time slot to block/unblock it
      </p>
    </div>
  )
}
```

- [ ] **Step 3: Update src/pages/Calendar.jsx**

```jsx
import React, { useState } from 'react'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import interactionPlugin from '@fullcalendar/interaction'
import DashboardLayout from '../components/DashboardLayout'
import AvailabilityEditor from '../components/AvailabilityEditor'
import { useBookings } from '../hooks/useBookings'

// TODO: Get actual client ID from logged-in user
const TEMP_CLIENT_ID = '00000000-0000-0000-0000-000000000001'

export default function Calendar() {
  const [selectedDate, setSelectedDate] = useState(null)
  const { bookings, loading, refetch } = useBookings(TEMP_CLIENT_ID)

  // Convert bookings to FullCalendar events
  const events = bookings.map((booking) => ({
    id: booking.id,
    title: `${booking.customer_name || 'Booking'} - ${booking.time}`,
    date: booking.date,
    color: booking.status === 'CONFIRMED' ? '#3B82F6' : '#6B7280'
  }))

  const handleDateClick = (info) => {
    setSelectedDate(info.dateStr)
  }

  if (loading) {
    return (
      <DashboardLayout title="Calendar">
        <div className="flex items-center justify-center h-64">
          <p className="text-gray-600">Loading calendar...</p>
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout title="Calendar">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <div className="bg-white shadow rounded-lg p-6">
            <FullCalendar
              plugins={[dayGridPlugin, interactionPlugin]}
              initialView="dayGridMonth"
              events={events}
              dateClick={handleDateClick}
              headerToolbar={{
                left: 'prev,next today',
                center: 'title',
                right: 'dayGridMonth'
              }}
              height="auto"
            />
          </div>
        </div>

        <div>
          {selectedDate ? (
            <AvailabilityEditor
              clientId={TEMP_CLIENT_ID}
              selectedDate={selectedDate}
              onUpdate={refetch}
            />
          ) : (
            <div className="bg-white shadow rounded-lg p-6">
              <p className="text-gray-600">
                Click a date on the calendar to manage your availability
              </p>
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  )
}
```

- [ ] **Step 4: Test calendar page**

```bash
npm run dev
```

Navigate to /calendar and verify:
- Calendar displays current month
- Bookings appear as events (if any exist)
- Clicking a date shows availability editor
- Time slot buttons work

Expected: Calendar functional with booking display

- [ ] **Step 5: Commit calendar page**

```bash
git add crm/src/pages/Calendar.jsx crm/src/components/AvailabilityEditor.jsx crm/src/hooks/useBookings.js
git commit -m "feat(crm): implement calendar with booking and availability management

- Add FullCalendar integration with month view
- Create useBookings hook to fetch bookings from API
- Build AvailabilityEditor for managing broker schedule
- Display bookings as calendar events
- Add date-click handler to select availability editing

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

## Task 7: Conversation Viewer with Bot Control

**Files:**
- Modify: `crm/src/pages/Conversations.jsx`
- Create: `crm/src/components/ConversationList.jsx`
- Create: `crm/src/components/ConversationViewer.jsx`
- Create: `crm/src/components/BotControl.jsx`
- Create: `crm/src/hooks/useConversations.js`

**Interfaces:**
- Consumes:
  - `api.getConversationHistory(conversationId)` from Task 2
  - `api.pauseBot(conversationId)` from Task 2
  - `api.resumeBot(conversationId)` from Task 2
  - `supabase.from('conversations').select()` from Task 2
- Produces:
  - `useConversations(clientId)` → {conversations, loading, error}
  - `<ConversationList />` component
  - `<ConversationViewer />` component
  - `<BotControl />` component for pause/resume

---

- [ ] **Step 1: Create src/hooks/useConversations.js**

```javascript
import { useState, useEffect } from 'react'
import { supabase } from '../lib/supabase'

export function useConversations(clientId) {
  const [conversations, setConversations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!clientId) return

    const fetchConversations = async () => {
      setLoading(true)
      setError(null)

      try {
        const { data, error: supabaseError } = await supabase
          .from('conversations')
          .select('*')
          .eq('client_id', clientId)
          .order('updated_at', { ascending: false })

        if (supabaseError) throw supabaseError
        setConversations(data || [])
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchConversations()
  }, [clientId])

  return { conversations, loading, error }
}
```

- [ ] **Step 2: Create src/components/BotControl.jsx**

```jsx
import React, { useState } from 'react'
import { Pause, Play } from 'lucide-react'
import { api } from '../lib/api'

export default function BotControl({ conversationId, botActive, onUpdate }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleToggle = async () => {
    setLoading(true)
    setError(null)

    try {
      if (botActive) {
        await api.pauseBot(conversationId)
      } else {
        await api.resumeBot(conversationId)
      }
      onUpdate()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-white border rounded-lg p-4">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="font-medium text-gray-900">Bot Status</h4>
          <p className="text-sm text-gray-600 mt-1">
            {botActive ? 'Bot is responding' : 'Human handling conversation'}
          </p>
        </div>
        <button
          onClick={handleToggle}
          disabled={loading}
          className={`flex items-center gap-2 px-4 py-2 rounded-md font-medium disabled:opacity-50 ${
            botActive
              ? 'bg-red-100 text-red-700 hover:bg-red-200'
              : 'bg-green-100 text-green-700 hover:bg-green-200'
          }`}
        >
          {botActive ? (
            <>
              <Pause className="h-4 w-4" />
              Pause Bot
            </>
          ) : (
            <>
              <Play className="h-4 w-4" />
              Resume Bot
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="mt-3 text-sm text-red-600">
          Error: {error}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Create src/components/ConversationList.jsx**

```jsx
import React from 'react'
import { MessageSquare } from 'lucide-react'

export default function ConversationList({ conversations, selectedId, onSelect }) {
  if (conversations.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No conversations yet
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {conversations.map((conv) => (
        <button
          key={conv.id}
          onClick={() => onSelect(conv.id)}
          className={`w-full text-left p-4 rounded-lg border transition-colors ${
            selectedId === conv.id
              ? 'bg-blue-50 border-blue-300'
              : 'bg-white border-gray-200 hover:bg-gray-50'
          }`}
        >
          <div className="flex items-start gap-3">
            <MessageSquare className="h-5 w-5 text-gray-400 mt-0.5" />
            <div className="flex-1 min-w-0">
              <p className="font-medium text-gray-900 truncate">
                {conv.customer_phone}
              </p>
              <p className="text-sm text-gray-600">
                {conv.bot_active ? '🤖 Bot active' : '👤 Human handling'}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                {new Date(conv.updated_at).toLocaleDateString()}
              </p>
            </div>
          </div>
        </button>
      ))}
    </div>
  )
}
```

- [ ] **Step 4: Create src/components/ConversationViewer.jsx**

```jsx
import React, { useState, useEffect } from 'react'
import { api } from '../lib/api'

export default function ConversationViewer({ conversationId }) {
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!conversationId) return

    const fetchMessages = async () => {
      setLoading(true)
      setError(null)

      try {
        const data = await api.getConversationHistory(conversationId)
        setMessages(data)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchMessages()
  }, [conversationId])

  if (loading) {
    return <div className="text-gray-600">Loading messages...</div>
  }

  if (error) {
    return <div className="text-red-600">Error: {error}</div>
  }

  if (messages.length === 0) {
    return <div className="text-gray-500">No messages yet</div>
  }

  return (
    <div className="space-y-4">
      {messages.map((msg, index) => (
        <div
          key={index}
          className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
        >
          <div
            className={`max-w-[70%] rounded-lg px-4 py-2 ${
              msg.role === 'user'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 text-gray-900'
            }`}
          >
            <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
            <p className="text-xs mt-1 opacity-70">
              {new Date(msg.timestamp).toLocaleTimeString()}
            </p>
          </div>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 5: Update src/pages/Conversations.jsx**

```jsx
import React, { useState } from 'react'
import DashboardLayout from '../components/DashboardLayout'
import ConversationList from '../components/ConversationList'
import ConversationViewer from '../components/ConversationViewer'
import BotControl from '../components/BotControl'
import { useConversations } from '../hooks/useConversations'

// TODO: Get actual client ID from logged-in user
const TEMP_CLIENT_ID = '00000000-0000-0000-0000-000000000001'

export default function Conversations() {
  const [selectedConvId, setSelectedConvId] = useState(null)
  const { conversations, loading, error } = useConversations(TEMP_CLIENT_ID)

  const selectedConv = conversations.find(c => c.id === selectedConvId)

  if (loading) {
    return (
      <DashboardLayout title="Conversations">
        <div className="flex items-center justify-center h-64">
          <p className="text-gray-600">Loading conversations...</p>
        </div>
      </DashboardLayout>
    )
  }

  if (error) {
    return (
      <DashboardLayout title="Conversations">
        <div className="bg-red-50 p-4 rounded-md">
          <p className="text-red-800">Error: {error}</p>
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout title="Conversations">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <div className="bg-white shadow rounded-lg p-4">
            <h3 className="font-semibold mb-4">All Conversations</h3>
            <ConversationList
              conversations={conversations}
              selectedId={selectedConvId}
              onSelect={setSelectedConvId}
            />
          </div>
        </div>

        <div className="lg:col-span-2">
          {selectedConvId ? (
            <div className="space-y-4">
              {selectedConv && (
                <BotControl
                  conversationId={selectedConvId}
                  botActive={selectedConv.bot_active}
                  onUpdate={() => window.location.reload()}
                />
              )}
              <div className="bg-white shadow rounded-lg p-6">
                <ConversationViewer conversationId={selectedConvId} />
              </div>
            </div>
          ) : (
            <div className="bg-white shadow rounded-lg p-6">
              <p className="text-gray-600">
                Select a conversation to view messages
              </p>
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  )
}
```

- [ ] **Step 6: Test conversations page**

```bash
npm run dev
```

Navigate to /conversations and verify:
- Conversation list appears on left
- Selecting a conversation shows messages
- Bot control (pause/resume) works
- Messages display correctly

Expected: Conversations page fully functional

- [ ] **Step 7: Commit conversations page**

```bash
git add crm/src/pages/Conversations.jsx crm/src/components/ConversationList.jsx crm/src/components/ConversationViewer.jsx crm/src/components/BotControl.jsx crm/src/hooks/useConversations.js
git commit -m "feat(crm): implement conversation viewer with bot control

- Create useConversations hook to fetch conversations from Supabase
- Add ConversationList component showing all conversations
- Build ConversationViewer to display message history
- Add BotControl component for pause/resume functionality
- Implement human handoff feature (Feature 3)

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

## Task 8: Dashboard Analytics with Real Data

**Files:**
- Modify: `crm/src/pages/Dashboard.jsx`
- Create: `crm/src/hooks/useDashboardStats.js`
- Create: `crm/src/components/StatsCard.jsx`
- Create: `crm/src/components/LeadChart.jsx`

**Interfaces:**
- Consumes:
  - `useLeads(clientId)` from Task 5
  - `useBookings(clientId)` from Task 6
- Produces:
  - `useDashboardStats(clientId)` → {stats, loading}
  - `<StatsCard />` component
  - `<LeadChart />` component with Recharts
  - Updated Dashboard.jsx with real data

---

- [ ] **Step 1: Create src/hooks/useDashboardStats.js**

```javascript
import { useState, useEffect } from 'react'
import { useLeads } from './useLeads'
import { useBookings } from './useBookings'

export function useDashboardStats(clientId) {
  const { leads, loading: leadsLoading } = useLeads(clientId)
  const { bookings, loading: bookingsLoading } = useBookings(clientId)
  const [stats, setStats] = useState(null)

  useEffect(() => {
    if (!leadsLoading && !bookingsLoading) {
      const hotLeads = leads.filter(l => l.classification === 'HOT').length
      const warmLeads = leads.filter(l => l.classification === 'WARM').length
      const coldLeads = leads.filter(l => l.classification === 'COLD').length
      const newLeads = leads.filter(l => l.classification === 'NEW').length
      
      const upcomingBookings = bookings.filter(
        b => b.status === 'CONFIRMED' && new Date(b.date) >= new Date()
      ).length

      setStats({
        hotLeads,
        warmLeads,
        coldLeads,
        newLeads,
        totalLeads: leads.length,
        upcomingBookings,
        conversionRate: leads.length > 0 ? ((hotLeads / leads.length) * 100).toFixed(1) : 0
      })
    }
  }, [leads, bookings, leadsLoading, bookingsLoading])

  return {
    stats,
    loading: leadsLoading || bookingsLoading
  }
}
```

- [ ] **Step 2: Create src/components/StatsCard.jsx**

```jsx
import React from 'react'

export default function StatsCard({ title, value, icon, color }) {
  return (
    <div className="bg-white overflow-hidden shadow rounded-lg">
      <div className="p-5">
        <div className="flex items-center">
          <div className="flex-shrink-0">
            <div className={`rounded-md ${color} p-3`}>
              <div className="h-6 w-6 text-white text-center">{icon}</div>
            </div>
          </div>
          <div className="ml-5 w-0 flex-1">
            <dl>
              <dt className="text-sm font-medium text-gray-500 truncate">
                {title}
              </dt>
              <dd className="text-2xl font-semibold text-gray-900">{value}</dd>
            </dl>
          </div>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Create src/components/LeadChart.jsx**

```jsx
import React from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

export default function LeadChart({ stats }) {
  if (!stats) return null

  const data = [
    { name: 'HOT', value: stats.hotLeads, fill: '#EF4444' },
    { name: 'WARM', value: stats.warmLeads, fill: '#F97316' },
    { name: 'COLD', value: stats.coldLeads, fill: '#3B82F6' },
    { name: 'NEW', value: stats.newLeads, fill: '#6B7280' }
  ]

  return (
    <div className="bg-white shadow rounded-lg p-6">
      <h3 className="text-lg font-semibold mb-4">Lead Distribution</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="name" />
          <YAxis />
          <Tooltip />
          <Bar dataKey="value" fill="#8884d8" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
```

- [ ] **Step 4: Update src/pages/Dashboard.jsx**

```jsx
import React from 'react'
import DashboardLayout from '../components/DashboardLayout'
import StatsCard from '../components/StatsCard'
import LeadChart from '../components/LeadChart'
import { useDashboardStats } from '../hooks/useDashboardStats'

// TODO: Get actual client ID from logged-in user
const TEMP_CLIENT_ID = '00000000-0000-0000-0000-000000000001'

export default function Dashboard() {
  const { stats, loading } = useDashboardStats(TEMP_CLIENT_ID)

  if (loading) {
    return (
      <DashboardLayout title="Dashboard">
        <div className="flex items-center justify-center h-64">
          <p className="text-gray-600">Loading dashboard...</p>
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout title="Dashboard">
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          title="HOT Leads"
          value={stats?.hotLeads || 0}
          icon="🔥"
          color="bg-lead-hot"
        />
        <StatsCard
          title="WARM Leads"
          value={stats?.warmLeads || 0}
          icon="🌡️"
          color="bg-lead-warm"
        />
        <StatsCard
          title="COLD Leads"
          value={stats?.coldLeads || 0}
          icon="❄️"
          color="bg-lead-cold"
        />
        <StatsCard
          title="NEW Leads"
          value={stats?.newLeads || 0}
          icon="📝"
          color="bg-lead-new"
        />
      </div>

      <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <LeadChart stats={stats} />
        
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4">Quick Stats</h3>
          <dl className="space-y-4">
            <div className="flex justify-between">
              <dt className="text-gray-600">Total Leads</dt>
              <dd className="font-semibold">{stats?.totalLeads || 0}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-600">Upcoming Bookings</dt>
              <dd className="font-semibold">{stats?.upcomingBookings || 0}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-600">Conversion Rate</dt>
              <dd className="font-semibold">{stats?.conversionRate || 0}%</dd>
            </div>
          </dl>
        </div>
      </div>
    </DashboardLayout>
  )
}
```

- [ ] **Step 5: Test dashboard with real data**

```bash
npm run dev
```

Navigate to /dashboard and verify:
- All stat cards show correct counts
- Bar chart displays lead distribution
- Quick stats section shows calculations
- Data updates when leads change

Expected: Dashboard showing real-time stats

- [ ] **Step 6: Commit dashboard analytics**

```bash
git add crm/src/pages/Dashboard.jsx crm/src/components/StatsCard.jsx crm/src/components/LeadChart.jsx crm/src/hooks/useDashboardStats.js
git commit -m "feat(crm): add dashboard analytics with real-time stats

- Create useDashboardStats hook aggregating leads and bookings
- Build StatsCard component for metric display
- Add LeadChart with Recharts bar chart visualization
- Calculate conversion rate and upcoming bookings
- Display real-time lead counts by classification

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

## Task 9: User Context & Client ID Management

**Files:**
- Create: `crm/src/contexts/UserContext.jsx`
- Modify: `crm/src/App.jsx`
- Modify: `crm/src/pages/Dashboard.jsx`
- Modify: `crm/src/pages/Leads.jsx`
- Modify: `crm/src/pages/Calendar.jsx`
- Modify: `crm/src/pages/Conversations.jsx`

**Interfaces:**
- Consumes:
  - `useAuth()` from Task 2
  - `supabase.from('clients').select()` from Task 2
- Produces:
  - `<UserProvider>` context provider
  - `useUser()` → {user, client, loading}
  - Remove all `TEMP_CLIENT_ID` hardcoded values

---

- [ ] **Step 1: Create src/contexts/UserContext.jsx**

```jsx
import React, { createContext, useContext, useState, useEffect } from 'react'
import { useAuth } from '../hooks/useAuth'
import { supabase } from '../lib/supabase'

const UserContext = createContext(null)

export function UserProvider({ children }) {
  const { user, loading: authLoading } = useAuth()
  const [client, setClient] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!authLoading) {
      if (user) {
        fetchClient()
      } else {
        setClient(null)
        setLoading(false)
      }
    }
  }, [user, authLoading])

  const fetchClient = async () => {
    try {
      // Get client record linked to this user's email
      const { data, error } = await supabase
        .from('clients')
        .select('*')
        .eq('owner_email', user.email)
        .single()

      if (error) throw error
      setClient(data)
    } catch (err) {
      console.error('Error fetching client:', err)
      setClient(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <UserContext.Provider value={{ user, client, loading }}>
      {children}
    </UserContext.Provider>
  )
}

export function useUser() {
  const context = useContext(UserContext)
  if (!context) {
    throw new Error('useUser must be used within UserProvider')
  }
  return context
}
```

- [ ] **Step 2: Update src/App.jsx to wrap with UserProvider**

```jsx
import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { UserProvider } from './contexts/UserContext'
import Login from './pages/Login'
import ProtectedRoute from './pages/ProtectedRoute'
import Dashboard from './pages/Dashboard'
import Leads from './pages/Leads'
import Calendar from './pages/Calendar'
import Conversations from './pages/Conversations'

function App() {
  return (
    <BrowserRouter>
      <UserProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/leads"
            element={
              <ProtectedRoute>
                <Leads />
              </ProtectedRoute>
            }
          />
          <Route
            path="/calendar"
            element={
              <ProtectedRoute>
                <Calendar />
              </ProtectedRoute>
            }
          />
          <Route
            path="/conversations"
            element={
              <ProtectedRoute>
                <Conversations />
              </ProtectedRoute>
            }
          />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </UserProvider>
    </BrowserRouter>
  )
}

export default App
```

- [ ] **Step 3: Update src/pages/Dashboard.jsx to use context**

Replace the line:
```javascript
const TEMP_CLIENT_ID = '00000000-0000-0000-0000-000000000001'
```

With:
```javascript
import { useUser } from '../contexts/UserContext'
// ... inside component
const { client } = useUser()
const clientId = client?.id
```

And pass `clientId` to `useDashboardStats(clientId)`

- [ ] **Step 4: Update src/pages/Leads.jsx to use context**

Replace the line:
```javascript
const TEMP_CLIENT_ID = '00000000-0000-0000-0000-000000000001'
```

With:
```javascript
import { useUser } from '../contexts/UserContext'
// ... inside component
const { client } = useUser()
const clientId = client?.id
```

And pass `clientId` to `useLeads(clientId)`

- [ ] **Step 5: Update src/pages/Calendar.jsx to use context**

Replace the line:
```javascript
const TEMP_CLIENT_ID = '00000000-0000-0000-0000-000000000001'
```

With:
```javascript
import { useUser } from '../contexts/UserContext'
// ... inside component
const { client } = useUser()
const clientId = client?.id
```

And pass `clientId` to `useBookings(clientId)` and `AvailabilityEditor`

- [ ] **Step 6: Update src/pages/Conversations.jsx to use context**

Replace the line:
```javascript
const TEMP_CLIENT_ID = '00000000-0000-0000-0000-000000000001'
```

With:
```javascript
import { useUser } from '../contexts/UserContext'
// ... inside component
const { client } = useUser()
const clientId = client?.id
```

And pass `clientId` to `useConversations(clientId)`

- [ ] **Step 7: Add owner_email column to clients table**

Create a SQL file `crm/add_owner_email.sql`:

```sql
-- Add owner_email to clients table for user-client mapping
ALTER TABLE clients
ADD COLUMN IF NOT EXISTS owner_email TEXT;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_clients_owner_email ON clients(owner_email);

-- Update test client with an email for testing
UPDATE clients
SET owner_email = 'test@example.com'
WHERE id = '00000000-0000-0000-0000-000000000001';
```

Run this in Supabase SQL Editor.

- [ ] **Step 8: Test user context**

```bash
npm run dev
```

Verify:
- App loads without errors
- After login, user context provides client data
- All pages use real client ID instead of hardcoded value

Expected: No more hardcoded client IDs, context working

- [ ] **Step 9: Commit user context**

```bash
git add crm/src/contexts/ crm/src/App.jsx crm/src/pages/ crm/add_owner_email.sql
git commit -m "feat(crm): add user context for client ID management

- Create UserContext to provide authenticated user and client data
- Remove all hardcoded TEMP_CLIENT_ID constants
- Add owner_email column to clients table for user-client mapping
- Update all pages to use client ID from context
- Add SQL migration for owner_email field

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

## Task 10: Production Build & Deployment Prep

**Files:**
- Create: `crm/.env.production`
- Create: `crm/vercel.json` (or deployment config)
- Modify: `crm/README.md`
- Create: `crm/DEPLOYMENT.md`

**Interfaces:**
- Consumes: Nothing
- Produces: Production-ready build configuration and deployment guide

---

- [ ] **Step 1: Create .env.production template**

```bash
# Production environment variables
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your_production_anon_key
VITE_API_URL=https://your-backend.onrender.com
```

- [ ] **Step 2: Create vercel.json for Vercel deployment**

```json
{
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://your-backend.onrender.com/:path*"
    },
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```

- [ ] **Step 3: Create DEPLOYMENT.md**

```markdown
# CRM Dashboard Deployment Guide

## Prerequisites

1. Supabase project set up with all tables
2. Backend deployed to Render (or other host)
3. Vercel account (or other static hosting)

## Environment Variables

Copy `.env.production` and fill in:

- `VITE_SUPABASE_URL`: Your Supabase project URL
- `VITE_SUPABASE_ANON_KEY`: Your Supabase anon/public key
- `VITE_API_URL`: Your deployed backend URL

## Build & Deploy

### Option 1: Vercel (Recommended)

1. Install Vercel CLI: `npm i -g vercel`
2. Login: `vercel login`
3. Deploy: `vercel --prod`

### Option 2: Manual Build + Any Host

1. Build: `npm run build`
2. Upload `dist/` folder to your host
3. Configure server to serve `index.html` for all routes (SPA mode)

## Post-Deployment Checklist

- [ ] Test login with real Supabase credentials
- [ ] Verify all API calls reach backend
- [ ] Check CORS settings on backend
- [ ] Test all pages (Dashboard, Leads, Calendar, Conversations)
- [ ] Verify mobile responsiveness
- [ ] Test bot pause/resume functionality
- [ ] Confirm bookings appear on calendar

## Troubleshooting

**API calls fail:** Check VITE_API_URL and backend CORS settings

**Authentication broken:** Verify Supabase keys and redirect URLs

**404 on refresh:** Ensure server rewrites all routes to index.html
```

- [ ] **Step 4: Update README.md with production info**

Add to existing README:

```markdown
## Production Deployment

See [DEPLOYMENT.md](./DEPLOYMENT.md) for complete deployment guide.

Quick deploy to Vercel:
```bash
npm run build
vercel --prod
```

## Environment Variables

Required for production:
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`
- `VITE_API_URL`

See `.env.example` for format.
```

- [ ] **Step 5: Test production build locally**

```bash
npm run build
npm run preview
```

Navigate to preview URL and verify app works

Expected: Production build runs without errors

- [ ] **Step 6: Commit deployment config**

```bash
git add crm/.env.production crm/vercel.json crm/DEPLOYMENT.md crm/README.md
git commit -m "feat(crm): add production build and deployment configuration

- Create .env.production template
- Add vercel.json for Vercel deployment
- Write comprehensive DEPLOYMENT.md guide
- Update README with production instructions
- Test production build process

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

## Final Verification

Before considering the CRM dashboard complete, verify:

1. **All pages load without errors**
   - Dashboard shows stats
   - Leads page displays and filters leads
   - Calendar shows bookings
   - Conversations display messages

2. **All features functional**
   - Authentication (login/logout)
   - Lead classification filtering
   - Bot pause/resume
   - Availability management
   - Booking display

3. **Responsive design works**
   - Test on mobile viewport
   - Test on tablet viewport
   - Test on desktop

4. **API integration correct**
   - All endpoints return data
   - Error handling works
   - Loading states display

5. **Production build succeeds**
   - `npm run build` completes
   - Preview build works
   - No console errors

---

**Plan Complete!**

This plan will produce a fully functional CRM dashboard integrated with your existing FastAPI backend and Supabase database.
