# Architecture Technique - UbuntuAirLab Backend

## Vue d'Ensemble

UbuntuAirLab Backend est un systeme de gestion aeroportuaire intelligent base sur une architecture moderne en couches avec patterns asynchrones. Le systeme gere l'aeroport international Gnassingbe Eyadema (DXXX/LFW) a Lome, Togo.

## Patterns Architecturaux

### 1. Repository Pattern

Separation claire entre la logique d'acces aux donnees et la logique metier.

**Localisation**: app/repositories/

**Repositories implementes**:
- FlightRepository: Operations CRUD sur les vols
- ParkingSpotRepository: Gestion des places de parking
- ParkingAllocationRepository: Allocations et disponibilites
- UserRepository: Gestion des utilisateurs
- NotificationRepository: Systeme d'alertes
- AIPredictionRepository: Historique des predictions

**Avantages**:
- Testabilite accrue (mock facile)
- Reutilisation du code
- Changement de source de donnees facilite
- Separation des preoccupations

**Exemple**:
```python
class FlightRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_icao24(self, icao24: str) -> Optional[Flight]:
        result = await self.db.execute(
            select(Flight).where(Flight.icao24 == icao24)
        )
        return result.scalar_one_or_none()
    
    async def list_flights(
        self, 
        skip: int = 0, 
        limit: int = 50,
        flight_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> Tuple[List[Flight], int]:
        # Implementation avec filtres
        pass
```

### 2. Service Layer Pattern

Encapsulation de la logique metier complexe dans des services dedies.

**Localisation**: app/services/

**Services metier** (app/services/business/):
- ParkingService: Algorithme d'allocation des places
  - Allocation optimale selon type d'avion
  - Gestion overflow civil vers militaire
  - Rappel automatique civil
  - Detection de conflits
- TrafficStatsService: Analytique temps reel
  - Statistiques de trafic horaire
  - Tendances journalieres
  - Metriques par compagnie

**Services externes** (app/services/external/):
- OpenSkyClient: Integration OAuth2 OpenSky Network
  - Gestion token automatique
  - Rate limiting
  - Retry avec backoff exponentiel
- AviationStackClient: API historique et future
  - Vols futurs (>7 jours)
  - Historique (3 mois)
  - Timetables journaliers
- MLAPIClient: Predictions IA Hugging Face
  - Endpoint unifie /predict
  - 3 modeles (ETA, occupation, conflits)
  - Cache Redis integre

**Services ML** (app/services/ml/):
- PredictionService: Orchestration des predictions
  - Enrichissement des donnees
  - Appel API ML
  - Stockage historique

**Services notifications** (app/services/notifications/):
- NotificationService: Systeme d'alertes
  - 6 types de notifications
  - 3 niveaux de severite
  - Persistance database

**Services orchestration** (app/services/orchestration/):
- SchedulerService: Gestion APScheduler
  - Synchronisation vols (5 min)
  - Rappel civil (2 min)
  - Job status monitoring
- PipelineOrchestrator: Coordination workflow
  - Pipeline de synchronisation
  - Traitement par lots (10 vols)
  - Gestion erreurs

### 3. Dependency Injection

Utilisation du systeme Depends() de FastAPI pour injection de dependances.

**Localisation**: app/api/v1/endpoints/

**Dependances principales**:
```python
from app.database import get_db
from app.api.v1.endpoints.auth import get_current_active_user

@router.get("/flights")
async def list_flights(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    flight_type: Optional[str] = None
):
    flight_repo = FlightRepository(db)
    flights = await flight_repo.list_flights(flight_type=flight_type)
    return flights
```

**Avantages**:
- Testabilite (injection de mocks)
- Gestion automatique du cycle de vie des objets
- Code declaratif et lisible
- Separation des preoccupations

### 4. Singleton Pattern

Application aux clients API externes pour reutilisation de connexions.

**Implementation**:
```python
from functools import lru_cache

@lru_cache()
def get_opensky_client() -> OpenSkyClient:
    return OpenSkyClient()

@lru_cache()
def get_ml_client() -> MLAPIClient:
    return MLAPIClient()
```

