#!/usr/bin/env pwsh
#
# Script de déploiement complet - Azure UbuntuAirLab
# Crée toute l'infrastructure Azure nécessaire
#

param(
    [string]$ResourceGroup = "ubuntuairlab-rg",
    [string]$Location = "westeurope",
    [string]$AcrName = "ubuntuairlabacr",
    [string]$AppName = "ubuntuairlab-api",
    [string]$DbServerName = "ubuntuairlab-db",
    [string]$RedisName = "ubuntuairlab-redis",
    [switch]$SkipConfirmation
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Déploiement UbuntuAirLab sur Azure" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Configuration summary
Write-Host "📋 Configuration:" -ForegroundColor Yellow
Write-Host "  Resource Group: $ResourceGroup"
Write-Host "  Location: $Location"
Write-Host "  ACR Name: $AcrName"
Write-Host "  App Name: $AppName"
Write-Host "  DB Server: $DbServerName"
Write-Host "  Redis: $RedisName"
Write-Host ""

if (-not $SkipConfirmation) {
    $confirm = Read-Host "Continuer avec cette configuration? (o/N)"
    if ($confirm -ne "o") {
        Write-Host "❌ Déploiement annulé" -ForegroundColor Red
        exit 1
    }
}

# Check Azure CLI
Write-Host "🔍 Vérification Azure CLI..." -ForegroundColor Yellow
try {
    $azVersion = az version --output tsv 2>&1
    Write-Host "✅ Azure CLI installé" -ForegroundColor Green
} catch {
    Write-Host "❌ Azure CLI non trouvé. Installez-le depuis: https://aka.ms/installazurecliwindows" -ForegroundColor Red
    exit 1
}

# Login check
Write-Host "🔐 Vérification connexion Azure..." -ForegroundColor Yellow
$account = az account show 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Non connecté à Azure. Connexion..." -ForegroundColor Yellow
    az login
}
Write-Host "✅ Connecté à Azure" -ForegroundColor Green

# Create Resource Group
Write-Host ""
Write-Host "📦 Création du Resource Group..." -ForegroundColor Yellow
az group create --name $ResourceGroup --location $Location --output table
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Resource Group créé" -ForegroundColor Green
}

# Create Azure Container Registry
Write-Host ""
Write-Host "🐳 Création Azure Container Registry..." -ForegroundColor Yellow
az acr create `
    --resource-group $ResourceGroup `
    --name $AcrName `
    --sku Basic `
    --admin-enabled true `
    --output table

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ ACR créé" -ForegroundColor Green
}

# Create PostgreSQL Flexible Server
Write-Host ""
Write-Host "🗄️  Création PostgreSQL Flexible Server..." -ForegroundColor Yellow

$dbAdminUser = Read-Host "Nom utilisateur admin PostgreSQL (default: airportadmin)"
if ([string]::IsNullOrEmpty($dbAdminUser)) { $dbAdminUser = "airportadmin" }

$dbPassword = Read-Host "Mot de passe admin PostgreSQL (min 8 caractères)" -AsSecureString
$dbPasswordPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($dbPassword)
)

az postgres flexible-server create `
    --resource-group $ResourceGroup `
    --name $DbServerName `
    --location $Location `
    --admin-user $dbAdminUser `
    --admin-password $dbPasswordPlain `
    --version 15 `
    --sku-name Standard_B2s `
    --tier Burstable `
    --storage-size 32 `
    --public-access 0.0.0.0 `
    --output table

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ PostgreSQL créé" -ForegroundColor Green
    
    # Create database
    Write-Host "📊 Création base de données airport_db..." -ForegroundColor Yellow
    az postgres flexible-server db create `
        --resource-group $ResourceGroup `
        --server-name $DbServerName `
        --database-name airport_db `
        --output table
}

# Create Redis Cache
Write-Host ""
Write-Host "💾 Création Redis Cache..." -ForegroundColor Yellow
az redis create `
    --resource-group $ResourceGroup `
    --name $RedisName `
    --location $Location `
    --sku Basic `
    --vm-size c0 `
    --output table

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Redis créé" -ForegroundColor Green
}

# Create App Service Plan
Write-Host ""
Write-Host "📱 Création App Service Plan..." -ForegroundColor Yellow
$appServicePlan = "$AppName-plan"
az appservice plan create `
    --resource-group $ResourceGroup `
    --name $appServicePlan `
    --is-linux `
    --sku B2 `
    --location $Location `
    --output table

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ App Service Plan créé" -ForegroundColor Green
}

# Create Web App
Write-Host ""
Write-Host "🌐 Création Web App..." -ForegroundColor Yellow
az webapp create `
    --resource-group $ResourceGroup `
    --plan $appServicePlan `
    --name $AppName `
    --deployment-container-image-name "mcr.microsoft.com/appsvc/staticsite:latest" `
    --output table

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Web App créée" -ForegroundColor Green
}

# Configure ACR access
Write-Host ""
Write-Host "🔑 Configuration accès ACR..." -ForegroundColor Yellow
$acrUsername = az acr credential show --name $AcrName --query username --output tsv
$acrPassword = az acr credential show --name $AcrName --query "passwords[0].value" --output tsv

az webapp config container set `
    --resource-group $ResourceGroup `
    --name $AppName `
    --docker-registry-server-url "https://$AcrName.azurecr.io" `
    --docker-registry-server-user $acrUsername `
    --docker-registry-server-password $acrPassword `
    --output table

# Summary
Write-Host ""
Write-Host "✅ Déploiement de l'infrastructure terminé!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Résumé des ressources créées:" -ForegroundColor Cyan
Write-Host "  ✓ Resource Group: $ResourceGroup"
Write-Host "  ✓ Container Registry: $AcrName.azurecr.io"
Write-Host "  ✓ PostgreSQL Server: $DbServerName.postgres.database.azure.com"
Write-Host "  ✓ Redis Cache: $RedisName.redis.cache.windows.net"
Write-Host "  ✓ Web App: https://$AppName.azurewebsites.net"
Write-Host ""
Write-Host "📝 Prochaines étapes:" -ForegroundColor Yellow
Write-Host "  1. Build et push de l'image Docker:"
Write-Host "     .\scripts\azure\deploy-app.ps1"
Write-Host ""
Write-Host "  2. Configurer les variables d'environnement:"
Write-Host "     .\scripts\azure\setup-secrets.ps1"
Write-Host ""
Write-Host "  3. Exécuter les migrations:"
Write-Host "     az webapp ssh --resource-group $ResourceGroup --name $AppName"
Write-Host "     alembic upgrade head"
Write-Host ""
