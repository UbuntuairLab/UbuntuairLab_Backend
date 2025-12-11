# 📘 Guide d'Intégration Frontend - UbuntuAirLab API

## 🌐 Vue d'ensemble

L'API UbuntuAirLab est une API REST complète pour la gestion aéroportuaire avec intelligence artificielle. Ce guide vous permettra d'intégrer rapidement l'API avec votre application frontend.

## 🔗 URLs de Base

### Développement Local
```
Base URL: http://localhost:8000
API: http://localhost:8000/api/v1
Docs: http://localhost:8000/docs
Metrics: http://localhost:8000/metrics
```

### Production Azure
```
Base URL: https://ubuntuairlab-api.azurewebsites.net
API: https://ubuntuairlab-api.azurewebsites.net/api/v1
```

## 🔐 Authentification

L'API utilise JWT (JSON Web Tokens) pour l'authentification.

### 1. Login (Obtenir un Token)

**Endpoint:** `POST /api/v1/auth/login`

**Request:**
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "password123"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### 2. Utiliser le Token

Ajoutez le token à chaque requête dans le header `Authorization`:

```http
GET /api/v1/flights
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 3. Vérifier l'Utilisateur Actuel

**Endpoint:** `GET /api/v1/auth/me`

**Response:**
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@ubuntuairlab.com",
  "full_name": "Administrator",
  "is_active": true,
  "created_at": "2025-12-11T10:00:00Z"
}
```

---

## ✈️ Endpoints Principaux

### 📊 Dashboard - Statistiques

**Endpoint:** `GET /api/v1/dashboard/stats`

**Authentification:** Requise

**Response:**
```json
{
  "parking": {
    "total_spots": 20,
    "available_spots": 12,
    "occupied_spots": 8,
    "civil_spots": 16,
    "military_spots": 4,
    "civil_available": 10,
    "military_available": 2,
    "occupation_rate": 0.4
  },
  "flights": {
    "approaching_count": 3,
    "departing_count": 2,
    "today_count": 45,
    "active_count": 8
  },
  "notifications": {
    "unread_count": 5,
    "critical_count": 2
  }
}
```

### 🛫 Flights - Liste des Vols

**Endpoint:** `GET /api/v1/flights`

**Query Parameters:**
- `status` (optional): `scheduled`, `active`, `completed`, `cancelled`
- `flight_type` (optional): `arrival`, `departure`
- `skip` (optional, default: 0): Pagination offset
- `limit` (optional, default: 100, max: 1000): Nombre de résultats

**Exemple:**
```http
GET /api/v1/flights?status=active&flight_type=arrival&limit=20
Authorization: Bearer <token>
```

**Response:**
```json
{
  "items": [
    {
      "icao24": "abc123",
      "callsign": "AFR1234",
      "origin_country": "France",
      "longitude": 1.2345,
      "latitude": 6.7890,
      "baro_altitude": 10000.0,
      "velocity": 450.0,
      "true_track": 180.0,
      "vertical_rate": -5.0,
      "on_ground": false,
      "squawk": "1200",
      "spi": false,
      "position_source": 0,
      "category": 3,
      "last_seen": 1702307200,
      "predicted_eta": "2025-12-11T18:30:00Z",
      "predicted_etd": null,
      "predicted_occupation_minutes": 45,
      "status": "active",
      "flight_type": "arrival",
      "parking_spot_id": null,
      "created_at": "2025-12-11T17:00:00Z",
      "updated_at": "2025-12-11T17:45:00Z"
    }
  ],
  "total": 8,
  "skip": 0,
  "limit": 20
}
```

### 🛬 Flight Detail

**Endpoint:** `GET /api/v1/flights/{icao24}`

**Response:**
```json
{
  "icao24": "abc123",
  "callsign": "AFR1234",
  "origin_country": "France",
  "status": "active",
  "flight_type": "arrival",
  "predicted_eta": "2025-12-11T18:30:00Z",
  "predicted_occupation_minutes": 45,
  "parking_allocation": {
    "id": 42,
    "spot_id": "C-01",
    "spot_type": "civil",
    "aircraft_size": "medium",
    "predicted_start_time": "2025-12-11T18:30:00Z",
    "predicted_end_time": "2025-12-11T19:15:00Z",
    "actual_start_time": null,
    "actual_end_time": null
  }
}
```

### 🅿️ Parking - Disponibilité

**Endpoint:** `GET /api/v1/parking/availability`