**Avantages**:
- Reutilisation des connexions HTTP
- Token OAuth2 partage
- Reduction overhead creation objets

### 5. Async/Await Throughout

Stack completement asynchrone pour scalabilite maximale.

**Composants asynchrones**:
- FastAPI endpoints (async def)
- SQLAlchemy operations (AsyncSession, asyncpg)
- HTTP clients (httpx AsyncClient)
- APScheduler (AsyncIOScheduler)
- Redis client (aioredis)

**Avantages**:
- Gestion efficace de milliers de requetes concurrentes
- Non-blocage sur I/O (DB, API externes)
- Meilleure utilisation des ressources CPU

## Schema de Base de Donnees

### Tables Principales

#### 1. flights

Table centrale de suivi des vols.

```sql
CREATE TABLE flights (
    icao24 VARCHAR(6) PRIMARY KEY,
    callsign VARCHAR(10),
    origin_country VARCHAR(100),
    first_seen INTEGER,
    last_seen INTEGER,
    est_departure_time INTEGER,
    est_arrival_time INTEGER,
    departure_airport VARCHAR(4),
    arrival_airport VARCHAR(4),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    altitude DOUBLE PRECISION,
    velocity DOUBLE PRECISION,
    heading DOUBLE PRECISION,
    vertical_rate DOUBLE PRECISION,
    flight_type VARCHAR(20) CHECK (flight_type IN ('arrival', 'departure')),
    status VARCHAR(20) CHECK (status IN ('scheduled', 'active', 'completed', 'cancelled')),
    predicted_eta TIMESTAMP,
    predicted_etd TIMESTAMP,
    predicted_occupation_minutes INTEGER,
    predicted_conflict_risk DOUBLE PRECISION,
    assigned_parking VARCHAR(10) REFERENCES parking_spots(spot_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_flights_status_type ON flights(status, flight_type);
CREATE INDEX idx_flights_airports ON flights(departure_airport, arrival_airport);
CREATE INDEX idx_flights_times ON flights(est_arrival_time, est_departure_time);
```

**Cardinalite**: ~500-1000 vols actifs, historique complet

#### 2. parking_spots

Places de parking physiques.

```sql
CREATE TYPE spot_type AS ENUM ('civil', 'military');
CREATE TYPE spot_status AS ENUM ('available', 'occupied', 'reserved', 'maintenance');
CREATE TYPE aircraft_size_category AS ENUM ('small', 'medium', 'large');

CREATE TABLE parking_spots (
    spot_id VARCHAR(10) PRIMARY KEY,
    spot_number INTEGER NOT NULL,
    spot_type spot_type NOT NULL,
    status spot_status DEFAULT 'available',
    aircraft_size_capacity aircraft_size_category NOT NULL,
    has_jetway BOOLEAN DEFAULT FALSE,
    distance_to_terminal INTEGER,
    admin_configurable BOOLEAN DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_parking_type_status ON parking_spots(spot_type, status);
```

**Configuration initiale**: 17 places (13 civiles + 4 militaires)

#### 3. parking_allocations

Historique et allocations actives.

```sql
CREATE TABLE parking_allocations (
    allocation_id SERIAL PRIMARY KEY,
    flight_icao24 VARCHAR(6) REFERENCES flights(icao24),
    spot_id VARCHAR(10) REFERENCES parking_spots(spot_id),
    allocated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    predicted_duration_minutes INTEGER,
    predicted_end_time TIMESTAMP,
    actual_start_time TIMESTAMP,
    actual_end_time TIMESTAMP,
    actual_duration_minutes INTEGER,
    overflow_to_military BOOLEAN DEFAULT FALSE,
    overflow_reason TEXT,
    conflict_detected BOOLEAN DEFAULT FALSE,
    conflict_resolved BOOLEAN DEFAULT FALSE,
    conflict_resolution_time TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_allocations_active ON parking_allocations(is_active);
CREATE INDEX idx_allocations_flight ON parking_allocations(flight_icao24);
CREATE INDEX idx_allocations_spot ON parking_allocations(spot_id);
```

#### 4. users

Authentification et autorisation.

