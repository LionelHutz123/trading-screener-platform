# Push Docker Image to GitHub Container Registry
# This is free and integrated with GitHub

param(
    [string]$GitHubUsername = "your-github-username",
    [string]$ImageName = "trading-screener",
    [string]$Tag = "latest"
)

Write-Host "🐳 Pushing Docker image to GitHub Container Registry..." -ForegroundColor Green

# Check if user provided their GitHub username
if ($GitHubUsername -eq "your-github-username") {
    Write-Host "❌ Please provide your GitHub username!" -ForegroundColor Red
    Write-Host "Usage: .\push_to_github.ps1 -GitHubUsername 'your-username'" -ForegroundColor Yellow
    exit 1
}

# Tag the local image for GitHub Container Registry
Write-Host "🏷️  Tagging image..." -ForegroundColor Yellow
$fullImageName = "ghcr.io/${GitHubUsername}/${ImageName}:${Tag}"
docker tag untitledfolder-trading-screener:latest $fullImageName

# Login to GitHub Container Registry (you'll need a GitHub Personal Access Token)
Write-Host "🔐 Logging into GitHub Container Registry..." -ForegroundColor Yellow
Write-Host "You'll need to create a GitHub Personal Access Token with 'write:packages' permission" -ForegroundColor Yellow
docker login ghcr.io

# Push to GitHub Container Registry
Write-Host "📤 Pushing to GitHub Container Registry..." -ForegroundColor Yellow
docker push $fullImageName

Write-Host "✅ Image pushed successfully!" -ForegroundColor Green
Write-Host "📋 Image: $fullImageName" -ForegroundColor Cyan

# Create deployment script for Digital Ocean
$deployScript = @"
# Deploy from GitHub Container Registry to Digital Ocean
# Run this on your Digital Ocean droplet

# Pull the image
docker pull $fullImageName

# Update docker-compose.yml to use the registry image
# Replace the 'build: .' line with:
# image: $fullImageName

# Then run:
# docker-compose up -d
"@

$deployScript | Out-File -FilePath "deploy_from_github.sh" -Encoding UTF8
Write-Host "📝 Created deploy_from_github.sh for Digital Ocean deployment" -ForegroundColor Green 