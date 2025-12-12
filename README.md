# UbuntuAirLab Backend - AIGE APRON-SMART

**Système intelligent de gestion de l'aire de stationnement de l'Aéroport International Gnassingbé Eyadéma**

Version 2.0 - Gestion automatisée des parkings avec Intelligence Artificielle

---

## Problématique

L'Aéroport International Gnassingbé Eyadéma (DXXX/LFW) à Lomé, Togo, fait face à plusieurs défis opérationnels critiques dans la gestion quotidienne de son aire de stationnement:

### 1. Attribution Manuelle et Inefficace
- **Processus manual chronophage**: Attribution des 17 postes de stationnement (13 civils + 4 militaires) effectuée manuellement par les contrôleurs au sol
- **Risques d'erreurs humaines**: Décisions prises sous pression sans vision globale optimale
- **Manque de standardisation**: Absence de règles d'allocation claires et reproductibles

### 2. Absence de Traçabilité et d'Historisation
- **Aucun historique**: Pas de base de données des allocations passées
- **Impossible d'analyser**: Aucune métrique sur l'utilisation réelle des postes
- **Perte d'informations**: Difficulté à justifier les décisions en cas d'incident

### 3. Coordination Limitée entre Services
- **Silos opérationnels**: ATC, Operations, Handling travaillent avec des informations fragmentées
- **Pas de vision temps réel**: Aucun dashboard unifié de l'état du tarmac
- **Communication inefficace**: Retards dans la transmission d'informations critiques

### 4. Absence de Prédictivité
- **Retards imprévisibles**: Aucun système pour anticiper les retards et ajuster les allocations
- **Conflits d'occupation**: Risques de double allocation ou de saturation non détectés à l'avance
- **Optimisation impossible**: Pas d'analyse prédictive pour améliorer le flux opérationnel

### 5. Visibilité Limitée du Trafic Aérien
- **Pas de radar intégré**: Impossibilité de suivre les vols en approche en temps réel
- **Anticipation difficile**: Préparation des postes non optimale faute de visibilité sur les ETA réels
- **Réactivité insuffisante**: Gestion des arrivées en mode réactif plutôt que proactif

### 6. Gestion Rudimentaire de la Saturation
- **Overflow non géré**: Pas de processus automatisé pour basculer vers les parkings militaires
- **Rappel manuel**: Libération des places civiles non surveillée automatiquement
- **Perturbations météo**: Impact non anticipé sur les durées d'occupation

---

## Solution Proposée

**UbuntuAirLab Backend** est une plateforme intelligente de gestion d'aire de stationnement qui résout ces problèmes via une architecture moderne combinant:

### 1. Intelligence Artificielle Prédictive

