import { useEffect, useRef, useState } from 'react'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { MODE_ICONS } from '../api.js'

const stopCoord = (network, id) => {
  const f = network?.stops.features.find((x) => x.properties.id === id)
  return f ? f.geometry.coordinates : null
}

function networkFeatures(network) {
  if (!network) return { type: 'FeatureCollection', features: [] }
  const lines = network.lines.map((ln) => ({
    type: 'Feature',
    geometry: {
      type: 'LineString',
      coordinates: ln.coords.map(([lat, lon]) => [lon, lat]),
    },
    properties: { color: ln.color, name: ln.name, fare: ln.fare, headway_min: ln.headway_min },
  }))
  const stops = network.stops.features.map((f) => ({
    type: 'Feature',
    geometry: f.geometry,
    properties: f.properties,
  }))
  return { type: 'FeatureCollection', features: [...lines, ...stops] }
}

function routeFeatures(itinerary, network) {
  if (!itinerary || !network) return { type: 'FeatureCollection', features: [] }
  const feats = []
  for (const leg of itinerary.legs) {
    if (leg.type === 'ride') {
      const line = network.lines.find((l) => l.id === leg.line_id)
      let coords = null
      if (line) {
        const i = line.stops.indexOf(leg.from)
        const j = line.stops.indexOf(leg.to)
        if (i >= 0 && j >= 0) {
          const step = i < j ? 1 : -1
          coords = []
          for (let k = i; step > 0 ? k <= j : k >= j; k += step) {
            coords.push(stopCoord(network, line.stops[k]))
          }
        }
      }
      if (!coords) {
        const a = stopCoord(network, leg.from)
        const b = stopCoord(network, leg.to)
        if (a && b) coords = [a, b]
      }
      if (coords) {
        feats.push({
          type: 'Feature',
          geometry: { type: 'LineString', coordinates: coords },
          properties: { color: leg.color },
        })
      }
    } else {
      const a = stopCoord(network, leg.from)
      const b = stopCoord(network, leg.to)
      if (a && b) {
        feats.push({
          type: 'Feature',
          geometry: { type: 'LineString', coordinates: [a, b] },
          properties: { color: '#1A2238', walk: true },
        })
      }
    }
  }
  return { type: 'FeatureCollection', features: feats }
}

function clearLayers(map, ids) {
  for (const id of ids) {
    if (map.getLayer(id)) map.removeLayer(id)
    if (map.getSource(id)) map.removeSource(id)
  }
}