```sql
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    role VARCHAR(20) CHECK (role IN ('admin', 'user')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);
```

#### 5. ai_predictions

Historique predictions ML.

```sql
CREATE TYPE prediction_model AS ENUM ('eta', 'occupation', 'conflit');

CREATE TABLE ai_predictions (
    prediction_id SERIAL PRIMARY KEY,
    flight_icao24 VARCHAR(6) REFERENCES flights(icao24),
    model_type prediction_model NOT NULL,
    model_version VARCHAR(20),
    input_data JSONB NOT NULL,
    prediction_result JSONB NOT NULL,
    confidence_score DOUBLE PRECISION,
    prediction_accurate BOOLEAN,
    actual_outcome JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_predictions_flight ON ai_predictions(flight_icao24);
CREATE INDEX idx_predictions_model ON ai_predictions(model_type);
```

#### 6. notifications

Systeme d'alertes.

```sql
CREATE TYPE notification_type AS ENUM (
    'conflit', 'saturation', 'rappel', 'overflow', 'delay', 'parking_freed'
);
CREATE TYPE notification_severity AS ENUM ('info', 'warning', 'critical');

CREATE TABLE notifications (
    notification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER REFERENCES users(user_id),
    type notification_type NOT NULL,
    severity notification_severity NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP
);

CREATE INDEX idx_notifications_user_unread ON notifications(user_id, is_read);
CREATE INDEX idx_notifications_severity ON notifications(severity);
```

#### 7. aircraft_turnaround_rules

Regles de temps de rotation.

```sql
CREATE TABLE aircraft_turnaround_rules (
    rule_id SERIAL PRIMARY KEY,
    aircraft_type VARCHAR(20) UNIQUE NOT NULL,
    min_turnaround_minutes INTEGER NOT NULL,
    typical_turnaround_minutes INTEGER NOT NULL,
    max_turnaround_minutes INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Relations

```
flights 1:1 -------- 0:1 parking_allocations
  |                        |
  | (assigned_parking)     | (spot_id)
  |                        |
  V                        V
parking_spots <---- 1:N parking_allocations

flights 1:N -------- ai_predictions

users 1:N ---------- notifications
```

### Migrations

Gerees via Alembic (app/alembic/versions/):

1. 001_initial_schema.py - Tables de base
2. 002_add_flight_parking_fk.py - Relation flight-parking
3. 003_seed_parking_spots.py - 17 places initiales
4. 004_add_conflict_tracking.py - Detection conflits
5. 005_add_timestamps.py - Audit trail
6. 006_add_enum_types.py - Types PostgreSQL
7. 007_add_military_spots.py - Zone militaire

## Integrations Externes

### 1. OpenSky Network API

**URL Base**: https://opensky-network.org/api

**Authentification**: OAuth2 Client Credentials Flow

**Configuration**:
```python
OPENSKY_CLIENT_ID=email@example.com-api-client
OPENSKY_CLIENT_SECRET=secret_key
OPENSKY_TOKEN_URL=https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token
```

**Endpoints utilises**:
- GET /flights/arrival: Vols en arrivee pour aeroport
- GET /flights/departure: Vols en depart pour aeroport

**Parametres**:
- airport: Code ICAO (DXXX)
- begin: Unix timestamp debut
- end: Unix timestamp fin

**Rate Limiting**:
- Headers: X-Rate-Limit-Remaining, X-Rate-Limit-Reset
- Gestion automatique via client
- Credits quotidiens surveilles

**Gestion Token**:
```python
class OpenSkyClient:
    async def _get_access_token(self) -> str:
        if self._token and not self._is_token_expired():
            return self._token
        
        # Obtenir nouveau token
        response = await self.client.post(
            self.token_url,
            data={
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }
        )
        token_data = response.json()
        self._token = token_data['access_token']
        self._token_expiry = datetime.now() + timedelta(
            seconds=token_data['expires_in'] - 60
        )
        return self._token