**3 Modèles Machine Learning Spécialisés** hébergés sur Hugging Face Space ([TAGBA/ubuntuairlab](https://tagba-ubuntuairlab.hf.space)):

- **Modèle 1 - Prédiction ETA/ETD Ajustée (XGBoost)**
  - Anticipe les retards avec probabilités (15min, 30min)
  - Ajuste les heures d'arrivée/départ réelles
  - Intègre 26 paramètres (vitesse, altitude, météo, trafic, historique)

- **Modèle 2 - Estimation Durée d'Occupation (LightGBM)**
  - Prédit la durée réelle de stationnement en minutes
  - Calcule intervalles de confiance (min/max)
  - Évite les conflits d'allocation

- **Modèle 3 - Détection de Conflits (XGBoost)**
  - Identifie les risques de double allocation
  - Recommande des décisions (accepter/reporter/rejeter)
  - Fournit explications textuelles pour les opérateurs

### 2. Synchronisation Temps Réel des Vols

**Intégration OpenSky Network** (OAuth2):
- Récupération automatique vols en arrivée/départ toutes les **5 minutes**
- Tracking latitude, longitude, altitude, vitesse, cap
- Identification automatique: immatriculation, compagnie, provenance/destination
- Traitement par lots de 10 vols en parallèle pour performance maximale

**Enrichissement AviationStack**:
- Données historiques (3 mois)
- Vols futurs planifiés (>7 jours)
- Horaires timetables journaliers
- Complément pour vols non visibles sur OpenSky

### 3. Allocation Intelligente et Automatisée

**Algorithme d'Allocation Optimale**:
1. Vérification compatibilité taille avion (small/medium/large) vs capacité poste
2. Calcul scoring multi-critères:
   - Distance au terminal (optimisation temps passagers)
   - Présence jetway (confort et rapidité)
   - Disponibilité horaire prédite par IA
   - Historique d'utilisation
3. Attribution automatique du poste ST-01 à ST-13 (civil) ou ST-14 à ST-17 (militaire)

**Configuration Actuelle**:
- **13 postes civils** (ST-01 à ST-13): Priorité pour vols commerciaux
- **4 postes militaires** (ST-14 à ST-17): Réservés ou overflow civil

### 4. Gestion Automatique de la Saturation

**Système d'Overflow Intelligent**:
- Détection automatique saturation zone civile
- Basculement temporaire vers parking militaire avec notification
- **Rappel automatique toutes les 2 minutes**: Surveillance libération places civiles
- Réaffectation automatique dès qu'une place civile se libère

**Gestion des Perturbations**:
- Ajustement ETA/ETD en fonction météo (température, vent, visibilité, pluie)
- Recalcul allocations en cas de retard prolongé
- Détection et résolution conflits d'occupation

### 5. Monitoring et Observabilité Complète

**Métriques Prometheus** exportées en temps réel:
- HTTP requests (total, durée, en cours)
- OpenSky API calls et rate limiting
- ML predictions (cache hit/miss, erreurs)
- Flight sync jobs (statut, durée, vols traités)
- Parking occupancy (total, disponibles, overflow)

**Dashboards Grafana**:
- Visualisation temps réel des métriques
- Alertes configurables (saturation, retards, conflits)
- Analyse tendances et patterns

**Logs Structurés JSON**:
- Traçabilité complète des actions
- Journaux des décisions d'allocation
- Audit trail pour conformité ANAC

### 6. Système de Notifications Multi-Niveau

**6 Types de Notifications**:
1. **Conflit**: Risque double allocation ou saturation
2. **Saturation**: Capacité parking proche du maximum
3. **Rappel**: Place civile disponible pour vol en zone militaire
4. **Overflow**: Vol civil alloué en zone militaire
5. **Delay**: Retard prévu sur ETA/ETD
6. **Parking Freed**: Libération anticipée de place

**3 Niveaux de Sévérité**: INFO, WARNING, CRITICAL

### 7. API REST Complète et Documentée

**Authentification JWT** sécurisée (HS256, 60 min expiration)

**Endpoints Opérationnels**:
- `/api/v1/flights` - Gestion vols (liste, détails, recherche)
- `/api/v1/parking/spots` - Gestion postes (création, modification, statut)
- `/api/v1/parking/allocations` - Historique allocations
- `/api/v1/parking/assign` - Attribution manuelle/automatique
- `/api/v1/parking/military-transfer` - Transfert militaire
- `/api/v1/parking/civil-recall` - Rappel civil
- `/api/v1/parking/conflicts` - Détection conflits
- `/api/v1/predictions/predict` - Prédictions ML (3 modèles)
- `/api/v1/sync/trigger` - Synchronisation manuelle
- `/api/v1/notifications` - Système d'alertes
- `/api/v1/dashboard/stats` - Statistiques opérationnelles

**Documentation Interactive**:
- Swagger UI: https://air-lab.bestwebapp.tech/docs
- ReDoc: https://air-lab.bestwebapp.tech/redoc

### 8. Performance et Cache

**Redis Cache**:
- TTL 5 minutes pour prédictions ML
- Réduction temps réponse: <50ms (hit) vs 5-30s (API ML cold start)
- Invalidation automatique nouveau vol détecté

**Optimisations**:
- Traitement asynchrone (AsyncIO complet)
- Pool PostgreSQL (20 connexions + 10 overflow)
- Batch processing 10 vols parallèles
- Retry automatique avec backoff exponentiel

---

## Fonctionnalités Principales

### 1. Synchronisation Intelligente des Vols

**Scheduler APScheduler**:
- Job synchronisation vols: **Toutes les 5 minutes**
- Job rappel civil: **Toutes les 2 minutes**
- Job nettoyage cache: **Toutes les heures**

**Flux de Synchronisation**:
1. Connexion OpenSky Network OAuth2
2. Récupération vols arrivée/départ pour DXXX (Lomé)
3. Enrichissement données AviationStack si nécessaire
4. Traitement par lots de 10 vols en parallèle
5. Création/mise à jour dans base PostgreSQL
6. Déclenchement allocation automatique si nouveau vol
7. Mise à jour statuts (scheduled → active → completed)

**Données Récupérées par Vol**:
- **Identification**: icao24 (unique), callsign, compagnie
- **Provenance/Destination**: departure_airport, arrival_airport, origin_country
- **Position**: latitude, longitude, altitude, velocity, heading, vertical_rate
- **Temporalité**: first_seen, last_seen, est_arrival_time, est_departure_time
- **Statut**: flight_type (arrival/departure), status (scheduled/active/completed/cancelled)

### 2. Allocation Automatique des Parkings

**Algorithme Multi-Critères**:

```python
# Scoring de compatibilité pour chaque poste
score = (
    compatibility_score * 0.4 +      # Taille avion vs capacité
    jetway_bonus * 0.3 +             # Préférence jetway
    distance_penalty * 0.2 +         # Proximité terminal
    availability_score * 0.1         # Disponibilité prédite
)
```

**Étapes d'Allocation**:
1. Vérifier si vol déjà alloué → retourner allocation existante
2. Appeler ML API pour obtenir prédiction durée occupation
3. Lister postes compatibles avec taille avion
4. Calculer score pour chaque poste disponible
5. Sélectionner poste optimal (score max)
6. Si aucun civil disponible → basculer vers militaire (overflow)
7. Créer allocation en base de données
8. Générer notification si overflow
9. Retourner résultat (spot_id, predicted_duration, overflow_flag)

**Critères de Compatibilité**:
- **Small aircraft** → Tous postes (ST-01 à ST-17)
- **Medium aircraft** → Postes medium/large uniquement
- **Large aircraft** → Postes large uniquement

### 3. Prédictions IA avec Cache

**Endpoint Unifié**: `POST /api/v1/predictions/predict`

**Paramètres Minimaux** (4 obligatoires):
```json
{
  "callsign": "AF1234",
  "icao24": "3944ef",
  "vitesse_actuelle": 250.0,
  "altitude": 3500.0
}
```

**Paramètres Complets** (26 paramètres):
- **Vol**: callsign, icao24, type_vol (0=arrival, 1=departure)
- **Position**: vitesse_actuelle, altitude, distance_piste
- **Météo**: temperature, vent_vitesse, visibilite, pluie, meteo_score
- **Trafic**: approaching, tarmac_occupation, available_spots, current_occupation
- **Historique**: retards_recents, occupations_longues, compagnie_connue
- **Contraintes**: heure_jour, jour_semaine, passagers_estimes, bagages_estimes
- **Operations**: maintenance_prevue, congestion_piste, distance_gate

**Auto-Remplissage Intelligent**:
- Paramètres manquants remplis automatiquement depuis:
  - Base de données (historique vol/compagnie)
  - Statistiques trafic temps réel
  - Données météo simulées
  - Valeurs par défaut sécurisées

**Réponse 3 Modèles**:
```json
{
  "model_1_eta": {
    "eta_ajuste": 36.37,
    "etd_ajuste": null,
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
    "decision_label": "Accepter normalement",
    "explication": "Conditions normales, risque faible"
  }
}
```

### 4. Dashboard et Visualisation

**Endpoint Dashboard**: `GET /api/v1/dashboard/stats`

**Statistiques Temps Réel**:
```json
{
  "overview": {
    "total_spots": 17,
    "occupied_spots": 8,
    "available_spots": 9,
    "occupation_rate": 47.06,
    "military_in_use": 1
  },
  "flights": {
    "active_arrivals": 5,
    "active_departures": 3,
    "scheduled_today": 24,
    "completed_today": 16
  },
  "traffic": {
    "approaching_60km": 8,
    "tarmac_occupation": 0.70,
    "incoming_next_hour": 6,
    "outgoing_next_hour": 4
  },
  "conflicts": {
    "current_conflicts": 0,
    "resolved_today": 2,
    "overflow_count": 3
  }
}
```

**Graphiques et Métriques**:
- Évolution occupation parkings par heure
- Répartition vols par compagnie
- Temps moyen d'occupation par type avion
- Taux d'utilisation postes (civil vs militaire)
- Précision prédictions IA

### 5. Gestion Overflow et Rappel Civil

**Transfert Militaire**: `POST /api/v1/parking/military-transfer`
```json
{
  "icao24": "3944ef",
  "reason": "Saturation zone civile"
}
```

**Rappel Civil Automatique**:
- Job APScheduler toutes les 2 minutes
- Recherche allocations militaires actives (overflow_to_military=TRUE)
- Vérification disponibilité postes civils compatibles
- Réallocation automatique si place disponible
- Notification INFO générée pour informer opérateurs

**Rappel Civil Manuel**: `POST /api/v1/parking/civil-recall`
```json
{
  "allocation_id": 123,
  "target_spot_id": "ST-05"
}
```

### 6. Historique et Traçabilité

**Table parking_allocations** (audit complet):
- allocation_id, flight_icao24, spot_id
- allocated_at, predicted_duration_minutes, predicted_end_time
- actual_start_time, actual_end_time, actual_duration_minutes
- overflow_to_military, overflow_reason
- conflict_detected, conflict_resolved, conflict_resolution_time
- is_active, created_at

**Export CSV**: Filtres sur dates, postes, compagnies, statuts

**Recherches Avancées**:
- Par période (date début/fin)
- Par type de vol (arrival/departure)
- Par compagnie aérienne
- Par poste de stationnement
- Par statut (active/completed)
- Avec/sans overflow
- Avec/sans conflits

### 7. Notifications Temps Réel

**Endpoint**: `GET /api/v1/notifications`

**Types de Notifications**:
1. **CONFLIT** (CRITICAL): Double allocation détectée, action immédiate requise
2. **SATURATION** (WARNING): >80% occupation civile, anticiper overflow
3. **RAPPEL** (INFO): Place civile disponible pour vol en militaire
4. **OVERFLOW** (WARNING): Vol civil basculé en militaire
5. **DELAY** (WARNING): Retard >30min prédit par IA
6. **PARKING_FREED** (INFO): Libération anticipée de place

**Filtres**:
- Non lues uniquement: `?is_read=false`
- Par sévérité: `?severity=critical`
- Par type: `?type=conflit`

**Actions**:
- Marquer lue: `POST /api/v1/notifications/{id}/acknowledge`
- Compteur non lues: `GET /api/v1/notifications/unread/count`

### 8. Sécurité et Authentification

**JWT Tokens**:
- Algorithme: HS256
- Expiration: 60 minutes
- Claims: username, role (admin/user)
- Stockage: localStorage frontend

**Endpoints Authentification**:
- `POST /api/v1/auth/login` - Connexion (retourne access_token)
- `GET /api/v1/auth/me` - Vérifier utilisateur actuel

**Format Login** (application/x-www-form-urlencoded):
```
username=admin@aige.tg
password=AdminAIGE2025!
```

**Rôles**:
- **admin**: Tous endpoints (lecture + écriture)
- **user**: Endpoints lecture uniquement

**Protection**:
- Hashage bcrypt (cost factor 12)
- SQL injection: SQLAlchemy ORM avec paramètres bindés
- CORS: Domaines autorisés configurables
- HTTPS: Let's Encrypt SSL en production

---

## Technologies Utilisées

### Backend Core
- **Python**: 3.11+
- **FastAPI**: 0.121.1 - Framework web ASGI haute performance
- **Uvicorn**: 0.38.0 - Serveur ASGI (4 workers production)
- **Pydantic**: 2.10.5 - Validation données et schémas

### Base de Données
- **PostgreSQL**: 15 - Base relationnelle production
- **SQLAlchemy**: 2.0.45 - ORM asynchrone
- **AsyncPG**: 0.30.0 - Driver PostgreSQL async
- **Alembic**: 1.17.2 - Migrations schéma

### Cache et Performance
- **Redis**: 7 - Cache en mémoire
- **redis[asyncio]**: 5.2.1 - Client Redis asynchrone

### APIs Externes
- **httpx**: 0.28.1 - Client HTTP asynchrone
- **OpenSky Network API**: OAuth2 pour vols temps réel
- **AviationStack API**: Historique et vols futurs
- **Hugging Face Space**: Hébergement modèles ML ([TAGBA/ubuntuairlab](https://tagba-ubuntuairlab.hf.space))

### Machine Learning
- **XGBoost**: Modèle 1 (ETA/ETD) + Modèle 3 (Conflits)
- **LightGBM**: Modèle 2 (Occupation parking)
- API unifiée `/predict` pour les 3 modèles

### Scheduling
- **APScheduler**: 3.11.0 - Planificateur tâches
  - Sync vols: 5 minutes
  - Rappel civil: 2 minutes
  - Nettoyage cache: 60 minutes

### Sécurité
- **python-jose[cryptography]**: 3.3.0 - JWT
- **passlib[bcrypt]**: 1.7.4 - Hashage mots de passe
- **bcrypt**: 4.2.1 - Algorithme sécurisé

### Monitoring
- **prometheus-client**: 0.21.1 - Métriques
- **prometheus-fastapi-instrumentator**: 7.0.0 - Instrumentation
- **python-json-logger**: 3.2.1 - Logs structurés
- **Grafana**: Dashboards visualisation

### Tests
- **pytest**: 8.3.4 - Framework tests
- **pytest-asyncio**: 0.25.2 - Tests asynchrones
- **pytest-cov**: 6.0.0 - Couverture code

### Déploiement
- **Docker**: Containerisation
- **Docker Compose**: Orchestration multi-conteneurs
- **Nginx**: Reverse proxy
- **Certbot**: SSL Let's Encrypt
- **Ubuntu Server**: 20.04+ / 22.04 LTS

---

## Architecture du Système

### Architecture en Couches

```
┌─────────────────────────────────────────────────────────┐
│                    CLIENT LAYER                         │
│  Frontend (JavaFX/React) + Grafana Dashboards          │
└─────────────────────────────────────────────────────────┘
                         ↓ HTTPS
┌─────────────────────────────────────────────────────────┐
│                  NGINX REVERSE PROXY                     │
│         (SSL/TLS, Load Balancing, Caching)              │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              FASTAPI APPLICATION (Backend)               │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │         API Layer (REST Endpoints)             │    │
│  │  /auth  /flights  /parking  /predictions       │    │
│  │  /sync  /notifications  /dashboard             │    │
│  └────────────────────────────────────────────────┘    │
│                         ↓                               │
│  ┌────────────────────────────────────────────────┐    │
│  │           Service Layer (Business Logic)       │    │
│  │  • ParkingService (allocation algorithms)      │    │
│  │  • PredictionService (ML orchestration)        │    │
│  │  • NotificationService (alerts)                │    │
│  │  • TrafficStatsService (analytics)             │    │
│  │  • SchedulerService (APScheduler jobs)         │    │
│  │  • PipelineOrchestrator (sync workflow)        │    │
│  └────────────────────────────────────────────────┘    │
│                         ↓                               │
│  ┌────────────────────────────────────────────────┐    │
│  │      Repository Layer (Data Access)            │    │
│  │  • FlightRepository                            │    │
│  │  • ParkingSpotRepository                       │    │
│  │  • ParkingAllocationRepository                 │    │
│  │  • UserRepository                              │    │
│  │  • NotificationRepository                      │    │
│  │  • AIPredictionRepository                      │    │
│  └────────────────────────────────────────────────┘    │
│                         ↓                               │
│  ┌────────────────────────────────────────────────┐    │
│  │     External Clients (API Integrations)        │    │
│  │  • OpenSkyClient (OAuth2)                      │    │
│  │  • AviationStackClient                         │    │
│  │  • MLAPIClient (Hugging Face)                  │    │
│  └────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
            ↓                         ↓
┌─────────────────────┐   ┌─────────────────────┐
│   PostgreSQL DB     │   │    Redis Cache      │
│  (Persistent Data)  │   │  (ML Predictions)   │
└─────────────────────┘   └─────────────────────┘

External APIs:
┌─────────────────────┐   ┌─────────────────────┐
│  OpenSky Network    │   │  AviationStack API  │
│  (Flight Tracking)  │   │  (Flight History)   │
└─────────────────────┘   └─────────────────────┘
                ↓
        ┌─────────────────────┐
        │  Hugging Face Space │
        │  TAGBA/ubuntuairlab │
        │  (3 ML Models)      │
        └─────────────────────┘

Monitoring Stack:
┌─────────────────────┐   ┌─────────────────────┐
│    Prometheus       │   │      Grafana        │
│  (Metrics Storage)  │   │   (Visualization)   │
└─────────────────────┘   └─────────────────────┘
```

### Structure des Dossiers

```
UbuntuairLab_Backend/
├── app/
│   ├── core/                     # Configuration centrale
│   │   ├── config.py            # Settings Pydantic
│   │   ├── security.py          # JWT + hashage
│   │   ├── logging.py           # Logs JSON
│   │   └── metrics.py           # Prometheus
│   ├── models/                  # SQLAlchemy ORM
│   │   ├── flight.py
│   │   ├── parking_spot.py
│   │   ├── parking_allocation.py
│   │   ├── user.py
│   │   ├── ai_prediction.py
│   │   └── notification.py
│   ├── schemas/                 # Pydantic validation
│   │   ├── flight.py
│   │   ├── parking.py
│   │   ├── prediction.py
│   │   └── user.py
│   ├── services/
│   │   ├── business/           # Logique métier
│   │   │   ├── parking_service.py
│   │   │   └── traffic_stats_service.py
│   │   ├── external/           # Clients API
│   │   │   ├── opensky_client.py
│   │   │   ├── aviationstack_client.py
│   │   │   └── ml_api_client.py
│   │   ├── ml/                 # Services ML
│   │   │   └── prediction_service.py
│   │   ├── notifications/      # Système alertes
│   │   │   └── notification_service.py
│   │   └── orchestration/      # Workflow
│   │       ├── scheduler_service.py
│   │       └── pipeline_orchestrator.py
│   ├── repositories/           # Accès données
│   │   ├── flight_repository.py
│   │   ├── parking_repository.py
│   │   └── user_repository.py
│   ├── api/v1/endpoints/       # REST API
│   │   ├── auth.py
│   │   ├── flights.py
│   │   ├── parking.py
│   │   ├── predictions.py
│   │   ├── sync.py
│   │   ├── notifications.py
│   │   └── dashboard.py
│   └── database.py             # DB sessions
├── alembic/                    # Migrations
│   └── versions/
│       ├── 001_initial_schema.py
│       ├── 002_add_flight_parking_fk.py
│       ├── 003_seed_parking_spots.py
│       └── ...
├── docs/                       # Documentation
│   ├── ARCHITECTURE.md
│   ├── FRONTEND_INTEGRATION.md
│   └── diagrammes/
├── monitoring/
│   ├── prometheus.yml
│   └── grafana/dashboards/
├── nginx/
│   └── ubuntuairlab.conf
├── docker-compose.prod.yml
├── Dockerfile
├── requirements.txt
└── .env.production.example
```

### Base de Données (PostgreSQL)

**7 Tables Principales**:

1. **flights** - Vols (arrivées/départs)
2. **parking_spots** - 17 postes stationnement
3. **parking_allocations** - Historique allocations
4. **users** - Utilisateurs système
5. **ai_predictions** - Historique prédictions ML
6. **notifications** - Système alertes
7. **aircraft_turnaround_rules** - Règles temps rotation

**Relations**:
- flights 1:1 → parking_allocations (assigned_parking)
- parking_spots 1:N → parking_allocations
- flights 1:N → ai_predictions
- users 1:N → notifications

Détails complets: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## Instructions pour Exécuter le Prototype

### Prérequis

- **Machine virtuelle Ubuntu Server** 20.04+ ou 22.04 LTS
- **Docker** 20.10+
- **Docker Compose** 2.0+
- **Nginx** 1.18+
- **Certbot** (Let's Encrypt) pour SSL
- **Compte OpenSky Network** avec OAuth2 credentials
- **Domaine** pointé vers IP de la VM

### Installation sur VM Ubuntu

#### 1. Préparation du Système

```bash
# Mettre à jour le système
sudo apt update && sudo apt upgrade -y

# Installer Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Installer Docker Compose
sudo apt install docker-compose-plugin -y

# Installer Nginx et Certbot
sudo apt install nginx certbot python3-certbot-nginx -y

# Redémarrer session pour groupe docker
newgrp docker
```

#### 2. Cloner et Configurer le Projet

```bash
# Cloner le repository
git clone https://github.com/votre-compte/UbuntuairLab_Backend.git
cd UbuntuairLab_Backend

# Créer fichier environnement production
cp .env.production.example .env
```

#### 3. Configurer Variables d'Environnement

Éditer le fichier `.env`:

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:CHANGE_ME_DB_PASSWORD@db:5432/ubuntuairlab

# OpenSky Network OAuth2
OPENSKY_CLIENT_ID=votre-email@example.com-api-client
OPENSKY_CLIENT_SECRET=VOTRE_SECRET_OPENSKY
OPENSKY_TOKEN_URL=https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token

# AviationStack API (optionnel)
AVIATIONSTACK_ACCESS_KEY=VOTRE_CLE_AVIATIONSTACK

# ML API (Hugging Face)
USE_MOCK_AI=false
ML_API_BASE_URL=https://tagba-ubuntuairlab.hf.space
ML_API_TIMEOUT=30.0

# JWT Secret (générer avec: openssl rand -hex 32)
JWT_SECRET=GENERER_SECRET_ALEATOIRE_32_CARACTERES_MINIMUM
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# Redis
REDIS_URL=redis://redis:6379/0

# CORS
CORS_ORIGINS=["https://air-lab.bestwebapp.tech","https://bestwebapp.tech"]

# Configuration AIGE
AIRPORT_ICAO=DXXX
AIRPORT_IATA=LFW
AIRPORT_NAME=Gnassingbe Eyadema International Airport
SYNC_INTERVAL_MINUTES=5
CIVIL_RECALL_INTERVAL_MINUTES=2

# Cache
ENABLE_PREDICTION_CACHE=true
PREDICTION_CACHE_TTL=300

# Monitoring
ENABLE_METRICS=true
LOG_LEVEL=INFO
```

#### 4. Build et Démarrage

```bash
# Build images Docker
docker compose -f docker-compose.prod.yml build

# Démarrer tous les services
docker compose -f docker-compose.prod.yml up -d

# Vérifier status
docker compose -f docker-compose.prod.yml ps
```

#### 5. Initialisation Base de Données

```bash
# Appliquer migrations Alembic
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Créer utilisateur administrateur
docker compose -f docker-compose.prod.yml exec backend python -c "
from app.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

db = SessionLocal()
admin = User(
    username='admin',
    email='admin@aige.tg',
    hashed_password=get_password_hash('AdminAIGE2025!'),
    full_name='Administrateur AIGE',
    role='admin',
    is_active=True
)
db.add(admin)
db.commit()
print('✅ Utilisateur admin créé avec succès')
"
```

#### 6. Configuration Firewall

```bash
# Autoriser ports nécessaires
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw enable
sudo ufw status
```

#### 7. Configuration Nginx Reverse Proxy

Créer `/etc/nginx/sites-available/ubuntuairlab`:

```nginx
server {
    listen 80;
    server_name air-lab.bestwebapp.tech;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 90;
    }

    # Prometheus metrics (accès restreint)
    location /metrics {
        proxy_pass http://localhost:8000/metrics;
        allow 10.0.0.0/8;    # Réseau interne uniquement
        deny all;
    }
}
```

Activer et redémarrer:

```bash
sudo ln -s /etc/nginx/sites-available/ubuntuairlab /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 8. Configuration SSL avec Let's Encrypt

```bash
# Obtenir certificat SSL
sudo certbot --nginx -d air-lab.bestwebapp.tech

# Tester renouvellement automatique
sudo certbot renew --dry-run
```

### Accès aux Services

Après déploiement:

- **API Backend**: https://air-lab.bestwebapp.tech/api/v1
- **Documentation Swagger**: https://air-lab.bestwebapp.tech/docs
- **ReDoc**: https://air-lab.bestwebapp.tech/redoc
- **Health Check**: https://air-lab.bestwebapp.tech/health
- **Prometheus**: http://localhost:9090 (VM uniquement)
- **Grafana**: http://localhost:3000 (VM uniquement)

### Credentials par Défaut

**Admin User**:
- Username: `admin@aige.tg`
- Password: `AdminAIGE2025!`

**Grafana** (si configuré):
- Username: `admin`
- Password: `admin` (changer après première connexion)

---

## API Endpoints Complets

### Authentification

| Méthode | Endpoint | Description | Auth |
|---------|----------|-------------|------|
| POST | `/api/v1/auth/login` | Connexion (retourne JWT) | Non |
| GET | `/api/v1/auth/me` | Utilisateur actuel | JWT |

### Vols

| Méthode | Endpoint | Description | Auth |
|---------|----------|-------------|------|
| GET | `/api/v1/flights/` | Liste vols (filtres: type, status) | JWT |
| GET | `/api/v1/flights/{icao24}` | Détails vol spécifique | JWT |
| GET | `/api/v1/flights/{icao24}/predictions` | Prédictions pour vol | JWT |

### Parking - Postes

| Méthode | Endpoint | Description | Auth |
|---------|----------|-------------|------|
| GET | `/api/v1/parking/spots` | Liste tous postes | JWT |
| POST | `/api/v1/parking/spots` | Créer nouveau poste | Admin |
| GET | `/api/v1/parking/spots/{spot_id}` | Détails poste | JWT |
| PATCH | `/api/v1/parking/spots/{spot_id}` | Modifier poste | Admin |
| DELETE | `/api/v1/parking/spots/{spot_id}` | Supprimer poste | Admin |

### Parking - Allocations

| Méthode | Endpoint | Description | Auth |
|---------|----------|-------------|------|
| GET | `/api/v1/parking/allocations` | Liste allocations | JWT |
| GET | `/api/v1/parking/allocations/{id}` | Détails allocation | JWT |
| GET | `/api/v1/parking/availability` | Disponibilité temps réel | JWT |
| POST | `/api/v1/parking/assign` | Attribuer parking (auto/manuel) | Admin |
| POST | `/api/v1/parking/military-transfer` | Transférer vers militaire | Admin |
| POST | `/api/v1/parking/civil-recall` | Rappeler vers civil | Admin |
| GET | `/api/v1/parking/conflicts` | Liste conflits détectés | JWT |

### Prédictions IA

| Méthode | Endpoint | Description | Auth |
|---------|----------|-------------|------|
| POST | `/api/v1/predictions/predict` | Prédiction ML (3 modèles) | JWT |
| POST | `/api/v1/predictions/predict/batch` | Prédictions multiples | JWT |
| GET | `/api/v1/predictions/health` | Santé API ML | JWT |
| GET | `/api/v1/predictions/models/info` | Info modèles | JWT |

### Synchronisation

| Méthode | Endpoint | Description | Auth |
|---------|----------|-------------|------|
| POST | `/api/v1/sync/trigger` | Déclencher sync manuelle | Admin |
| GET | `/api/v1/sync/status` | Statut sync en cours | JWT |
| PATCH | `/api/v1/sync/interval/{minutes}` | Modifier intervalle sync | Admin |

### Notifications

| Méthode | Endpoint | Description | Auth |
|---------|----------|-------------|------|
| GET | `/api/v1/notifications/notifications` | Liste notifications | JWT |
| POST | `/api/v1/notifications/notifications/{id}/acknowledge` | Marquer notification lue | JWT |
| GET | `/api/v1/notifications/notifications/unread/count` | Compteur non lues | JWT |
| GET | `/api/v1/notifications/notifications/critical` | Notifications critiques | JWT |

### Dashboard

| Méthode | Endpoint | Description | Auth |
|---------|----------|-------------|------|
| GET | `/api/v1/dashboard/stats` | Statistiques complètes | JWT |

### Monitoring

| Méthode | Endpoint | Description | Auth |
|---------|----------|-------------|------|
| GET | `/health` | Health check système | Non |
| GET | `/metrics` | Métriques Prometheus | Non (IP restreint) |

Documentation interactive complète: https://air-lab.bestwebapp.tech/docs

---

## Monitoring et Maintenance

### Logs

```bash
# Logs backend temps réel
docker compose -f docker-compose.prod.yml logs -f backend

# Logs base de données
docker compose -f docker-compose.prod.yml logs -f db

# Logs Redis
docker compose -f docker-compose.prod.yml logs -f redis

# Tous logs
docker compose -f docker-compose.prod.yml logs -f
```

### Backup Base de Données

```bash
# Backup manuel
docker compose -f docker-compose.prod.yml exec db pg_dump -U postgres ubuntuairlab > backup_$(date +%Y%m%d_%H%M%S).sql

# Restauration
docker compose -f docker-compose.prod.yml exec -T db psql -U postgres ubuntuairlab < backup_20251212_153000.sql
```

### Mise à Jour

```bash
# Pull dernière version
git pull origin main

# Rebuild images
docker compose -f docker-compose.prod.yml build

# Restart services
docker compose -f docker-compose.prod.yml up -d

# Appliquer nouvelles migrations
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### Health Checks

```bash
# Vérifier santé application
curl https://air-lab.bestwebapp.tech/health

# Vérifier métriques
curl https://air-lab.bestwebapp.tech/metrics

# Status containers
docker compose -f docker-compose.prod.yml ps
```

---

## Documentation Additionnelle

- [Architecture Technique Détaillée](docs/ARCHITECTURE.md)
- [Guide Intégration Frontend](docs/FRONTEND_INTEGRATION.md)
- [Diagrammes de Flux](docs/diagrammes/)

---

## Déploiement Production

**URL Production**: https://air-lab.bestwebapp.tech

**Infrastructure**:
- VM Ubuntu Server 22.04 LTS
- Docker Compose (backend + PostgreSQL + Redis)
- Nginx reverse proxy
- Let's Encrypt SSL
- Prometheus + Grafana monitoring

**Performance**:
- Health check: ✅ Healthy
- Scheduler: ✅ Active (prochain sync: voir `/health`)
- API Response Time: <100ms (P95)
- ML Predictions (cache hit): <50ms
- ML Predictions (cache miss): <30s

---

## Contribution

Pour contribuer au projet:

1. Fork le repository
2. Créer branche feature (`git checkout -b feature/AmazingFeature`)
3. Commit changements (`git commit -m 'Add AmazingFeature'`)
4. Push branche (`git push origin feature/AmazingFeature`)
5. Ouvrir Pull Request

---

## Licence

Ce projet est sous licence MIT.

---

## Support et Contact

**Équipe UbuntuAirLab - AIGE APRON-SMART**

- Email support: support@ubuntuairlab.com
- Documentation API: https://air-lab.bestwebapp.tech/docs
- Monitoring: Grafana dashboards (accès interne)

**Partenaires**:
- AIGE - Aéroport International Gnassingbé Eyadéma
- ANAC Togo - Autorité Nationale de l'Aviation Civile
- TAGBA - Modèles ML et IA

---

**Version**: 2.0.0  
**Dernière mise à jour**: 12 Décembre 2025  
**Déploiement**: https://air-lab.bestwebapp.tech