export default function MapView({ network, itinerary, plan, vehicles, dim = false }) {
  const containerRef = useRef(null)
  const mapRef = useRef(null)
  const renderRef = useRef(() => {})
  const vehicleSyncRef = useRef(() => {})
  const markersRef = useRef([])
  const vehicleMarkersRef = useRef({})
  const [mapFailed, setMapFailed] = useState(false)
  const dataRef = useRef({ network, itinerary, plan, dim })
  dataRef.current = { network, itinerary, plan, dim }
  const vehiclesRef = useRef(vehicles)
  vehiclesRef.current = vehicles

  useEffect(() => {
    let map
    try {
      map = new maplibregl.Map({
        container: containerRef.current,
        style: {
          version: 8,
          sources: {
            osm: {
              type: 'raster',
              tiles: ['/tiles/{z}/{x}/{y}.png'],
              tileSize: 256,
              attribution: '© OpenStreetMap contributors',
            },
          },
          layers: [{ id: 'osm', type: 'raster', source: 'osm' }],
        },
        center: [-4.0, 5.335],
        zoom: 11.2,
      })
    } catch (e) {
      // WebGL indisponible (driver, machine virtuelle…) : l'app reste utilisable sans carte.
      setMapFailed(true)
      return
    }
    mapRef.current = map

    const render = () => {
      const { network: net, itinerary: it, plan: p, dim: d } = dataRef.current
      clearLayers(map, ['route-lines', 'route-walk', 'net-lines', 'net-stops'])
      markersRef.current.forEach((m) => m.remove())
      markersRef.current = []

      if (net) {
        map.addSource('net', { type: 'geojson', data: networkFeatures(net) })
        map.addLayer({
          id: 'net-lines',
          type: 'line',
          source: 'net',
          filter: ['==', '$type', 'LineString'],
          paint: {
            'line-color': ['get', 'color'],
            'line-width': 2.5,
            'line-opacity': d ? 0.16 : 0.45,
          },
        })
        map.addLayer({
          id: 'net-stops',
          type: 'circle',
          source: 'net',
          filter: ['==', '$type', 'Point'],
          paint: {
            'circle-radius': ['case', ['==', ['get', 'kind'], 'hub'], 5, 3.2],
            'circle-color': '#1A2238',
            'circle-stroke-color': '#ffffff',
            'circle-stroke-width': 1.2,
            'circle-opacity': d ? 0.25 : 0.85,
          },
        })
      }

      if (it && net) {
        const route = routeFeatures(it, net)
        map.addSource('route', { type: 'geojson', data: route })
        map.addLayer({
          id: 'route-lines',
          type: 'line',
          source: 'route',
          filter: ['!=', ['get', 'walk'], true],
          layout: { 'line-cap': 'round', 'line-join': 'round' },
          paint: { 'line-color': ['get', 'color'], 'line-width': 5.5, 'line-opacity': 0.95 },
        })
        map.addLayer({
          id: 'route-walk',
          type: 'line',
          source: 'route',
          filter: ['==', ['get', 'walk'], true],
          paint: {
            'line-color': ['get', 'color'],
            'line-width': 3,
            'line-opacity': 0.8,
            'line-dasharray': [2, 1.5],
          },
        })
        const bounds = new maplibregl.LngLatBounds()
        let has = false
        route.features.forEach((f) =>
          f.geometry.coordinates.forEach((c) => {
            bounds.extend(c)
            has = true
          })
        )
        if (has) map.fitBounds(bounds, { padding: 60, duration: 700, maxZoom: 14.5 })
      } else if (net) {
        const bounds = new maplibregl.LngLatBounds()
        net.stops.features.forEach((f) => bounds.extend(f.geometry.coordinates))
        map.fitBounds(bounds, { padding: 40, duration: 0, maxZoom: 12 })
      }

      if (p && net) {
        const fromEl = document.createElement('div')
        fromEl.className = 'mk mk-from'
        const toEl = document.createElement('div')
        toEl.className = 'mk mk-to'
        markersRef.current.push(
          new maplibregl.Marker({ element: fromEl })
            .setLngLat([p.from.stop.lon, p.from.stop.lat])
            .addTo(map),
          new maplibregl.Marker({ element: toEl })
            .setLngLat([p.to.stop.lon, p.to.stop.lat])
            .addTo(map)
        )
      }
    }
    renderRef.current = render

    const syncVehicles = () => {
      const list = vehiclesRef.current || []
      const seen = new Set()
      for (const v of list) {
        seen.add(v.vehicle_id)
        let m = vehicleMarkersRef.current[v.vehicle_id]
        const title = v.driver_name
          ? `${v.driver_name} · ${v.line_name} · ${v.dir_label}`
          : `${v.line_name} · ${v.dir_label}`
        if (!m) {
          const el = document.createElement('div')
          el.className = `vhc vhc-${v.mode}`
          el.innerHTML = `<span class="vhc-pulse"></span><span class="vhc-ico">${MODE_ICONS[v.mode] || '🚐'}</span>`
          el.title = title
          m = new maplibregl.Marker({ element: el }).setLngLat([v.lon, v.lat]).addTo(map)
          vehicleMarkersRef.current[v.vehicle_id] = m
        } else {
          m.setLngLat([v.lon, v.lat])
          m.getElement().title = title
        }
      }
      for (const id of Object.keys(vehicleMarkersRef.current)) {
        if (!seen.has(id)) {
          vehicleMarkersRef.current[id].remove()
          delete vehicleMarkersRef.current[id]
        }
      }
    }
    vehicleSyncRef.current = syncVehicles

    map.on('load', () => {
      render()
      syncVehicles()
      map.on('click', 'net-lines', (e) => {
        const f = e.features[0]
        new maplibregl.Popup({ closeButton: false })
          .setLngLat(e.lngLat)
          .setHTML(
            `<b>${f.properties.name}</b><br>${f.properties.fare} FCFA · départ ~ toutes les ${f.properties.headway_min} min`
          )
          .addTo(map)
      })
      map.on('mouseenter', 'net-lines', () => (map.getCanvas().style.cursor = 'pointer'))
      map.on('mouseleave', 'net-lines', () => (map.getCanvas().style.cursor = ''))
    })

    return () => {
      markersRef.current.forEach((m) => m.remove())
      Object.values(vehicleMarkersRef.current).forEach((m) => m.remove())
      vehicleMarkersRef.current = {}
      map.remove()
    }
  }, [])

  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    if (map.isStyleLoaded()) renderRef.current()
    else map.once('load', renderRef.current)
  }, [network, itinerary, plan, dim])

  useEffect(() => {
    if (mapRef.current) vehicleSyncRef.current()
  }, [vehicles])

  if (mapFailed) {
    return (
      <div className="map-fallback">
        🗺️ Carte indisponible sur cet appareil — itinéraires et paiement restent accessibles.
      </div>
    )
  }
  return <div ref={containerRef} className="map-view" />
}
