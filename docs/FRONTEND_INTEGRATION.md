# 🚀 Guide d'Intégration Frontend - UbuntuAirLab API

> Guide complet pour intégrer l'API UbuntuAirLab dans votre application frontend (React, Vue, Angular, Next.js)

## 📋 Table des matières

1. [⚡ Démarrage Rapide](#-démarrage-rapide)
2. [🔧 Configuration](#-configuration)
3. [🔐 Authentification Complète](#-authentification-complète)
4. [📡 API Reference](#-api-reference)
5. [💻 Exemples Pratiques](#-exemples-pratiques)
6. [⚠️ Gestion des Erreurs](#️-gestion-des-erreurs)
7. [🎯 Best Practices](#-best-practices)

---

## ⚡ Démarrage Rapide

### Étape 1: URL de l'API

```
Production: https://ubuntuairlab.azurewebsites.net/api/v1
```

### Étape 2: Test rapide avec cURL

```bash
# Tester si l'API est accessible
curl https://air-lab.bestwebapp.tech/api/v1/

# Devrait retourner: {"message": "Welcome to UbuntuAirLab API"}
```

### Étape 3: Premier appel authentifié

```bash
# 1. Se connecter
curl -X POST https://air-lab.bestwebapp.tech/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=votre-email@example.com&password=votre-password"

# Réponse: {"access_token": "eyJhbG...", "token_type": "bearer"}

# 2. Utiliser le token
curl https://air-lab.bestwebapp.tech/api/v1/flights \
  -H "Authorization: Bearer eyJhbG..."
```

---

## 🔧 Configuration

### Option 1: React/Next.js avec Axios

#### Installation
```bash
npm install axios
```

#### Créer le fichier de configuration
```typescript
// lib/api.ts
import axios from 'axios';

// URL de base de l'API
const BASE_URL = 'https://air-lab.bestwebapp.tech/api/v1';

// Créer l'instance axios
export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Ajouter automatiquement le token à chaque requête
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Gérer les erreurs 401 (token expiré)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expiré, rediriger vers login
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
```

### Option 2: Vue 3 avec Fetch API

```typescript
// composables/useApi.ts
import { ref } from 'vue';

const BASE_URL = 'https://air-lab.bestwebapp.tech/api/v1';

export function useApi() {
  const loading = ref(false);
  const error = ref<string | null>(null);

  const fetchApi = async (endpoint: string, options: RequestInit = {}) => {
    loading.value = true;
    error.value = null;

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${BASE_URL}${endpoint}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...(token && { Authorization: `Bearer ${token}` }),
          ...options.headers,
        },
      });

      if (response.status === 401) {
        localStorage.removeItem('token');
        window.location.href = '/login';
        throw new Error('Non authentifié');
      }

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Erreur API');
      }

      return await response.json();
    } catch (err: any) {
      error.value = err.message;
      throw err;
    } finally {
      loading.value = false;
    }
  };

  return { fetchApi, loading, error };
}
```

### Option 3: Vanilla JavaScript

```javascript
// api.js
const BASE_URL = 'https://air-lab.bestwebapp.tech/api/v1';

async function apiCall(endpoint, options = {}) {
  const token = localStorage.getItem('token');
  
  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    },
  });

  if (response.status === 401) {
    localStorage.removeItem('token');
    window.location.href = '/login';
  }

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Erreur API');
  }

  return response.json();
}

export { apiCall };
```

### Variables d'environnement

**.env.local** (développement)
```bash
NEXT_PUBLIC_API_URL=https://air-lab.bestwebapp.tech/api/v1
```

**.env.production**
```bash
NEXT_PUBLIC_API_URL=https://air-lab.bestwebapp.tech/api/v1
```


---

## 🔐 Authentification Complète

### Flow d'authentification

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Frontend  │      │  Backend API │      │  Database   │
└──────┬──────┘      └───────┬──────┘      └──────┬──────┘
       │                     │                    │
       │  POST /auth/login   │                    │
       │ ──────────────────> │                    │
       │                     │   Verify user      │
       │                     │ ─────────────────> │
       │                     │ <───────────────── │
       │   JWT Token         │                    │
       │ <────────────────── │                    │
       │                     │                    │
       │  Store in          │                    │
       │  localStorage       │                    │
       │                     │                    │
       │  GET /flights       │                    │
       │  + Bearer Token     │                    │
       │ ──────────────────> │                    │
       │                     │   Get flights      │
       │                     │ ─────────────────> │
       │   Flights data      │ <───────────────── │
       │ <────────────────── │                    │
```

### 1. Inscription d'un nouvel utilisateur

**Endpoint:** `POST /auth/register`

```typescript
// services/auth.ts
import api from '@/lib/api';

interface RegisterData {
  email: string;
  password: string;
  full_name: string;
  role?: 'operator' | 'admin' | 'viewer';
}

interface AuthResponse {
  access_token: string;
  token_type: string;
  user: {
    id: number;
    email: string;
    full_name: string;
    role: string;
    is_active: boolean;
  };
}

export async function register(data: RegisterData): Promise<AuthResponse> {
  const response = await api.post<AuthResponse>('/auth/register', {
    email: data.email,
    password: data.password,
    full_name: data.full_name,
    role: data.role || 'operator'
  });
  
  // Sauvegarder le token
  localStorage.setItem('token', response.data.access_token);
  localStorage.setItem('user', JSON.stringify(response.data.user));
  
  return response.data;
}
```

**Exemple d'utilisation dans React:**
```typescript
// components/RegisterForm.tsx
import { useState } from 'react';
import { register } from '@/services/auth';

export function RegisterForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const result = await register({
        email,
        password,
        full_name: fullName,
      });
      
      console.log('Inscription réussie:', result.user);
      window.location.href = '/dashboard';
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erreur lors de l\'inscription');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="email"
        placeholder="Email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
      />
      <input
        type="password"
        placeholder="Mot de passe"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />
      <input
        type="text"
        placeholder="Nom complet"
        value={fullName}
        onChange={(e) => setFullName(e.target.value)}
        required
      />
      
      {error && <div className="error">{error}</div>}
      
      <button type="submit" disabled={loading}>
        {loading ? 'Inscription...' : 'S\'inscrire'}
      </button>
    </form>
  );
}
```

### 2. Connexion

**Endpoint:** `POST /auth/login`

⚠️ **Important:** Le endpoint login utilise `application/x-www-form-urlencoded` (pas JSON)

```typescript
// services/auth.ts
export async function login(email: string, password: string): Promise<AuthResponse> {
  // Créer FormData pour le format x-www-form-urlencoded
  const formData = new FormData();
  formData.append('username', email);  // ⚠️ Le champ s'appelle "username" pas "email"
  formData.append('password', password);

  const response = await api.post<AuthResponse>('/auth/login', formData, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  });

  // Sauvegarder le token
  localStorage.setItem('token', response.data.access_token);
  
  return response.data;
}
```

**Exemple React complet:**
```typescript
// components/LoginForm.tsx
import { useState } from 'react';
import { login } from '@/services/auth';

export function LoginForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      await login(email, password);
      window.location.href = '/dashboard';
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Email ou mot de passe incorrect');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleLogin}>
      <h2>Connexion</h2>
      
      <input
        type="email"
        placeholder="Email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
      />
      
      <input
        type="password"
        placeholder="Mot de passe"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />
      
      {error && <div style={{ color: 'red' }}>{error}</div>}
      
      <button type="submit" disabled={loading}>
        {loading ? 'Connexion...' : 'Se connecter'}
      </button>
    </form>
  );
}
```

### 3. Vérifier si l'utilisateur est connecté

```typescript
// services/auth.ts
export function isAuthenticated(): boolean {
  const token = localStorage.getItem('token');
  return !!token;
}

export function getToken(): string | null {
  return localStorage.getItem('token');
}

export function logout() {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  window.location.href = '/login';
}
```

**Route protégée (React):**
```typescript
// components/ProtectedRoute.tsx
import { useEffect } from 'react';
import { isAuthenticated } from '@/services/auth';

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    if (!isAuthenticated()) {
      window.location.href = '/login';
    }
  }, []);

  if (!isAuthenticated()) {
    return <div>Redirection...</div>;
  }

  return <>{children}</>;
}