**Response:**
```json
{
  "total_spots": 20,
  "available_spots": 12,
  "occupied_spots": 8,
  "civil": {
    "total": 16,
    "available": 10,
    "occupied": 6
  },
  "military": {
    "total": 4,
    "available": 2,
    "occupied": 2
  },
  "by_size": {
    "small": {
      "total": 6,
      "available": 4
    },
    "medium": {
      "total": 10,
      "available": 6
    },
    "large": {
      "total": 4,
      "available": 2
    }
  }
}
```

### 🅿️ Parking - Liste des Spots

**Endpoint:** `GET /api/v1/parking/spots`

**Query Parameters:**
- `spot_type` (optional): `civil`, `military`
- `status` (optional): `available`, `occupied`, `reserved`, `maintenance`
- `aircraft_size` (optional): `small`, `medium`, `large`

**Response:**
```json
[
  {
    "id": "C-01",
    "spot_type": "civil",
    "status": "available",
    "aircraft_size_category": "medium",
    "latitude": 6.1656,
    "longitude": 1.2545,
    "created_at": "2025-12-10T10:00:00Z",
    "updated_at": "2025-12-11T17:30:00Z"
  }
]
```

### 🎯 Assignment Automatique de Parking

**Endpoint:** `POST /api/v1/parking/assign`

**Request:**
```json
{
  "icao24": "abc123",
  "aircraft_size": "medium",
  "spot_type": "civil"
}
```

**Response (200 OK):**
```json
{
  "allocation_id": 42,
  "spot_id": "C-01",
  "flight_icao24": "abc123",
  "predicted_start_time": "2025-12-11T18:30:00Z",
  "predicted_end_time": "2025-12-11T19:15:00Z",
  "message": "Parking spot C-01 assigned successfully"
}
```

### 🚁 Transfer Militaire (Overflow)

**Endpoint:** `POST /api/v1/parking/military-transfer`

**Description:** Transfert automatique des avions civils vers le parking militaire quand le parking civil est plein.

**Response:**
```json
{
  "success": true,
  "transferred_count": 3,
  "transfers": [
    {
      "flight_icao24": "xyz789",
      "from_spot": "C-08",
      "to_spot": "M-02",
      "reason": "civil_overflow"
    }
  ]
}
```

### 🔄 Recall Civil (Retour au Parking Civil)

**Endpoint:** `POST /api/v1/parking/civil-recall`

**Description:** Rappel des avions civils depuis le parking militaire vers le parking civil quand des places se libèrent.

**Response:**
```json
{
  "success": true,
  "recalled_count": 2,
  "recalls": [
    {
      "flight_icao24": "xyz789",
      "from_spot": "M-02",
      "to_spot": "C-05",
      "reason": "civil_space_available"
    }
  ]
}
```

### 🤖 Prédiction ML - Vol Individuel

**Endpoint:** `POST /api/v1/predictions/predict`

**Request (minimal - auto-enrichissement depuis DB):**
```json
{
  "icao24": "abc123"
}
```

**Request (complet - override manuel):**
```json
{
  "icao24": "abc123",
  "trafic_approche": 5,
  "occupation_tarmac": 0.6,
  "spots_disponibles_civil": 8,
  "temperature": 28.5,
  "vitesse_vent": 15.0,
  "visibilite": 10000,
  "conditions_meteo": "clair",
  "retard_historique_compagnie": 12.5,
  "temps_occupation_moyen_compagnie": 45.0
}
```

**Response:**
```json
{
  "icao24": "abc123",
  "predicted_eta_minutes": 35,
  "predicted_occupation_minutes": 48,
  "confidence_score": 0.87,
  "model_version": "v1.2.3",
  "prediction_timestamp": "2025-12-11T17:45:00Z",
  "input_data": {
    "trafic_approche": 5,
    "occupation_tarmac": 0.6,
    "temperature": 28.5
  }
}
```

### 📈 Prédictions en Lot

**Endpoint:** `POST /api/v1/predictions/batch`

**Request:**
```json
{
  "icao24_list": ["abc123", "def456", "ghi789"]
}
```

**Response:**
```json
{
  "predictions": [
    {
      "icao24": "abc123",
      "predicted_eta_minutes": 35,
      "predicted_occupation_minutes": 48,
      "confidence_score": 0.87
    },
    {
      "icao24": "def456",
      "predicted_eta_minutes": 42,
      "predicted_occupation_minutes": 52,
      "confidence_score": 0.91
    }
  ],
  "total_processed": 3,
  "total_succeeded": 2,
  "total_failed": 1,
  "errors": [
    {
      "icao24": "ghi789",
      "error": "Flight not found"
    }
  ]
}
```

