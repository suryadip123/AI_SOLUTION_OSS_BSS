import { Routes, Route } from 'react-router-dom'
import Sidebar from './components/layout/Sidebar'
import Navbar  from './components/layout/Navbar'
import Dashboard          from './pages/Dashboard'
import NetworkAgent       from './pages/NetworkAgent'
import CustomerAgent      from './pages/CustomerAgent'
import ServiceFulfillment from './pages/ServiceFulfillment'
import ServiceAssurance   from './pages/ServiceAssurance'
import BillingAgent       from './pages/BillingAgent'
import CallAgent          from './pages/CallAgent'
import SocialMediaAgent   from './pages/SocialMediaAgent'

export default function App() {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <Navbar />
        <main className="flex-1 overflow-y-auto p-6">
          <Routes>
            <Route path="/"                    element={<Dashboard />} />
            <Route path="/network"             element={<NetworkAgent />} />
            <Route path="/customer"            element={<CustomerAgent />} />
            <Route path="/service-fulfillment" element={<ServiceFulfillment />} />
            <Route path="/service-assurance"   element={<ServiceAssurance />} />
            <Route path="/billing"             element={<BillingAgent />} />
            <Route path="/call"                element={<CallAgent />} />
            <Route path="/social-media"        element={<SocialMediaAgent />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}
