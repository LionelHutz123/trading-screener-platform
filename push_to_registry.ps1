# Push Docker Image to Registry
# This script tags and pushes the local image to Docker Hub

param(
    [string]$DockerHubUsername = "your-dockerhub-username",
    [string]$ImageName = "trading-screener",
    [string]$Tag = "latest"
)

Write-Host "🐳 Pushing Docker image to registry..." -ForegroundColor Green

# Check if user provided their Docker Hub username
if ($DockerHubUsername -eq "your-dockerhub-username") {
    Write-Host "❌ Please provide your Docker Hub username!" -ForegroundColor Red
    Write-Host "Usage: .\push_to_registry.ps1 -DockerHubUsername 'your-username'" -ForegroundColor Yellow
    exit 1
}

# Tag the local image
Write-Host "🏷️  Tagging image..." -ForegroundColor Yellow
$fullImageName = "${DockerHubUsername}/${ImageName}:${Tag}"
docker tag untitledfolder-trading-screener:latest $fullImageName

# Push to Docker Hub
Write-Host "📤 Pushing to Docker Hub..." -ForegroundColor Yellow
docker push $fullImageName

Write-Host "✅ Image pushed successfully!" -ForegroundColor Green
Write-Host "📋 Image: $fullImageName" -ForegroundColor Cyan

# Create deployment script for Digital Ocean
$deployScript = @"
# Deploy from Registry to Digital Ocean
# Run this on your Digital Ocean droplet

# Pull the image
docker pull $fullImageName

# Update docker-compose.yml to use the registry image
# Replace the 'build: .' line with:
# image: $fullImageName

# Then run:
# docker-compose up -d
"@

$deployScript | Out-File -FilePath "deploy_from_registry.sh" -Encoding UTF8
Write-Host "📝 Created deploy_from_registry.sh for Digital Ocean deployment" -ForegroundColor Green 