# 🚀 Scripts de Déploiement Azure

Scripts PowerShell et Bash pour automatiser le déploiement sur Azure.

## 📋 Scripts Disponibles

### 1. `deploy-full.ps1` / `deploy-full.sh`
Déploiement complet de l'infrastructure Azure:
- Resource Group
- Container Registry
- PostgreSQL
- Redis
- App Service

### 2. `deploy-app.ps1` / `deploy-app.sh`
Déploiement uniquement de l'application:
- Build Docker image
- Push vers ACR
- Update App Service

### 3. `setup-secrets.ps1` / `setup-secrets.sh`
Configuration des secrets et variables d'environnement

## 🔧 Utilisation

### Windows PowerShell

```powershell
# Configuration initiale
.\scripts\azure\setup-env.ps1

# Déploiement complet
.\scripts\azure\deploy-full.ps1

# Mise à jour de l'app
.\scripts\azure\deploy-app.ps1
```

### Linux/macOS

```bash
# Rendre les scripts exécutables
chmod +x scripts/azure/*.sh

# Configuration initiale
./scripts/azure/setup-env.sh

# Déploiement complet
./scripts/azure/deploy-full.sh

# Mise à jour de l'app
./scripts/azure/deploy-app.sh
```

## ⚙️ Configuration

Créez `scripts/azure/.env.azure`:

```env
RESOURCE_GROUP=ubuntuairlab-rg
LOCATION=westeurope
ACR_NAME=ubuntuairlabacr
APP_NAME=ubuntuairlab-api
DB_SERVER_NAME=ubuntuairlab-db
REDIS_NAME=ubuntuairlab-redis
```
