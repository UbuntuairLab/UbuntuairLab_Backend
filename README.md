# UbuntuAirLab Backend

Backend FastAPI professionnel pour systeme de gestion aeroportuaire avec integration IA, monitoring complet, et deploiement Azure.

## Caracteristiques

- Authentification OpenSky Network OAuth2
- Integration 3 modeles IA (ETA/ETD, Occupation parking, Detection conflits)
- Cache Redis pour predictions
- Monitoring Prometheus + Grafana
- JWT authentication pour endpoints admin
- Scheduler APScheduler pour synchronisation automatique
- PostgreSQL avec migrations Alembic
- Architecture modulaire et maintenable

## Demarrage rapide

### Prerequis

- Python 3.11+
- Docker et Docker Compose
- Compte OpenSky Network avec API Client

### Installation

1. Cloner le repository
```bash
git clone <repository-url>
cd UbuntuairLab_Backend
```

2. Creer fichier .env depuis template
```bash
cp .env.example .env
```

3. Editer .env avec vos credentials OpenSky
```env
OPENSKY_CLIENT_ID=votre-client-id
OPENSKY_CLIENT_SECRET=votre-client-secret
JWT_SECRET=votre-secret-jwt
```

4. Demarrer avec Docker Compose
```bash
docker-compose up -d
```

5. Acceder a l'API
- API: http://localhost:8000
- Documentation: http://localhost:8000/docs
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

## Configuration

### Parametres cles dans .env

- `SYNC_INTERVAL_MINUTES`: Intervalle synchronisation OpenSky (defaut: 5)
- `USE_MOCK_AI`: Utiliser mock IA (true) ou endpoints reels (false)
- `ENABLE_PREDICTION_CACHE`: Activer cache Redis predictions
- `AIRPORT_ICAO`: Code ICAO aeroport (defaut: DXXX)

## Integration modeles IA

Voir documentation complete: [docs/AI_INTEGRATION_GUIDE.md](docs/AI_INTEGRATION_GUIDE.md)

### Basculer vers production

1. Deployer vos 3 modeles IA sur endpoints HTTP
2. Mettre a jour .env:
```env
USE_MOCK_AI=false
MODEL_ETA_ENDPOINT=https://votre-endpoint-eta.com/predict
MODEL_OCCUPATION_ENDPOINT=https://votre-endpoint-occupation.com/predict
MODEL_CONFLIT_ENDPOINT=https://votre-endpoint-conflit.com/predict
```

3. Redemarrer service
```bash
docker-compose restart backend
```

## API Endpoints principaux

### Authentification
- `POST /api/v1/auth/login` - Connexion
- `POST /api/v1/auth/register` - Inscription

### Vols
- `GET /api/v1/flights` - Liste vols actifs
- `GET /api/v1/flights/{icao24}` - Details vol
- `POST /api/v1/flights/sync` - Synchronisation manuelle

### Parking
- `GET /api/v1/parking/allocations` - Allocations actuelles
- `GET /api/v1/admin/parking/spots` - Liste spots (admin)
- `POST /api/v1/admin/parking/spots` - Creer spot (admin)

### Admin
- `GET /api/v1/admin/config` - Configuration actuelle
- `PATCH /api/v1/admin/config` - Modifier configuration

### Monitoring
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

## Architecture

```
app/
├── core/           # Configuration, logging
├── models/         # SQLAlchemy models
├── schemas/        # Pydantic schemas
├── services/       # Business logic
│   ├── ai_models/      # Clients IA
│   ├── external/       # OpenSky client
│   ├── orchestration/  # Scheduler
│   └── business/       # Logique parking
├── repositories/   # Data access layer
├── api/           # REST endpoints
└── middleware/    # Auth, monitoring
```

## Tests

```bash
pytest tests/ -v --cov=app
```

## Deploiement Azure

Voir guide complet: [docs/DEPLOYMENT_AZURE.md](docs/DEPLOYMENT_AZURE.md)

## License

MIT
