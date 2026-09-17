import { useEffect, useMemo, useState } from 'react'
import { getJSON, postJSON } from './api.js'
import { useVehicles } from './live.js'
import Logo from './components/Logo.jsx'
import PhoneFrame from './components/PhoneFrame.jsx'
import HomeView from './components/HomeView.jsx'
import ResultsView from './components/ResultsView.jsx'
import PaymentView from './components/PaymentView.jsx'
import TicketView from './components/TicketView.jsx'
import ReceiptView from './components/ReceiptView.jsx'
import DriverView from './components/DriverView.jsx'
import SpendingsView from './components/SpendingsView.jsx'

export default function App() {
  // Lien direct #driver → ouvrir le tableau de bord conducteur (utile en démo/test)
  const [view, setView] = useState(() =>
    typeof window !== 'undefined' && window.location.hash === '#driver' ? 'driver' : 'home'
  )
  const [returnTo, setReturnTo] = useState('home')
  const [pois, setPois] = useState([])
  const [network, setNetwork] = useState(null)
  const [plan, setPlan] = useState(null)
  const [selected, setSelected] = useState(null)
  const [ticket, setTicket] = useState(null)
  const [autoPrint, setAutoPrint] = useState(false)
  const [fullscreen, setFullscreen] = useState(false)
  const vehicles = useVehicles()

  useEffect(() => {
    getJSON('/api/pois').then(setPois).catch(() => {})
    getJSON('/api/network').then(setNetwork).catch(() => {})
  }, [])

  const stopMap = useMemo(() => {
    const m = {}
    network?.stops.features.forEach((f) => {
      m[f.properties.id] = {
        ...f.properties,
        lon: f.geometry.coordinates[0],
        lat: f.geometry.coordinates[1],
      }
    })
    return m
  }, [network])

  async function search(body) {
    const p = await postJSON('/api/plan', body)
    setPlan(p)
    setSelected(p.itineraries[0])
    setView('results')
  }

  function toggleDriver() {
    if (view === 'driver') setView(returnTo || 'home')
    else {
      setReturnTo(view)
      setView('driver')
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <Logo size={40} />
          <div>
            <div className="brand-name">
              Abidjan<span>Mob</span>
            </div>
            <div className="brand-tag">Bouger à Abidjan, simplement</div>
          </div>
        </div>
        <div className="topbar-right">
          <span className="badge-aimd">Prototype · Démo AIMD 2026</span>
          <button
            className={`tb-btn ${view === 'driver' ? 'tb-btn-active' : ''}`}
            onClick={toggleDriver}
          >
            {view === 'driver' ? '👤 Mode passager' : '🚐 Mode conducteur'}
          </button>
          <button className="tb-btn" onClick={() => setFullscreen(!fullscreen)} title="Plein écran">
            {fullscreen ? '⤢' : '⛶'}
          </button>
        </div>
      </header>

      <main className="stage">
        <PhoneFrame fullscreen={fullscreen}>
          {view === 'home' && (
            <HomeView
              pois={pois}
              network={network}
              vehicles={vehicles}
              onSearch={search}
              onSpendings={() => setView('spendings')}
            />
          )}
          {view === 'results' && plan && (
            <ResultsView
              plan={plan}
              selected={selected}
              onSelect={setSelected}
              onPay={(it) => {
                setSelected(it)
                setView('pay')
              }}
              onBack={() => setView('home')}
              stopMap={stopMap}
              network={network}
              vehicles={vehicles}
            />
          )}
          {view === 'pay' && selected && (
            <PaymentView
              itinerary={selected}
              onCancel={() => setView('results')}
              onDone={(t) => {
                setTicket(t)
                setView('ticket')
              }}
            />
          )}
          {view === 'ticket' && ticket && (
            <TicketView
              ticket={ticket}
              itinerary={selected}
              vehicles={vehicles}
              stopMap={stopMap}
              onHome={() => setView('home')}
              onReceipt={() => {
                setAutoPrint(false)
                setView('receipt')
              }}
              onPrint={() => {
                setAutoPrint(true)
                setView('receipt')
              }}
            />
          )}
          {view === 'receipt' && ticket && (
            <ReceiptView
              ticket={ticket}
              autoPrint={autoPrint}
              onBack={() => setView('ticket')}
            />
          )}
          {view === 'driver' && (
            <DriverView onBack={toggleDriver} network={network} vehicles={vehicles} />
          )}
          {view === 'spendings' && <SpendingsView onBack={() => setView('home')} />}
        </PhoneFrame>
      </main>

      <footer className="page-footer">
        Prototype de démonstration : données indicatives · paiements simulés (aucun débit
        réel) · Fond de carte © OpenStreetMap contributors
      </footer>
    </div>
  )
}
