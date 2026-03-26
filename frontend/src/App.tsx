import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import Dashboard from './pages/Dashboard'
import NewCall from './pages/NewCall'
import CallDetail from './pages/CallDetail'
import CallHistory from './pages/CallHistory'
import Agents from './pages/Agents'
import Evals from './pages/Evals'
import ApiDocs from './pages/ApiDocs'
import Settings from './pages/Settings'

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/calls/new" element={<NewCall />} />
          <Route path="/calls/:id" element={<CallDetail />} />
          <Route path="/calls" element={<CallHistory />} />
          <Route path="/agents" element={<Agents />} />
          <Route path="/evals" element={<Evals />} />
          <Route path="/api-docs" element={<ApiDocs />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}