```

### 2. AviationStack API

**URL Base**: https://api.aviationstack.com/v1

**Authentification**: API Access Key

**Configuration**:
```python
AVIATIONSTACK_ACCESS_KEY=votre_cle_api
```

**Endpoints utilises**:
- GET /flights: Vols temps reel
- GET /timetables: Horaires journaliers
- GET /flights/future: Vols planifies (>7 jours)

**Rate Limits**:
- Plan Free: 1 req/60s pour timetables et future
- Plan Paid: 1 req/10s

**Exemple requete**:
```python
params = {
    'access_key': self.access_key,
    'arr_iata': 'LFW',
    'type': 'arrival',
    'flight_date': '2025-12-20'
}
response = await self.client.get('/flights', params=params)
```

### 3. Hugging Face ML API

**URL Base**: https://tagba-ubuntuairlab.hf.space

**Space**: TAGBA/ubuntuairlab

**Modeles**:

1. **Modele 1 - ETA/ETD (XGBoost)**
   - Input: 26 parametres (vitesse, altitude, meteo, trafic, etc.)
   - Output: eta_ajuste, etd_ajuste, proba_delay_15, proba_delay_30

2. **Modele 2 - Occupation (LightGBM)**
   - Input: Type avion, historique, meteo, trafic
   - Output: temps_occupation_minutes, intervalle_confiance

3. **Modele 3 - Conflits (XGBoost)**
   - Input: Occupation actuelle, trafic, previsions
   - Output: risque_conflit, decision_recommandee, explication

**Endpoint unifie**: POST /predict

**Exemple requete**:
```python
request_data = {
    "callsign": "AF1234",
    "icao24": "3944ef",
    "vitesse_actuelle": 250.0,
    "altitude": 3500.0,
    "distance_piste": 15.5,
    "type_vol": 0,
    # ... 22 autres parametres (auto-remplis si absents)
}

response = await ml_client.predict(request_data)
```

**Reponse**:
```json
{
  "model_1_eta": {
    "eta_ajuste": 36.37,
    "proba_delay_15": 0.23,
    "proba_delay_30": 0.08
  },
  "model_2_occupation": {
    "temps_occupation_minutes": 52.99,
    "temps_min_minutes": 42.5,
    "temps_max_minutes": 63.5
  },
  "model_3_conflict": {
    "risque_conflit": 0,
    "proba_conflit": 0.12,
    "decision_recommandee": 0,
    "decision_label": "Accepter normalement"
  },
  "metadata": {
    "timestamp": "2025-12-12T10:45:23Z",
    "pipeline_version": "1.0.0"
  }
}
```

**Cache Redis**:
- TTL: 300 secondes (5 minutes)
- Cle: prediction:{icao24}
- Invalidation: Nouveau vol detecte

**Health Check**: GET /health

## Flux de Donnees

### 1. Pipeline de Synchronisation

```
APScheduler (toutes les 5 min)
    |
    v
SchedulerService.trigger_sync()
    |
    v
PipelineOrchestrator.run_sync_pipeline()
    |
    +-- OpenSkyClient.get_arrivals(airport, begin, end)
    |       |
    |       v
    |   Batch de 10 vols en parallele
    |       |
    |       v
    +-- Pour chaque vol:
            |
            +-- FlightRepository.create_or_update()
            |
            +-- ParkingService.allocate_if_needed()
            |       |
            |       v
            |   MLAPIClient.predict() -> Cache Redis
            |       |
            |       v
            |   Algorithme allocation optimale
            |       |
            |       v
            |   ParkingAllocationRepository.create()
            |
            +-- NotificationService.create_if_needed()
```

### 2. Requete API Prediction

```
Client Frontend
    |
    v
POST /api/v1/predictions/predict
    |
    v
PredictionService.predict()
    |
    +-- Verifier cache Redis
    |   |
    |   +-- Hit -> Retourner cached
    |   |
    |   +-- Miss -> Continuer
    |
    +-- Enrichir donnees
    |   |
    |   +-- TrafficStatsService.get_stats()
    |   |
    |   +-- WeatherService.get_current()
    |   |
    |   +-- FlightRepository.get_historical()
    |
    +-- MLAPIClient.predict(enriched_data)
    |   |
    |   v
    |   Hugging Face API
    |   |
    |   v
    |   3 modeles -> Predictions
    |
    +-- Cache dans Redis (5 min)
    |
    +-- AIPredictionRepository.save_history()
    |
    v