// Utilisation
function App() {
  return (
    <ProtectedRoute>
      <Dashboard />
    </ProtectedRoute>
  );
}
```

### 4. Obtenir le profil utilisateur

**Endpoint:** `GET /auth/me`

```typescript
// services/auth.ts
interface User {
  id: number;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export async function getCurrentUser(): Promise<User> {
  const response = await api.get<User>('/auth/me');
  return response.data;
}
```

**Hook React:**
```typescript
// hooks/useAuth.ts
import { useState, useEffect } from 'react';
import { getCurrentUser, logout } from '@/services/auth';

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadUser() {
      try {
        const userData = await getCurrentUser();
        setUser(userData);
      } catch (error) {
        console.error('Erreur chargement user:', error);
        logout();
      } finally {
        setLoading(false);
      }
    }

    loadUser();
  }, []);

  return { user, loading, logout };
}

// Utilisation dans un composant
function Header() {
  const { user, logout } = useAuth();

  return (
    <header>
      <span>Bienvenue {user?.full_name}</span>
      <button onClick={logout}>Déconnexion</button>
    </header>
  );
}
```


---

## 📡 API Reference

### 📍 Récap des Endpoints

```
Base URL: https://air-lab.bestwebapp.tech/api/v1
```

| Catégorie | Endpoint | Méthode | Auth | Description |
|-----------|----------|---------|------|-------------|
| **Auth** | `/auth/register` | POST | ❌ | Créer un compte |
| | `/auth/login` | POST | ❌ | Se connecter |
| | `/auth/me` | GET | ✅ | Profil utilisateur |
| **Flights** | `/flights` | GET | ✅ | Liste des vols |
| | `/flights/{icao24}` | GET | ✅ | Détails d'un vol |
| | `/flights/{icao24}/predictions` | GET | ✅ | Prédictions d'un vol |
| **Parking** | `/parking/spots` | GET | ✅ | Liste places parking |
| | `/parking/allocations` | GET | ✅ | Allocations actuelles |
| | `/parking/availability` | GET | ✅ | Disponibilité temps réel |
| | `/parking/conflicts` | GET | ✅ | Conflits détectés |
| | `/parking/allocate` | POST | ✅ | Allouer automatiquement |
| **Predictions** | `/predictions/predict` | POST | ✅ | Prédiction ML |
| | `/predictions/health` | GET | ✅ | Santé API ML |
| | `/predictions/models/info` | GET | ✅ | Info modèles ML |
| **Dashboard** | `/dashboard/stats` | GET | ✅ | Statistiques temps réel |
| **Notifications** | `/notifications/notifications` | GET | ✅ | Liste notifications |
| | `/notifications/notifications/unread/count` | GET | ✅ | Compte non lues |
| **Sync** | `/sync/trigger` | POST | ✅ | Sync manuelle |
| | `/sync/status` | GET | ✅ | Statut sync |

---

## 💻 Exemples Pratiques

### 1️⃣ Afficher la liste des vols actifs

```typescript
// services/flights.ts
import api from '@/lib/api';

