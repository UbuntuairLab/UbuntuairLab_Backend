# 🚀 Guide de Déploiement Azure - UbuntuAirLab Backend

## 📋 Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [Prérequis](#prérequis)
3. [Architecture Azure](#architecture-azure)
4. [Déploiement Azure Container Registry](#déploiement-azure-container-registry)
5. [Déploiement Azure App Service](#déploiement-azure-app-service)
6. [Configuration des Variables d'Environnement](#configuration-des-variables-denvironnement)
7. [Base de Données PostgreSQL](#base-de-données-postgresql)
8. [CI/CD avec GitHub Actions](#cicd-avec-github-actions)
9. [Monitoring et Logs](#monitoring-et-logs)
10. [Scaling et Performance](#scaling-et-performance)
11. [Sécurité](#sécurité)
12. [Troubleshooting](#troubleshooting)

---

## 🌐 Vue d'ensemble

Ce guide vous accompagne dans le déploiement complet de l'API UbuntuAirLab sur Azure en utilisant:

- **Azure Container Registry (ACR)** - Stockage d'images Docker
- **Azure App Service** - Hébergement de conteneurs
- **Azure Database for PostgreSQL** - Base de données managée
- **Azure Redis Cache** - Cache distribué
- **Azure Monitor** - Monitoring et alertes
- **GitHub Actions** - CI/CD automatisé

---

## 📦 Prérequis

### Outils Locaux

```bash
# Azure CLI
az --version

# Docker
docker --version

# Git
git --version
```

### Installation Azure CLI (si nécessaire)

```bash
# Windows (PowerShell)
Invoke-WebRequest -Uri https://aka.ms/installazurecliwindows -OutFile .\AzureCLI.msi
Start-Process msiexec.exe -Wait -ArgumentList '/I AzureCLI.msi /quiet'

# macOS
brew install azure-cli

# Linux
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

### Connexion Azure

```bash
az login
az account set --subscription "<your-subscription-id>"
```

---

## 🏗️ Architecture Azure

```
┌─────────────────────────────────────────────────────────────┐
│                      Azure Resource Group                    │
│  ┌────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Container    │  │   App Service   │  │  PostgreSQL  │ │
│  │   Registry     │──▶│   (Linux)       │──▶│  Flexible   │ │
│  │   (ACR)        │  │   Docker        │  │  Server      │ │
│  └────────────────┘  └─────────────────┘  └──────────────┘ │
│                             │                                │
│                             ▼                                │
│                      ┌─────────────┐                         │
│                      │ Redis Cache │                         │
│                      └─────────────┘                         │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Azure Monitor + Log Analytics             │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 🐳 Déploiement Azure Container Registry

### 1. Créer le Resource Group

```bash
# Variables
RESOURCE_GROUP="ubuntuairlab-rg"
LOCATION="westeurope"
ACR_NAME="ubuntuairlabacr"

# Créer le groupe de ressources
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION
```

### 2. Créer Azure Container Registry

```bash
# Créer ACR
az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku Basic \
  --admin-enabled true

# Récupérer les identifiants
az acr credential show --name $ACR_NAME --resource-group $RESOURCE_GROUP
```

### 3. Build et Push de l'Image Docker

```bash
# Se connecter à ACR
az acr login --name $ACR_NAME

# Build l'image
docker build -t ubuntuairlab-backend:latest .

# Tagger l'image
docker tag ubuntuairlab-backend:latest $ACR_NAME.azurecr.io/ubuntuairlab-backend:latest
docker tag ubuntuairlab-backend:latest $ACR_NAME.azurecr.io/ubuntuairlab-backend:v1.0.0

# Push vers ACR
docker push $ACR_NAME.azurecr.io/ubuntuairlab-backend:latest
docker push $ACR_NAME.azurecr.io/ubuntuairlab-backend:v1.0.0

# Vérifier les images
az acr repository list --name $ACR_NAME --output table
az acr repository show-tags --name $ACR_NAME --repository ubuntuairlab-backend --output table
```

---

## 🗄️ Base de Données PostgreSQL

### 1. Créer PostgreSQL Flexible Server

```bash
DB_SERVER_NAME="ubuntuairlab-db"
DB_ADMIN_USER="airportadmin"
DB_ADMIN_PASSWORD="SecurePassword123!"
DB_NAME="airport_db"

# Créer le serveur PostgreSQL
az postgres flexible-server create \
  --resource-group $RESOURCE_GROUP \
  --name $DB_SERVER_NAME \
  --location $LOCATION \
  --admin-user $DB_ADMIN_USER \
  --admin-password $DB_ADMIN_PASSWORD \
  --version 15 \
  --sku-name Standard_B2s \
  --tier Burstable \
  --storage-size 32 \
  --public-access 0.0.0.0

# Créer la base de données
az postgres flexible-server db create \
  --resource-group $RESOURCE_GROUP \
  --server-name $DB_SERVER_NAME \
  --database-name $DB_NAME
```

### 2. Configurer le Firewall

```bash
# Autoriser les services Azure
az postgres flexible-server firewall-rule create \
  --resource-group $RESOURCE_GROUP \
  --name $DB_SERVER_NAME \
  --rule-name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0

# Autoriser votre IP locale (pour migration)
MY_IP=$(curl -s https://api.ipify.org)
az postgres flexible-server firewall-rule create \
  --resource-group $RESOURCE_GROUP \
  --name $DB_SERVER_NAME \
  --rule-name AllowMyIP \
  --start-ip-address $MY_IP \
  --end-ip-address $MY_IP
```

### 3. Connection String

```bash
# Format de la connection string
DATABASE_URL="postgresql+asyncpg://$DB_ADMIN_USER:$DB_ADMIN_PASSWORD@$DB_SERVER_NAME.postgres.database.azure.com:5432/$DB_NAME?sslmode=require"
```

---

## 💾 Azure Redis Cache

### Créer Redis Cache

```bash
REDIS_NAME="ubuntuairlab-redis"

az redis create \
  --resource-group $RESOURCE_GROUP \
  --name $REDIS_NAME \
  --location $LOCATION \
  --sku Basic \
  --vm-size c0

# Récupérer les clés
az redis list-keys --resource-group $RESOURCE_GROUP --name $REDIS_NAME

# Connection string
REDIS_URL="redis://:<primary-key>@$REDIS_NAME.redis.cache.windows.net:6380/0?ssl=true"
```

---

## 🌐 Déploiement Azure App Service

### 1. Créer App Service Plan

```bash
APP_SERVICE_PLAN="ubuntuairlab-plan"

az appservice plan create \
  --resource-group $RESOURCE_GROUP \
  --name $APP_SERVICE_PLAN \
  --is-linux \
  --sku B2 \
  --location $LOCATION
```

### 2. Créer Web App avec Container

```bash
APP_NAME="ubuntuairlab-api"

az webapp create \
  --resource-group $RESOURCE_GROUP \
  --plan $APP_SERVICE_PLAN \
  --name $APP_NAME \
  --deployment-container-image-name $ACR_NAME.azurecr.io/ubuntuairlab-backend:latest
```

### 3. Configurer l'Accès à ACR

```bash
# Récupérer les credentials ACR
ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query username --output tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query passwords[0].value --output tsv)

# Configurer le registry
az webapp config container set \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME \
  --docker-registry-server-url https://$ACR_NAME.azurecr.io \
  --docker-registry-server-user $ACR_USERNAME \
  --docker-registry-server-password $ACR_PASSWORD
```

### 4. Activer le Continuous Deployment

```bash
az webapp deployment container config \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME \
  --enable-cd true
```

---

## ⚙️ Configuration des Variables d'Environnement

### 1. Configurer les App Settings

```bash
# Récupérer la DATABASE_URL complète
DB_CONNECTION_STRING="postgresql+asyncpg://$DB_ADMIN_USER:$DB_ADMIN_PASSWORD@$DB_SERVER_NAME.postgres.database.azure.com:5432/$DB_NAME?sslmode=require"

# Récupérer REDIS_URL
REDIS_KEY=$(az redis list-keys --resource-group $RESOURCE_GROUP --name $REDIS_NAME --query primaryKey --output tsv)
REDIS_CONNECTION_STRING="redis://:$REDIS_KEY@$REDIS_NAME.redis.cache.windows.net:6380/0?ssl=true"

# Configurer toutes les variables
az webapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME \
  --settings \
    DATABASE_URL="$DB_CONNECTION_STRING" \
    REDIS_URL="$REDIS_CONNECTION_STRING" \
    OPENSKY_USERNAME="your-opensky-username" \
    OPENSKY_PASSWORD="your-opensky-password" \
    OPENSKY_API_BASE_URL="https://opensky-network.org/api" \
    AIRPORT_ICAO="DXXX" \
    AIRPORT_NAME="Lome Airport" \
    SYNC_INTERVAL_MINUTES="5" \
    SYNC_LOOKBACK_HOURS="2" \
    JWT_SECRET="your-production-secret-key-change-this" \
    JWT_ALGORITHM="HS256" \
    JWT_EXPIRATION_MINUTES="60" \
    API_V1_PREFIX="/api/v1" \
    CORS_ORIGINS="https://yourdomain.com,https://app.yourdomain.com" \
    LOG_LEVEL="INFO" \
    LOG_FORMAT="json" \
    ENABLE_METRICS="true" \
    ENABLE_PREDICTION_CACHE="true" \
    CACHE_TTL_SECONDS="300" \
    WEBSITES_PORT="8000" \
    WEBSITES_CONTAINER_START_TIME_LIMIT="600"
```

### 2. Configuration CORS (via Portal ou CLI)

```bash
az webapp cors add \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME \
  --allowed-origins "https://yourdomain.com" "https://app.yourdomain.com"
```

---

## 🔧 Migration de la Base de Données

### 1. Depuis votre machine locale

```bash
# Installer psql si nécessaire
# Windows: https://www.postgresql.org/download/windows/
# macOS: brew install postgresql

# Variables
export DATABASE_URL="postgresql+asyncpg://$DB_ADMIN_USER:$DB_ADMIN_PASSWORD@$DB_SERVER_NAME.postgres.database.azure.com:5432/$DB_NAME?sslmode=require"

# Activer l'environnement virtuel
.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate    # Linux/macOS

# Exécuter les migrations Alembic
alembic upgrade head

# Seed initial data (optionnel)
python seed_data.py
```

### 2. Configuration SSL PostgreSQL

Téléchargez le certificat SSL Azure:

```bash
curl -o DigiCertGlobalRootCA.crt.pem https://cacerts.digicert.com/DigiCertGlobalRootG2.crt.pem
```

Ajoutez à la connection string:
```
?sslmode=require&sslrootcert=DigiCertGlobalRootCA.crt.pem
```

---

## 🔄 CI/CD avec GitHub Actions

### 1. Créer le Workflow File

Créez `.github/workflows/azure-deploy.yml`:

```yaml
name: Deploy to Azure

on:
  push:
    branches:
      - main
  workflow_dispatch:

env:
  ACR_NAME: ubuntuairlabacr
  IMAGE_NAME: ubuntuairlab-backend
  RESOURCE_GROUP: ubuntuairlab-rg
  APP_NAME: ubuntuairlab-api

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      
      - name: Build and push Docker image
        run: |
          az acr login --name ${{ env.ACR_NAME }}
          
          docker build -t ${{ env.ACR_NAME }}.azurecr.io/${{ env.IMAGE_NAME }}:${{ github.sha }} .
          docker build -t ${{ env.ACR_NAME }}.azurecr.io/${{ env.IMAGE_NAME }}:latest .
          
          docker push ${{ env.ACR_NAME }}.azurecr.io/${{ env.IMAGE_NAME }}:${{ github.sha }}
          docker push ${{ env.ACR_NAME }}.azurecr.io/${{ env.IMAGE_NAME }}:latest
      
      - name: Deploy to Azure Web App
        uses: azure/webapps-deploy@v2
        with:
          app-name: ${{ env.APP_NAME }}
          images: ${{ env.ACR_NAME }}.azurecr.io/${{ env.IMAGE_NAME }}:${{ github.sha }}
      
      - name: Run Database Migrations
        run: |
          # SSH into App Service and run migrations
          az webapp ssh --resource-group ${{ env.RESOURCE_GROUP }} --name ${{ env.APP_NAME }} --timeout 300
          alembic upgrade head
      
      - name: Azure Logout
        run: az logout
```

### 2. Créer Azure Service Principal

```bash
az ad sp create-for-rbac \
  --name "ubuntuairlab-github-actions" \
  --role contributor \
  --scopes /subscriptions/<subscription-id>/resourceGroups/$RESOURCE_GROUP \
  --sdk-auth
```

Copiez le JSON retourné et ajoutez-le comme secret GitHub `AZURE_CREDENTIALS`.

### 3. GitHub Secrets à Configurer

Dans votre repository GitHub > Settings > Secrets:

- `AZURE_CREDENTIALS` - JSON du service principal
- `ACR_USERNAME` - Username ACR
- `ACR_PASSWORD` - Password ACR

---

## 📊 Monitoring et Logs

### 1. Activer Application Insights

```bash
# Créer Application Insights
APPINSIGHTS_NAME="ubuntuairlab-insights"

az monitor app-insights component create \
  --app $APPINSIGHTS_NAME \
  --location $LOCATION \
  --resource-group $RESOURCE_GROUP \
  --application-type web

# Récupérer l'Instrumentation Key
INSTRUMENTATION_KEY=$(az monitor app-insights component show \
  --app $APPINSIGHTS_NAME \
  --resource-group $RESOURCE_GROUP \
  --query instrumentationKey \
  --output tsv)

# Configurer dans App Service
az webapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME \
  --settings APPINSIGHTS_INSTRUMENTATIONKEY=$INSTRUMENTATION_KEY
```

### 2. Consulter les Logs

```bash
# Stream des logs en temps réel
az webapp log tail --resource-group $RESOURCE_GROUP --name $APP_NAME

# Télécharger les logs
az webapp log download --resource-group $RESOURCE_GROUP --name $APP_NAME

# Via Azure Portal
# App Service > Monitoring > Log stream
```

### 3. Configurer les Alertes

```bash
# Alerte sur erreurs HTTP 5xx
az monitor metrics alert create \
  --name "High-Error-Rate" \
  --resource-group $RESOURCE_GROUP \
  --scopes "/subscriptions/<subscription-id>/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Web/sites/$APP_NAME" \
  --condition "count Http5xx > 10" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --action-group <action-group-id>
```

---

## 📈 Scaling et Performance

### 1. Auto-scaling

```bash
# Activer l'auto-scaling
az monitor autoscale create \
  --resource-group $RESOURCE_GROUP \
  --resource $APP_NAME \
  --resource-type "Microsoft.Web/sites" \
  --name autoscale-ubuntuairlab \
  --min-count 1 \
  --max-count 5 \
  --count 2

# Règle: Scale out si CPU > 70%
az monitor autoscale rule create \
  --resource-group $RESOURCE_GROUP \
  --autoscale-name autoscale-ubuntuairlab \
  --condition "Percentage CPU > 70 avg 5m" \
  --scale out 1

# Règle: Scale in si CPU < 30%
az monitor autoscale rule create \
  --resource-group $RESOURCE_GROUP \
  --autoscale-name autoscale-ubuntuairlab \
  --condition "Percentage CPU < 30 avg 5m" \
  --scale in 1
```

### 2. Optimisations App Service

```bash
# Activer ARR Affinity (désactiver pour API stateless)
az webapp update \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME \
  --client-affinity-enabled false

# Activer Always On
az webapp config set \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME \
  --always-on true
```

---

## 🔒 Sécurité

### 1. Activer HTTPS Only

```bash
az webapp update \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME \
  --https-only true
```

### 2. Configurer un Custom Domain + SSL

```bash
# Ajouter le domaine
az webapp config hostname add \
  --resource-group $RESOURCE_GROUP \
  --webapp-name $APP_NAME \
  --hostname api.yourdomain.com

# Activer SSL gratuit
az webapp config ssl bind \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME \
  --certificate-thumbprint auto \
  --ssl-type SNI
```

### 3. Managed Identity pour ACR

```bash
# Activer Managed Identity
az webapp identity assign \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME

# Donner accès à ACR
PRINCIPAL_ID=$(az webapp identity show --resource-group $RESOURCE_GROUP --name $APP_NAME --query principalId --output tsv)

az role assignment create \
  --assignee $PRINCIPAL_ID \
  --role AcrPull \
  --scope /subscriptions/<subscription-id>/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.ContainerRegistry/registries/$ACR_NAME
```

---

## 🐛 Troubleshooting

### Container ne démarre pas

```bash
# Vérifier les logs de démarrage
az webapp log tail --resource-group $RESOURCE_GROUP --name $APP_NAME

# Vérifier la configuration du container
az webapp config container show --resource-group $RESOURCE_GROUP --name $APP_NAME

# Redémarrer l'app
az webapp restart --resource-group $RESOURCE_GROUP --name $APP_NAME
```

### Erreurs de connexion à la DB

```bash
# Tester la connexion depuis App Service
az webapp ssh --resource-group $RESOURCE_GROUP --name $APP_NAME

# Dans le shell:
apt-get update && apt-get install -y postgresql-client
psql "host=$DB_SERVER_NAME.postgres.database.azure.com port=5432 dbname=$DB_NAME user=$DB_ADMIN_USER sslmode=require"
```

### Slow Performance

```bash
# Vérifier les métriques
az monitor metrics list \
  --resource "/subscriptions/<subscription-id>/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Web/sites/$APP_NAME" \
  --metric "CpuPercentage,MemoryPercentage,ResponseTime"

# Upgrade du plan si nécessaire
az appservice plan update \
  --resource-group $RESOURCE_GROUP \
  --name $APP_SERVICE_PLAN \
  --sku P1V2
```

---

## 💰 Estimation des Coûts (Par Mois)

| Service | Tier | Prix Estimé (EUR) |
|---------|------|-------------------|
| App Service (B2) | Basic | ~€55 |
| PostgreSQL Flexible (B2s) | Burstable | ~€30 |
| Redis Cache (C0) | Basic | ~€15 |
| Container Registry (Basic) | Basic | ~€5 |
| Application Insights | Pay-as-you-go | ~€10 |
| **TOTAL** | | **~€115/mois** |

Pour réduire les coûts en développement:
- Utilisez le tier Free/Shared pour App Service
- Arrêtez les ressources la nuit avec Azure Automation
- Utilisez des Reserved Instances pour la production

---

## ✅ Checklist de Déploiement

- [ ] Resource Group créé
- [ ] Azure Container Registry configuré
- [ ] Image Docker buildée et pushée
- [ ] PostgreSQL Flexible Server créé et migré
- [ ] Redis Cache configuré
- [ ] App Service créé et configuré
- [ ] Variables d'environnement définies
- [ ] HTTPS activé
- [ ] Custom domain configuré (optionnel)
- [ ] Monitoring et alertes configurés
- [ ] CI/CD GitHub Actions configuré
- [ ] Backup automatique activé
- [ ] Documentation mise à jour

---

## 📚 Ressources Supplémentaires

- [Azure App Service Documentation](https://docs.microsoft.com/azure/app-service/)
- [Azure Database for PostgreSQL](https://docs.microsoft.com/azure/postgresql/)
- [Azure Container Registry](https://docs.microsoft.com/azure/container-registry/)
- [FastAPI Deployment Best Practices](https://fastapi.tiangolo.com/deployment/)

---

**Dernière mise à jour:** 11 Décembre 2025
**Auteur:** UbuntuAirLab Team