Retourner reponse
```

### 3. Allocation Parking

```
Nouveau vol detecte
    |
    v
ParkingService.allocate_spot()
    |
    +-- Verifier si deja alloue
    |   |
    |   +-- Oui -> Retourner allocation existante
    |   |
    |   +-- Non -> Continuer
    |
    +-- Obtenir prediction occupation ML
    |
    +-- Calculer compatibilite
    |   |
    |   +-- Taille avion vs capacite place
    |   |
    |   +-- Preference jetway
    |   |
    |   +-- Distance terminal
    |
    +-- Chercher place civile disponible
    |   |
    |   +-- Trouvee -> Allouer
    |   |
    |   +-- Non trouvee -> Overflow militaire
    |
    +-- Creer allocation dans DB
    |
    +-- Creer notification si overflow
    |
    v
Retourner resultat
```

### 4. Rappel Civil Automatique

```
APScheduler (toutes les 2 min)
    |
    v
SchedulerService.trigger_civil_recall()
    |
    v
ParkingService.recall_to_civil()
    |
    +-- Trouver allocations militaires actives
    |   (overflow_to_military = TRUE, actual_end_time = NULL)
    |
    +-- Pour chaque allocation:
        |
        +-- Verifier si place civile disponible
        |   |
        |   +-- Compatible taille avion
        |   |
        |   +-- Status = available
        |
        +-- Si disponible:
            |
            +-- Terminer allocation militaire
            |
            +-- Creer nouvelle allocation civile
            |
            +-- Mettre a jour flight.assigned_parking
            |
            +-- NotificationService.create(RAPPEL)