interface Flight {
  icao24: string;
  callsign: string;
  origin_country: string;
  latitude: number;
  longitude: number;
  altitude: number;
  velocity: number;
  heading: number;
  vertical_rate: number;
  flight_type: 'arrival' | 'departure';
  status: 'active' | 'landed' | 'scheduled';
  last_seen: string;
  predicted_eta: string | null;
  predicted_etd: string | null;
  assigned_parking: string | null;
}

interface FlightsResponse {
  flights: Flight[];
  total: number;
  limit: number;
  offset: number;
}

export async function getFlights(params?: {
  status?: 'active' | 'landed' | 'scheduled';
  type?: 'arrival' | 'departure';
  limit?: number;
  offset?: number;
}): Promise<FlightsResponse> {
  const queryParams = new URLSearchParams();
  
  if (params?.status) queryParams.append('status', params.status);
  if (params?.type) queryParams.append('type', params.type);
  if (params?.limit) queryParams.append('limit', params.limit.toString());
  if (params?.offset) queryParams.append('offset', params.offset.toString());

  const response = await api.get<FlightsResponse>(
    `/flights?${queryParams.toString()}`
  );
  
  return response.data;
}
```

**Composant React:**
```typescript
// components/FlightsList.tsx
import { useState, useEffect } from 'react';
import { getFlights } from '@/services/flights';

