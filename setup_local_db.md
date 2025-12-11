# Configuration Base de Données Locale

## Option 1 : Utiliser Docker pour PostgreSQL uniquement (RECOMMANDÉ)

```powershell
# Lancer uniquement PostgreSQL et Redis avec Docker
docker-compose up -d postgres redis

# Copier .env.local vers .env
cp .env.local .env

# Lancer les migrations
.venv/Scripts/python.exe -m alembic upgrade head

# Initialiser la base (créer admin)
.venv/Scripts/python.exe init_db.py

# Lancer l'API en local
.venv/Scripts/python.exe -m uvicorn main:app --reload
```

## Option 2 : Installer PostgreSQL localement

### 1. Télécharger PostgreSQL 15
https://www.postgresql.org/download/windows/

### 2. Créer la base de données

Ouvrir **pgAdmin** ou **psql** :

```sql
-- Créer la base
CREATE DATABASE airport_db;

-- Créer l'utilisateur
CREATE USER airport_user WITH PASSWORD 'airport_pass';

-- Accorder tous les privilèges
GRANT ALL PRIVILEGES ON DATABASE airport_db TO airport_user;

-- Se connecter à airport_db
\c airport_db

-- Accorder privilèges sur le schéma public
GRANT ALL ON SCHEMA public TO airport_user;
```

### 3. Copier la configuration locale

```powershell
cp .env.local .env
```

### 4. Lancer les migrations

```powershell
.venv/Scripts/python.exe -m alembic upgrade head
```

### 5. Initialiser la base

```powershell
.venv/Scripts/python.exe init_db.py
```

### 6. Lancer l'application

```powershell
.venv/Scripts/python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Option 3 : Tout avec Docker (PRODUCTION-LIKE)

```powershell
# Utiliser .env avec hostnames Docker
docker-compose up -d

# L'API sera disponible sur http://localhost:8000
```

## Vérification

- API: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Metrics: http://localhost:8000/metrics

## Login par défaut

- Username: `admin`
- Password: `admin123`