```

## Decisions de Conception

### 1. Pourquoi AsyncIO partout?

**Raison**: Gestion efficace des I/O multiples (DB, APIs externes, cache)

**Impact**:
- 10x plus de requetes concurrentes que synchrone
- Temps de reponse reduit (pas de blocage)
- Meilleure utilisation CPU (event loop)

**Trade-offs**:
- Complexite accrue du code
- Debugging plus difficile
- Necessite connaissances async/await

### 2. Pourquoi Repository Pattern?

**Raison**: Separation logique metier et acces donnees

**Impact**:
- Tests unitaires faciles (mock repository)
- Changement de DB facilite
- Code reutilisable

**Trade-offs**:
- Plus de fichiers a maintenir
- Boilerplate code
- Courbe d'apprentissage

### 3. Pourquoi Cache Redis pour predictions ML?

**Raison**: API ML peut prendre 10-30s (cold start Hugging Face)

**Impact**:
- Temps de reponse < 100ms (cache hit)
- Reduction charge API ML
- Meilleure experience utilisateur

**Trade-offs**:
- Donnees potentiellement obsoletes (5 min max)
- Infrastructure additionnelle (Redis)
- Gestion invalidation cache

### 4. Pourquoi 17 places de parking?

**Raison**: Configuration reelle aeroport Lome

**Distribution**:
- 13 civiles (76%)
- 4 militaires (24%)

**Logique overflow**:
- Saturation civile -> Militaire temporaire
- Rappel automatique des que civil libre
- Notifications pour visibilite

### 5. Pourquoi APScheduler au lieu de Celery?

**Raison**: Simplicite pour cas d'usage limite

**Avantages**:
- Pas de broker externe (RabbitMQ/Redis)
- Configuration simple
- Integre directement dans l'app

**Limitations**:
- Pas de distribution multi-workers
- Pas de retry sophistique
- Pas de monitoring avance

**Quand migrer vers Celery**:
- Plus de 20 jobs concurrents
- Besoin de distribution
- Workflows complexes

### 6. Pourquoi 3 modeles ML separes?

**Raison**: Specialisation par tache

**Model 1 (ETA/ETD)**:
- Regression temporelle
- Features: Meteo, trafic, historique compagnie
- Optimise pour precision temporelle

**Model 2 (Occupation)**:
- Regression duree
- Features: Type avion, passagers, operations
- Optimise pour planification

**Model 3 (Conflits)**:
- Classification binaire
- Features: Occupation actuelle, previsions, contraintes
- Optimise pour detection proactive

**Alternative rejetee**: Model unique multi-taches
- Moins de precision par tache
- Plus difficile a entrainer
- Moins de flexibilite

## Performance et Scalabilite

### Configuration Actuelle

**Base de donnees**:
- Pool size: 20 connexions
- Max overflow: 10 connexions
- Total: 30 connexions max

**Serveur ASGI**:
- 4 workers Uvicorn en production
- 1 worker en developpement

**Cache Redis**:
- TTL predictions: 300s
- TTL sessions: 1800s
- Eviction policy: allkeys-lru

### Metriques Cibles

**API Response Time**:
- P50: < 100ms
- P95: < 500ms
- P99: < 1000ms

**ML Predictions**:
- Cache hit: < 50ms
- Cache miss: < 5000ms (API ML)

**Database Queries**:
- Simple SELECT: < 10ms
- JOIN complexe: < 50ms
- Batch operations: < 200ms

**Synchronisation**:
- 10 vols en parallele: < 30s
- 50 vols: < 2min

### Limites et Scalabilite

**Limites actuelles**:
- 1000 vols actifs simultanes
- 100 predictions par minute
- 500 requetes API par minute

**Bottlenecks potentiels**:
1. API ML Hugging Face (cold start 30s)
2. OpenSky rate limiting (credits quotidiens)
3. Database pool saturation (30 connexions)

**Strategies de scaling**:

**Horizontal**:
- Load balancer devant N instances backend
- Database read replicas
- Redis Cluster pour cache distribue

**Vertical**:
- Augmenter workers Uvicorn
- Augmenter pool size DB
- Optimiser queries (indexes, explain analyze)

**Optimisations**:
- Materialized views pour stats
- Partitioning table flights par date
- Connection pooling externe (PgBouncer)

## Securite

### Authentification JWT

**Algorithme**: HS256

**Secret**: Minimum 32 caracteres (variable env)

**Expiration**: 60 minutes configurable

**Claims**:
```json
{
  "sub": "username",
  "exp": 1702345678,
  "iat": 1702342078
}
```

**Stockage token**: localStorage frontend

**Refresh**: Pas de refresh token (re-login requis)

### Hashage Mots de Passe

**Algorithme**: bcrypt

**Cost factor**: 12 (par defaut)

**Sel**: Automatique par bcrypt

**Verification**:
```python
def verify_password(plain_password: str, hashed: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode('utf-8'), 
        hashed.encode('utf-8')
    )
```

### CORS

**Configuration production**:
```python
CORS_ORIGINS=["https://air-lab.bestwebapp.tech","https://bestwebapp.tech"]
```

**Methodes autorisees**: GET, POST, PUT, DELETE, PATCH, OPTIONS

**Headers autorises**: Authorization, Content-Type

### SQL Injection Protection

**ORM**: SQLAlchemy avec parametres binds

**Exemple securise**:
```python
# Securise (parametres binds)
result = await db.execute(
    select(Flight).where(Flight.icao24 == icao24)
)