### 🔔 Notifications - Liste

**Endpoint:** `GET /api/v1/notifications/notifications`

**Query Parameters:**
- `severity` (optional): `info`, `warning`, `critical`
- `is_read` (optional): `true`, `false`
- `skip` (optional, default: 0)
- `limit` (optional, default: 50)

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "title": "Parking presque plein",
      "message": "Occupation à 85% - 3 places restantes",
      "severity": "warning",
      "is_read": false,
      "metadata": {
        "available_spots": 3,
        "occupation_rate": 0.85
      },
      "created_at": "2025-12-11T17:40:00Z"
    }
  ],
  "total": 5,
  "unread_count": 3
}
```

### 🔔 Marquer Notification comme Lue

**Endpoint:** `POST /api/v1/notifications/notifications/{notification_id}/acknowledge`

**Response:**
```json
{
  "id": 1,
  "is_read": true,
  "read_at": "2025-12-11T17:50:00Z"
}
```

### 🔄 Synchronisation - Trigger Manuel

**Endpoint:** `POST /api/v1/sync/trigger`

**Description:** Déclenche manuellement une synchronisation avec OpenSky Network.

**Response:**
```json
{
  "status": "success",
  "message": "Flight synchronization triggered",
  "timestamp": "2025-12-11T17:50:00Z"
}
```

### 🔄 Statut du Scheduler

**Endpoint:** `GET /api/v1/sync/status`

**Response:**
```json
{
  "scheduler_running": true,
  "next_sync_at": "2025-12-11T18:00:00Z",
  "last_sync_at": "2025-12-11T17:55:00Z",
  "sync_interval_minutes": 5,
  "jobs": [
    {
      "id": "flight_sync",
      "name": "Flight Synchronization",
      "next_run_time": "2025-12-11T18:00:00Z"
    },
    {
      "id": "civil_recall",
      "name": "Civil Parking Recall",
      "next_run_time": "2025-12-11T17:57:00Z"
    }
  ]
}
```

---

## 🎨 Exemple d'Intégration Frontend

### React/Next.js avec Axios

```typescript
// lib/api.ts
import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

// Créer une instance Axios
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Intercepteur pour ajouter le token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Intercepteur pour gérer les erreurs 401
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expiré - rediriger vers login
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Services
export const authService = {
  login: async (username: string, password: string) => {
    const response = await apiClient.post('/auth/login', { username, password });
    localStorage.setItem('access_token', response.data.access_token);
    return response.data;
  },
  
  logout: () => {
    localStorage.removeItem('access_token');
  },
  
  getCurrentUser: async () => {
    const response = await apiClient.get('/auth/me');
    return response.data;
  },
};

export const flightService = {
  getFlights: async (params?: {
    status?: string;
    flight_type?: string;
    skip?: number;
    limit?: number;
  }) => {
    const response = await apiClient.get('/flights', { params });
    return response.data;
  },
  
  getFlight: async (icao24: string) => {
    const response = await apiClient.get(`/flights/${icao24}`);
    return response.data;
  },
};

export const dashboardService = {
  getStats: async () => {
    const response = await apiClient.get('/dashboard/stats');
    return response.data;
  },
};

export const parkingService = {
  getAvailability: async () => {
    const response = await apiClient.get('/parking/availability');
    return response.data;
  },
  
  getSpots: async (params?: {
    spot_type?: string;
    status?: string;
  }) => {
    const response = await apiClient.get('/parking/spots', { params });
    return response.data;
  },
  
  assignSpot: async (data: {
    icao24: string;
    aircraft_size: string;
    spot_type: string;
  }) => {
    const response = await apiClient.post('/parking/assign', data);
    return response.data;
  },
};