export function FlightsList() {
  const [flights, setFlights] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function loadFlights() {
      try {
        const data = await getFlights({ status: 'active', limit: 50 });
        setFlights(data.flights);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    loadFlights();
    
    // Rafraîchir toutes les 30 secondes
    const interval = setInterval(loadFlights, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div>Chargement des vols...</div>;
  if (error) return <div>Erreur: {error}</div>;

  return (
    <div>
      <h2>Vols Actifs ({flights.length})</h2>
      <table>
        <thead>
          <tr>
            <th>Callsign</th>
            <th>Pays</th>
            <th>Type</th>
            <th>Altitude</th>
            <th>Vitesse</th>
            <th>Parking</th>
          </tr>
        </thead>
        <tbody>
          {flights.map((flight) => (
            <tr key={flight.icao24}>
              <td>{flight.callsign}</td>
              <td>{flight.origin_country}</td>
              <td>{flight.flight_type}</td>
              <td>{Math.round(flight.altitude)}m</td>
              <td>{Math.round(flight.velocity)} km/h</td>
              <td>{flight.assigned_parking || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

### 2️⃣ Détails d'un vol spécifique

```typescript
// services/flights.ts
export async function getFlightDetails(icao24: string): Promise<Flight> {
  const response = await api.get<Flight>(`/flights/${icao24}`);
  return response.data;
}
```

**Page de détails (Next.js):**
```typescript
// app/flights/[icao24]/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { getFlightDetails } from '@/services/flights';

export default function FlightDetailsPage() {
  const params = useParams();
  const [flight, setFlight] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await getFlightDetails(params.icao24 as string);
        setFlight(data);
      } catch (error) {
        console.error('Erreur:', error);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [params.icao24]);

  if (loading) return <div>Chargement...</div>;
  if (!flight) return <div>Vol non trouvé</div>;

  return (
    <div>
      <h1>Vol {flight.callsign}</h1>
      <dl>
        <dt>ICAO24:</dt>
        <dd>{flight.icao24}</dd>
        
        <dt>Pays d'origine:</dt>
        <dd>{flight.origin_country}</dd>
        
        <dt>Position:</dt>
        <dd>
          Lat: {flight.latitude.toFixed(4)}, 
          Lon: {flight.longitude.toFixed(4)}
        </dd>
        
        <dt>Altitude:</dt>
        <dd>{Math.round(flight.altitude)} mètres</dd>
        
        <dt>Vitesse:</dt>
        <dd>{Math.round(flight.velocity)} km/h</dd>
        
        <dt>ETA prédit:</dt>
        <dd>{flight.predicted_eta || 'Non disponible'}</dd>
        
        <dt>Parking assigné:</dt>
        <dd>{flight.assigned_parking || 'Aucun'}</dd>
      </dl>
    </div>
  );
}
```

### 3️⃣ Disponibilité des parkings

```typescript
// services/parking.ts
import api from '@/lib/api';

interface ParkingAvailability {
  total_spots: number;
  available: number;
  occupied: number;
  maintenance: number;
  utilization_rate: number;
  spots_by_type: {
    [key: string]: {
      total: number;
      available: number;
    };
  };
}

export async function getParkingAvailability(): Promise<ParkingAvailability> {
  const response = await api.get<ParkingAvailability>('/parking/availability');
  return response.data;
}
```

**Composant Widget:**
```typescript
// components/ParkingWidget.tsx
import { useState, useEffect } from 'react';
import { getParkingAvailability } from '@/services/parking';

export function ParkingWidget() {
  const [data, setData] = useState(null);

  useEffect(() => {
    async function load() {
      const availability = await getParkingAvailability();
      setData(availability);
    }
    
    load();
    const interval = setInterval(load, 60000); // Refresh chaque minute
    return () => clearInterval(interval);
  }, []);

  if (!data) return <div>Chargement...</div>;

  return (
    <div className="parking-widget">
      <h3>Parking - Disponibilité</h3>
      
      <div className="stats">
        <div className="stat">
          <span className="label">Total</span>
          <span className="value">{data.total_spots}</span>
        </div>
        
        <div className="stat available">
          <span className="label">Disponibles</span>
          <span className="value">{data.available}</span>
        </div>
        
        <div className="stat occupied">
          <span className="label">Occupés</span>
          <span className="value">{data.occupied}</span>
        </div>
        
        <div className="stat maintenance">
          <span className="label">Maintenance</span>
          <span className="value">{data.maintenance}</span>
        </div>
      </div>

      <div className="utilization">
        Taux d'utilisation: {(data.utilization_rate * 100).toFixed(1)}%
      </div>

      <div className="by-type">
        <h4>Par type:</h4>
        {Object.entries(data.spots_by_type).map(([type, stats]) => (
          <div key={type}>
            <strong>{type}:</strong> {stats.available}/{stats.total} disponibles
          </div>
        ))}
      </div>
    </div>
  );
}
```

### 4️⃣ Statistiques Dashboard

```typescript
// services/dashboard.ts
import api from '@/lib/api';

interface DashboardStats {
  active_flights: number;
  arrivals_today: number;
  departures_today: number;
  parking_utilization: number;
  average_turnaround: number;
  delays_count: number;
  conflicts_detected: number;
}

export async function getDashboardStats(): Promise<DashboardStats> {
  const response = await api.get<DashboardStats>('/dashboard/stats');
  return response.data;
}
```

**Dashboard complet:**
```typescript
// components/Dashboard.tsx
import { useState, useEffect } from 'react';
import { getDashboardStats } from '@/services/dashboard';
import { FlightsList } from './FlightsList';
import { ParkingWidget } from './ParkingWidget';

export function Dashboard() {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    async function load() {
      const data = await getDashboardStats();
      setStats(data);
    }
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, []);

  if (!stats) return <div>Chargement...</div>;

  return (
    <div className="dashboard">
      <h1>Tableau de Bord</h1>

      <div className="stats-grid">
        <div className="card">
          <h3>Vols Actifs</h3>
          <div className="big-number">{stats.active_flights}</div>
        </div>

        <div className="card">
          <h3>Arrivées Aujourd'hui</h3>
          <div className="big-number">{stats.arrivals_today}</div>
        </div>

        <div className="card">
          <h3>Départs Aujourd'hui</h3>
          <div className="big-number">{stats.departures_today}</div>
        </div>

        <div className="card">
          <h3>Taux Parking</h3>
          <div className="big-number">
            {(stats.parking_utilization * 100).toFixed(0)}%
          </div>
        </div>

        <div className="card">
          <h3>Turnaround Moyen</h3>
          <div className="big-number">{Math.round(stats.average_turnaround)} min</div>
        </div>

        <div className="card alert">
          <h3>Retards</h3>
          <div className="big-number">{stats.delays_count}</div>
        </div>

        <div className="card warning">
          <h3>Conflits</h3>
          <div className="big-number">{stats.conflicts_detected}</div>
        </div>
      </div>

      <div className="content-grid">
        <div className="section">
          <FlightsList />
        </div>
        
        <div className="section">
          <ParkingWidget />
        </div>
      </div>
    </div>
  );
}
```

### 5️⃣ Prédiction ML pour un vol

```typescript
// services/predictions.ts
import api from '@/lib/api';

interface FlightPredictionRequest {
  callsign: string;
  icao24: string;
  vitesse_actuelle: number;
  altitude: number;
  distance_piste: number;
  temperature: number;
  vent_vitesse: number;
  vent_direction: number;
  visibilite: number;
  pluie: number;
  compagnie: string;
  retard_historique_compagnie: number;
  trafic_approche: number;
  occupation_tarmac: number;
  type_avion: string;
  historique_occupation_avion: number;
  type_vol: number;
  passagers_estimes: number;
  disponibilite_emplacements: number;
  occupation_actuelle: number;
  meteo_score: number;
  trafic_entrant: number;
  trafic_sortant: number;
  priorite_vol: number;
  emplacements_futurs_libres: number;
  heure_jour: number;
  jour_semaine: number;
  periode_annee: number;
}

interface PredictionResponse {
  model_1_eta: {
    eta_ajuste: number;
    proba_delay_15: number;
    proba_delay_30: number;
    confidence: number;
  };
  model_2_occupation: {
    temps_occupation_minutes: number;
    intervalle_confiance_min: number;
    intervalle_confiance_max: number;
  };
  model_3_conflict: {
    conflit_detecte: boolean;
    score_risque: number;
    emplacements_recommandes: string[];
  };
  metadata: {
    timestamp: string;
    model_version: string;
  };
}

export async function predictFlight(data: FlightPredictionRequest): Promise<PredictionResponse> {
  const response = await api.post<PredictionResponse>('/predictions/predict', data);
  return response.data;
}
```

**Exemple d'utilisation:**
```typescript
// components/FlightPrediction.tsx
import { useState } from 'react';
import { predictFlight } from '@/services/predictions';

export function FlightPrediction({ flight }) {
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(false);

  const handlePredict = async () => {
    setLoading(true);
    try {
      const result = await predictFlight({
        callsign: flight.callsign,
        icao24: flight.icao24,
        vitesse_actuelle: flight.velocity,
        altitude: flight.altitude,
        distance_piste: 20.0,
        temperature: 25.0,
        vent_vitesse: 10.0,
        vent_direction: 180.0,
        visibilite: 10.0,
        pluie: 0,
        compagnie: flight.callsign.substring(0, 3),
        retard_historique_compagnie: 5.0,
        trafic_approche: 3,
        occupation_tarmac: 0.5,
        type_avion: 'A320',
        historique_occupation_avion: 45.0,
        type_vol: flight.flight_type === 'arrival' ? 0 : 1,
        passagers_estimes: 150,
        disponibilite_emplacements: 17,
        occupation_actuelle: 0.6,
        meteo_score: 0.8,
        trafic_entrant: 5,
        trafic_sortant: 4,
        priorite_vol: 0,
        emplacements_futurs_libres: 5,
        heure_jour: new Date().getHours(),
        jour_semaine: new Date().getDay(),
        periode_annee: new Date().getMonth() + 1,
      });
      
      setPrediction(result);
    } catch (error) {
      console.error('Erreur prédiction:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <button onClick={handlePredict} disabled={loading}>
        {loading ? 'Calcul en cours...' : 'Lancer Prédiction ML'}
      </button>

      {prediction && (
        <div className="prediction-results">
          <h3>Résultats Prédiction</h3>
          
          <div className="model-result">
            <h4>📊 Modèle 1 - ETA</h4>
            <p>ETA ajusté: <strong>{prediction.model_1_eta.eta_ajuste.toFixed(1)} min</strong></p>
            <p>Probabilité retard 15min: {(prediction.model_1_eta.proba_delay_15 * 100).toFixed(1)}%</p>
            <p>Probabilité retard 30min: {(prediction.model_1_eta.proba_delay_30 * 100).toFixed(1)}%</p>
            <p>Confiance: {(prediction.model_1_eta.confidence * 100).toFixed(1)}%</p>
          </div>

          <div className="model-result">
            <h4>⏱️ Modèle 2 - Occupation Parking</h4>
            <p>Durée estimée: <strong>{Math.round(prediction.model_2_occupation.temps_occupation_minutes)} min</strong></p>
            <p>Intervalle: {prediction.model_2_occupation.intervalle_confiance_min} - {prediction.model_2_occupation.intervalle_confiance_max} min</p>
          </div>

          <div className="model-result">
            <h4>⚠️ Modèle 3 - Détection Conflits</h4>
            <p>Conflit détecté: <strong>{prediction.model_3_conflict.conflit_detecte ? 'OUI' : 'NON'}</strong></p>
            <p>Score de risque: {(prediction.model_3_conflict.score_risque * 100).toFixed(1)}%</p>
            <p>Parkings recommandés: {prediction.model_3_conflict.emplacements_recommandes.join(', ')}</p>
          </div>
        </div>
      )}
    </div>
  );
}
```

---

## ⚠️ Gestion des Erreurs

### Codes d'erreur HTTP

| Code | Nom | Signification | Action |
|------|-----|---------------|--------|
| 200 | OK | Succès | ✅ Continuer |
| 201 | Created | Ressource créée | ✅ Continuer |
| 400 | Bad Request | Paramètres invalides | ⚠️ Vérifier les données envoyées |
| 401 | Unauthorized | Token manquant/expiré | 🔒 Rediriger vers /login |
| 403 | Forbidden | Permissions insuffisantes | ⛔ Afficher message d'erreur |
| 404 | Not Found | Ressource inexistante | ❓ Vérifier l'URL/ID |
| 422 | Unprocessable Entity | Validation échouée | ⚠️ Afficher erreurs de validation |
| 429 | Too Many Requests | Rate limit dépassé | ⏸️ Attendre avant retry |
| 500 | Internal Server Error | Erreur serveur | 🔥 Réessayer plus tard |
| 503 | Service Unavailable | ML API offline | 🚨 Afficher message maintenance |

### Format des erreurs API

Toutes les erreurs retournent:
```json
{
  "detail": "Message d'erreur descriptif"
}
```

### Handler d'erreurs global

```typescript
// utils/errorHandler.ts
interface ApiError {
  response?: {
    status: number;
    data: {
      detail?: string;
      [key: string]: any;
    };
  };
  request?: any;
  message: string;
}

export function handleApiError(error: ApiError): string {
  // Erreur avec réponse serveur
  if (error.response) {
    const { status, data } = error.response;
    
    switch (status) {
      case 400:
        return data.detail || 'Requête invalide. Vérifiez les paramètres.';
      
      case 401:
        // Token expiré ou manquant
        localStorage.removeItem('token');
        window.location.href = '/login';
        return 'Session expirée. Reconnexion requise.';
      
      case 403:
        return 'Vous n\'avez pas les permissions nécessaires pour cette action.';
      
      case 404:
        return 'Ressource introuvable.';
      
      case 422:
        // Erreurs de validation
        if (data.detail && Array.isArray(data.detail)) {
          return data.detail.map((err: any) => 
            `${err.loc.join('.')}: ${err.msg}`
          ).join(', ');
        }
        return data.detail || 'Données invalides.';
      
      case 429:
        return 'Trop de requêtes. Veuillez patienter quelques instants.';
      
      case 500:
        return 'Erreur serveur. Veuillez réessayer plus tard.';
      
      case 503:
        return 'Service ML temporairement indisponible. Réessayez dans quelques minutes.';
      
      default:
        return data.detail || `Erreur ${status}`;
    }
  }
  
  // Erreur réseau (pas de réponse)
  if (error.request) {
    return 'Impossible de contacter le serveur. Vérifiez votre connexion internet.';
  }
  
  // Autre erreur
  return error.message || 'Une erreur inattendue est survenue.';
}
```

### Utilisation du handler

```typescript
// components/FlightsList.tsx
import { handleApiError } from '@/utils/errorHandler';
import { getFlights } from '@/services/flights';

export function FlightsList() {
  const [error, setError] = useState('');

  const loadFlights = async () => {
    try {
      const data = await getFlights({ status: 'active' });
      setFlights(data.flights);
    } catch (err) {
      const errorMessage = handleApiError(err);
      setError(errorMessage);
      console.error('Erreur:', err);
    }
  };

  return (
    <div>
      {error && (
        <div className="alert alert-danger">
          {error}
        </div>
      )}
      {/* ... */}
    </div>
  );
}
```

### Toast notifications (React)

```typescript
// components/ToastProvider.tsx
import { createContext, useContext, useState } from 'react';

interface Toast {
  id: number;
  message: string;
  type: 'success' | 'error' | 'warning' | 'info';
}

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const showToast = (message: string, type: Toast['type'] = 'info') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 5000);
  };

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className="toast-container">
        {toasts.map(toast => (
          <div key={toast.id} className={`toast toast-${toast.type}`}>
            {toast.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);
```

**Utilisation:**
```typescript
import { useToast } from '@/components/ToastProvider';
import { handleApiError } from '@/utils/errorHandler';

function MyComponent() {
  const { showToast } = useToast();

  const handleAction = async () => {
    try {
      await someApiCall();
      showToast('Opération réussie !', 'success');
    } catch (error) {
      const message = handleApiError(error);
      showToast(message, 'error');
    }
  };
}
```

---

## 🎯 Best Practices

### 1. Sécurité

✅ **DO:**
- Utiliser HTTPS en production
- Stocker le JWT dans localStorage ou sessionStorage
- Nettoyer le token à la déconnexion
- Implémenter un auto-logout sur 401
- Ne jamais exposer le token dans les URLs
- Valider les données côté client avant envoi

❌ **DON'T:**
- Stocker le token en cookie sans flag httpOnly en production
- Logger les tokens dans la console en production
- Envoyer le mot de passe en clair (l'API attend x-www-form-urlencoded)

### 2. Performance

✅ **DO:**
- Mettre en cache les données statiques (liste parkings)
- Utiliser le pagination pour les grandes listes
- Implémenter du debouncing pour la recherche
- Rafraîchir les données critiques toutes les 30-60s
- Utiliser React.memo / Vue computed pour éviter re-renders inutiles

**Exemple de debounce:**
```typescript
// hooks/useDebounce.ts
import { useEffect, useState } from 'react';

export function useDebounce<T>(value: T, delay: number = 500): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}

// Utilisation
function SearchFlights() {
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebounce(search, 500);

  useEffect(() => {
    if (debouncedSearch) {
      searchFlights(debouncedSearch);
    }
  }, [debouncedSearch]);

  return <input value={search} onChange={(e) => setSearch(e.target.value)} />;
}
```

### 3. UX/UI

✅ **DO:**
- Afficher des loaders pendant les requêtes
- Afficher des messages d'erreur clairs
- Permettre de retry en cas d'erreur réseau
- Désactiver les boutons pendant les actions
- Afficher un feedback visuel après les actions

**Exemple de bouton avec état:**
```typescript
function ActionButton({ onClick, children }) {
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleClick = async () => {
    setLoading(true);
    try {
      await onClick();
      setSuccess(true);
      setTimeout(() => setSuccess(false), 2000);
    } catch (error) {
      // Géré par le handler global
    } finally {
      setLoading(false);
    }
  };

  return (
    <button 
      onClick={handleClick} 
      disabled={loading}
      className={success ? 'success' : ''}
    >
      {loading ? '⏳ Chargement...' : success ? '✅ Fait !' : children}
    </button>
  );
}
```

### 4. Gestion d'état

Pour React, utilisez **TanStack Query** (React Query):
```bash
npm install @tanstack/react-query
```

```typescript
// app/providers.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30000, // 30s
    },
  },
});

export function Providers({ children }) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}
```

**Hook personnalisé:**
```typescript
// hooks/useFlights.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getFlights } from '@/services/flights';

export function useFlights(status?: string) {
  return useQuery({
    queryKey: ['flights', status],
    queryFn: () => getFlights({ status }),
    refetchInterval: 30000, // Refresh auto toutes les 30s
  });
}

export function useAllocateParking() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data) => allocateParking(data),
    onSuccess: () => {
      // Invalider le cache pour rafraîchir
      queryClient.invalidateQueries({ queryKey: ['parking'] });
      queryClient.invalidateQueries({ queryKey: ['flights'] });
    },
  });
}
```

### 5. TypeScript

Définir les types pour toute l'API:

```typescript
// types/api.ts
export interface Flight {
  icao24: string;
  callsign: string;
  origin_country: string;
  latitude: number;
  longitude: number;
  altitude: number;
  velocity: number;
  heading: number;
  vertical_rate: number;
  flight_type: 'arrival' | 'departure';
  status: 'active' | 'landed' | 'scheduled';
  last_seen: string;
  predicted_eta: string | null;
  predicted_etd: string | null;
  assigned_parking: string | null;
}

export interface ParkingSpot {
  id: number;
  spot_number: string;
  type: 'commercial' | 'cargo' | 'military';
  status: 'available' | 'occupied' | 'maintenance';
  capacity_category: string;
  is_active: boolean;
}

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: 'admin' | 'operator' | 'viewer';
  is_active: boolean;
  created_at: string;
}

// ... autres types
```

### 6. Environnement de dev vs prod

```typescript
// config/env.ts
export const config = {
  apiUrl: process.env.NEXT_PUBLIC_API_URL || 'https://air-lab.bestwebapp.tech/api/v1',
  isDev: process.env.NODE_ENV === 'development',
  isProd: process.env.NODE_ENV === 'production',
  enableDebug: process.env.NEXT_PUBLIC_DEBUG === 'true',
};

// Utilisation
if (config.isDev) {
  console.log('Debug mode activé');
}
```

---

## 📚 Ressources

### Documentation officielle
- **API Interactive (Swagger):** https://air-lab.bestwebapp.tech/docs
- **OpenAPI Schema:** https://air-lab.bestwebapp.tech/openapi.json
- **API ML (Hugging Face):** https://tagba-ubuntuairlab.hf.space/docs

### Endpoints de test
```bash
# Health check
curl https://air-lab.bestwebapp.tech/api/v1/

# ML API health
curl https://tagba-ubuntuairlab.hf.space/health
```

### Limitations
- **Rate limiting:** 100 requêtes/minute par utilisateur
- **Timeout:** 30 secondes par requête
- **Payload max:** 10 MB
- **ML timeout:** 30 secondes pour les prédictions

---

## 🚨 FAQ / Troubleshooting

### Q: "401 Unauthorized" sur toutes les requêtes
**R:** Vérifiez que:
1. Le token est bien stocké: `localStorage.getItem('token')`
2. Le header est correct: `Authorization: Bearer TOKEN`
3. Le token n'est pas expiré (durée: 24h)

### Q: "CORS error" dans la console
**R:** Normal en développement local. Solutions:
1. Utiliser un proxy dans `package.json` (Create React App)
2. Configurer `vite.config.ts` proxy (Vite)
3. L'API autorise `http://localhost:3000` et `http://localhost:8080`

### Q: Les données ne se rafraîchissent pas
**R:** Implémenter un système de polling:
```typescript
useEffect(() => {
  loadData();
  const interval = setInterval(loadData, 30000);
  return () => clearInterval(interval);
}, []);
```

### Q: "503 Service Unavailable" sur `/predictions/predict`
**R:** L'API ML Hugging Face peut être en veille. Réessayez après 30-60 secondes.

### Q: Comment gérer le refresh token ?
**R:** Actuellement pas de refresh token. Le JWT expire après 24h. L'utilisateur doit se reconnecter.

---

**Version:** 2.0.0  
**Dernière mise à jour:** 12 Décembre 2025  
**Auteur:** UbuntuAirLab Team