# Dangereux (jamais utilise)
query = f"SELECT * FROM flights WHERE icao24 = '{icao24}'"
```

### Secrets Management

**Variables d'environnement**: Tous les secrets

**Fichiers gitignores**: .env, .env.local, .env.production

**Azure Key Vault**: Non utilise (VM standalone)

**Rotation secrets**: Manuelle

## Monitoring

### Metriques Prometheus

**Localisation**: app/core/metrics.py

**Metriques HTTP**:
- http_requests_total{method, endpoint, status}
- http_request_duration_seconds{method, endpoint}
- http_requests_in_progress{method, endpoint}

**Metriques OpenSky API**:
- opensky_api_calls_total{endpoint, status}
- opensky_rate_limit_remaining
- opensky_rate_limit_reset_timestamp

**Metriques ML**:
- ml_predictions_total{model, cache_status}
- ml_prediction_duration_seconds{model}
- ml_prediction_errors_total{model, error_type}

**Metriques Sync**:
- flight_sync_jobs_total{status}
- flight_sync_duration_seconds
- flights_processed_total{flight_type, status}

**Metriques Parking**:
- parking_spots_total{type}
- parking_spots_available{type}
- parking_allocations_total{type, overflow}

**Metriques App**:
- ubuntuairlab_backend_info{version, build}

### Logging Structure

**Format production**: JSON

**Champs**:
- timestamp: ISO 8601
- level: DEBUG, INFO, WARNING, ERROR, CRITICAL
- logger: Module name
- message: Message texte
- context: Donnees additionnelles (dict)

**Exemple**:
```json
{
  "timestamp": "2025-12-12T10:30:45.123Z",
  "level": "INFO",
  "logger": "app.services.orchestration.scheduler",
  "message": "Flight sync completed",
  "context": {
    "flights_processed": 45,
    "duration_seconds": 12.5,
    "errors": 0
  }
}
```

### Health Checks

**Endpoint**: GET /health

**Verifications**:
- Database connectivity (pg_isready)
- Redis connectivity (PING)
- Scheduler status (running/stopped)

**Reponse**:
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "scheduler": "running",
  "next_sync": "2025-12-12T10:35:00Z"
}
```

## Diagrammes

### Diagramme de Deploiement

```
                         Internet
                             |
                             |
                    [Nginx Reverse Proxy]
                    (Port 80/443 SSL)
                             |
                             |
              +--------------+---------------+
              |                              |
    [Backend FastAPI]              [Static Frontend]
    (Port 8000)                    (Served by Nginx)
    4 workers Uvicorn
              |
              |
    +---------+---------+
    |                   |
[PostgreSQL]        [Redis]
(Port 5433)        (Port 6379)
    |
    |
[Persistent Volume]

External APIs:
- OpenSky Network (OAuth2)
- AviationStack
- Hugging Face ML
```

### Diagramme de Composants

```
┌─────────────────────────────────────────────────┐
│              FastAPI Application                 │
│                                                  │
│  ┌───────────────────────────────────────────┐  │
│  │         API Layer (Endpoints)             │  │
│  │  /auth  /flights  /parking  /predictions │  │
│  └───────────────────────────────────────────┘  │
│                      ↓                           │
│  ┌───────────────────────────────────────────┐  │
│  │          Service Layer                     │  │
│  │  - ParkingService                         │  │
│  │  - PredictionService                      │  │
│  │  - NotificationService                    │  │
│  │  - SchedulerService                       │  │
│  └───────────────────────────────────────────┘  │
│                      ↓                           │
│  ┌───────────────────────────────────────────┐  │
│  │       Repository Layer                     │  │
│  │  - FlightRepository                       │  │
│  │  - ParkingRepository                      │  │
│  │  - UserRepository                         │  │
│  └───────────────────────────────────────────┘  │
│                      ↓                           │
│  ┌───────────────────────────────────────────┐  │
│  │         Database Layer                     │  │
│  │  SQLAlchemy ORM + AsyncPG                 │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
            ↓                        ↓
      [PostgreSQL]                [Redis]
      
External Clients:
- OpenSkyClient → OpenSky API
- AviationStackClient → AviationStack API
- MLAPIClient → Hugging Face ML
```

### Flux Utilisateur - Allocation Parking

```
[Vol detecte par sync]
         |
         v
[Verifier allocation existante]
         |
    Non  |  Oui
         |   |
         v   v
[Appel ML API] -> [Retourner existante]
         |
         v
[Algorithme allocation]
         |
    +----+----+
    |         |
[Civil]  [Militaire]
 dispo    (overflow)
    |         |
    v         v
[Allouer] [Allouer + Notification]
    |         |
    +----+----+
         |
         v
[Enregistrer DB]
         |
         v
   [Terminer]
```

## Conclusion

Cette architecture assure:
- Scalabilite horizontale et verticale
- Maintenabilite via separation des couches
- Testabilite grace au dependency injection
- Performance via async et cache
- Observabilite complete (logs, metriques, traces)
- Securite par design (JWT, bcrypt, CORS)

Pour questions ou ameliorations, consulter l'equipe UbuntuAirLab.