export const predictionService = {
  predict: async (data: { icao24: string; [key: string]: any }) => {
    const response = await apiClient.post('/predictions/predict', data);
    return response.data;
  },
};
```

### Composant React Exemple

```typescript
// components/Dashboard.tsx
import { useEffect, useState } from 'react';
import { dashboardService } from '@/lib/api';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await dashboardService.getStats();
        setStats(data);
      } catch (error) {
        console.error('Error fetching stats:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
    
    // Refresh every 30 seconds
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div>Loading...</div>;

  return (
    <div className="grid grid-cols-3 gap-4">
      <div className="stat-card">
        <h3>Parking Disponible</h3>
        <p className="text-3xl">{stats?.parking.available_spots}</p>
        <p className="text-sm">sur {stats?.parking.total_spots} spots</p>
      </div>
      
      <div className="stat-card">
        <h3>Vols en Approche</h3>
        <p className="text-3xl">{stats?.flights.approaching_count}</p>
        <p className="text-sm">dans les 30 prochaines minutes</p>
      </div>
      
      <div className="stat-card">
        <h3>Notifications</h3>
        <p className="text-3xl">{stats?.notifications.unread_count}</p>
        <p className="text-sm text-red-500">
          {stats?.notifications.critical_count} critiques
        </p>
      </div>
    </div>
  );
}
```

### Vue.js avec Composition API

```typescript
// composables/useApi.ts
import { ref } from 'vue';

export function useFlights() {
  const flights = ref([]);
  const loading = ref(false);
  const error = ref(null);

  const fetchFlights = async (params = {}) => {
    loading.value = true;
    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/flights?${new URLSearchParams(params)}`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          },
        }
      );
      
      if (!response.ok) throw new Error('Failed to fetch flights');
      
      const data = await response.json();
      flights.value = data.items;
    } catch (e) {
      error.value = e.message;
    } finally {
      loading.value = false;
    }
  };

  return { flights, loading, error, fetchFlights };
}
```

---

## ⚠️ Gestion des Erreurs

L'API renvoie des erreurs HTTP standard avec un format JSON cohérent:

### Format d'Erreur

```json
{
  "detail": "Description de l'erreur"
}
```

### Codes HTTP Principaux

| Code | Signification | Action Frontend |
|------|---------------|-----------------|
| `200` | Succès | Traiter les données |
| `201` | Créé | Ressource créée avec succès |
| `204` | No Content | Opération réussie sans données |
| `400` | Bad Request | Valider les données d'entrée |
| `401` | Unauthorized | Rediriger vers login |
| `403` | Forbidden | Afficher message permissions |
| `404` | Not Found | Ressource introuvable |
| `422` | Validation Error | Afficher erreurs de validation |
| `500` | Server Error | Afficher message erreur générique |

### Exemple de Gestion d'Erreur

```typescript
try {
  const data = await apiClient.post('/parking/assign', assignData);
  // Success
  showNotification('Parking assigné avec succès', 'success');
} catch (error) {
  if (error.response) {
    switch (error.response.status) {
      case 400:
        showNotification(error.response.data.detail, 'error');
        break;
      case 404:
        showNotification('Vol introuvable', 'error');
        break;
      case 422:
        // Validation errors
        const errors = error.response.data.detail;
        showValidationErrors(errors);
        break;
      default:
        showNotification('Erreur serveur', 'error');
    }
  }
}
```

---

## 🔄 Polling et Real-time

### Polling Recommandé

Pour les données en temps réel, utilisez du polling avec ces intervalles:

```typescript
// Dashboard stats - toutes les 30 secondes
setInterval(() => fetchDashboardStats(), 30000);

// Liste des vols - toutes les 60 secondes
setInterval(() => fetchFlights(), 60000);

// Notifications - toutes les 20 secondes
setInterval(() => fetchNotifications(), 20000);
```

### WebSocket (Future Enhancement)

WebSocket sera ajouté dans la v2.0 pour:
- Mises à jour en temps réel des vols
- Notifications push
- Changements de statut parking

---

## 📝 Variables d'Environnement Frontend

Créez un fichier `.env.local`:

```env
# API
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws

# Azure Production
# NEXT_PUBLIC_API_URL=https://ubuntuairlab-api.azurewebsites.net/api/v1

# Features
NEXT_PUBLIC_ENABLE_METRICS=true
NEXT_PUBLIC_ENABLE_NOTIFICATIONS=true
NEXT_PUBLIC_REFRESH_INTERVAL=30000
```

---

## 🧪 Testing avec Postman/Thunder Client

### Collection Postman

Importez cette collection pour tester rapidement l'API:

```json
{
  "info": {
    "name": "UbuntuAirLab API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "auth": {
    "type": "bearer",
    "bearer": [
      {
        "key": "token",
        "value": "{{access_token}}",
        "type": "string"
      }
    ]
  },
  "variable": [
    {
      "key": "base_url",
      "value": "http://localhost:8000/api/v1"
    },
    {
      "key": "access_token",
      "value": ""
    }
  ]
}
```

---

## 📞 Support

- **Documentation Interactive**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **GitHub Issues**: https://github.com/ubuntuairlab/backend/issues

---

**Dernière mise à jour:** 11 Décembre 2025
**Version API:** 1.0.0
