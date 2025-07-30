#!/bin/bash

# Digital Ocean Deployment Script for Trading Screener
# Usage: ./deploy/digitalocean_deploy.sh [environment]

set -e

# Configuration
ENVIRONMENT=${1:-production}
APP_NAME="trading-screener"
REGISTRY_NAME="trading-screener-registry"
DROPLET_NAME="trading-screener-${ENVIRONMENT}"
DROPLET_SIZE="s-2vcpu-4gb"
DROPLET_REGION="nyc3"
DROPLET_IMAGE="docker-20-04"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required tools are installed
check_requirements() {
    echo_status "Checking requirements..."
    
    if ! command -v doctl &> /dev/null; then
        echo_error "doctl is not installed. Please install it first."
        exit 1
    fi
    
    if ! command -v docker &> /dev/null; then
        echo_error "Docker is not installed. Please install it first."
        exit 1
    fi
    
    # Check if authenticated with DigitalOcean
    if ! doctl account get &> /dev/null; then
        echo_error "Not authenticated with DigitalOcean. Run 'doctl auth init' first."
        exit 1
    fi
    
    echo_status "Requirements check passed."
}

# Create or get container registry
setup_registry() {
    echo_status "Setting up container registry..."
    
    if ! doctl registry get $REGISTRY_NAME &> /dev/null; then
        echo_status "Creating container registry..."
        doctl registry create $REGISTRY_NAME --region nyc3
    else
        echo_status "Container registry already exists."
    fi
    
    # Login to registry
    doctl registry login
}

# Build and push Docker images
build_and_push() {
    echo_status "Building and pushing Docker images..."
    
    # Get registry URL
    REGISTRY_URL=$(doctl registry get $REGISTRY_NAME --format URL --no-header)
    
    # Build backend image
    echo_status "Building backend image..."
    docker build -t $REGISTRY_URL/trading-screener:latest .
    
    # Build frontend image
    echo_status "Building frontend image..."
    docker build -t $REGISTRY_URL/trading-frontend:latest ./frontend
    
    # Push images
    echo_status "Pushing images to registry..."
    docker push $REGISTRY_URL/trading-screener:latest
    docker push $REGISTRY_URL/trading-frontend:latest
}

# Create or update droplet
setup_droplet() {
    echo_status "Setting up droplet..."
    
    # Check if droplet exists
    if doctl compute droplet get $DROPLET_NAME &> /dev/null; then
        echo_status "Droplet already exists. Updating..."
        DROPLET_IP=$(doctl compute droplet get $DROPLET_NAME --format PublicIPv4 --no-header)
    else
        echo_status "Creating new droplet..."
        
        # Create SSH key if not exists
        if ! doctl compute ssh-key get trading-screener-key &> /dev/null; then
            if [ ! -f ~/.ssh/trading_screener_rsa ]; then
                ssh-keygen -t rsa -b 4096 -f ~/.ssh/trading_screener_rsa -N ""
            fi
            doctl compute ssh-key import trading-screener-key --public-key-file ~/.ssh/trading_screener_rsa.pub
        fi
        
        # Create droplet
        doctl compute droplet create $DROPLET_NAME \
            --size $DROPLET_SIZE \
            --image $DROPLET_IMAGE \
            --region $DROPLET_REGION \
            --ssh-keys trading-screener-key \
            --enable-monitoring \
            --enable-private-networking \
            --tag-names $APP_NAME,$ENVIRONMENT \
            --wait
        
        # Get droplet IP
        DROPLET_IP=$(doctl compute droplet get $DROPLET_NAME --format PublicIPv4 --no-header)
        
        echo_status "Droplet created with IP: $DROPLET_IP"
        
        # Wait for SSH to be ready
        echo_status "Waiting for SSH to be ready..."
        while ! ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -i ~/.ssh/trading_screener_rsa root@$DROPLET_IP "echo 'SSH ready'" &> /dev/null; do
            sleep 5
            echo "."
        done
    fi
}

# Deploy application to droplet
deploy_application() {
    echo_status "Deploying application to droplet..."
    
    # Copy deployment files
    scp -i ~/.ssh/trading_screener_rsa -r deploy/docker-compose.prod.yml root@$DROPLET_IP:/root/
    scp -i ~/.ssh/trading_screener_rsa -r deploy/nginx.conf root@$DROPLET_IP:/root/
    scp -i ~/.ssh/trading_screener_rsa -r .env.production root@$DROPLET_IP:/root/
    
    # Get registry URL
    REGISTRY_URL=$(doctl registry get $REGISTRY_NAME --format URL --no-header)
    
    # Deploy on droplet
    ssh -i ~/.ssh/trading_screener_rsa root@$DROPLET_IP << EOF
        # Install docker-compose if not present
        if ! command -v docker-compose &> /dev/null; then
            curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-\$(uname -s)-\$(uname -m)" -o /usr/local/bin/docker-compose
            chmod +x /usr/local/bin/docker-compose
        fi
        
        # Login to registry
        echo "$DIGITAL_OCEAN_TOKEN" | docker login registry.digitalocean.com -u "\$DO_REGISTRY_TOKEN" --password-stdin
        
        # Stop existing containers
        docker-compose -f docker-compose.prod.yml down || true
        
        # Pull latest images
        docker pull $REGISTRY_URL/trading-screener:latest
        docker pull $REGISTRY_URL/trading-frontend:latest
        
        # Update environment variables
        export REGISTRY_URL=$REGISTRY_URL
        
        # Start services
        docker-compose -f docker-compose.prod.yml up -d
        
        # Clean up old images
        docker image prune -f
EOF
    
    echo_status "Application deployed successfully!"
    echo_status "Application URL: http://$DROPLET_IP"
}

# Setup monitoring
setup_monitoring() {
    echo_status "Setting up monitoring..."
    
    ssh -i ~/.ssh/trading_screener_rsa root@$DROPLET_IP << 'EOF'
        # Install Node Exporter for Prometheus monitoring
        if ! command -v node_exporter &> /dev/null; then
            wget https://github.com/prometheus/node_exporter/releases/download/v1.6.0/node_exporter-1.6.0.linux-amd64.tar.gz
            tar xvf node_exporter-1.6.0.linux-amd64.tar.gz
            cp node_exporter-1.6.0.linux-amd64/node_exporter /usr/local/bin/
            rm -rf node_exporter-1.6.0.linux-amd64*
            
            # Create systemd service
            cat > /etc/systemd/system/node_exporter.service << 'NODEEOF'
[Unit]
Description=Node Exporter
After=network.target

[Service]
User=prometheus
Group=prometheus
Type=simple
ExecStart=/usr/local/bin/node_exporter
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
NODEEOF
            
            # Create prometheus user
            useradd --no-create-home --shell /bin/false prometheus || true
            
            # Start and enable service
            systemctl daemon-reload
            systemctl enable node_exporter
            systemctl start node_exporter
        fi
EOF
    
    echo_status "Monitoring setup complete."
}

# Setup SSL certificate
setup_ssl() {
    if [ -n "$DOMAIN_NAME" ]; then
        echo_status "Setting up SSL certificate for $DOMAIN_NAME..."
        
        ssh -i ~/.ssh/trading_screener_rsa root@$DROPLET_IP << EOF
            # Install certbot
            apt update
            apt install -y certbot python3-certbot-nginx
            
            # Get certificate
            certbot --nginx -d $DOMAIN_NAME --non-interactive --agree-tos --email admin@$DOMAIN_NAME
            
            # Setup auto-renewal
            (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | crontab -
EOF
        
        echo_status "SSL certificate setup complete."
    else
        echo_warning "DOMAIN_NAME not set. Skipping SSL setup."
    fi
}

# Health check
health_check() {
    echo_status "Performing health check..."
    
    sleep 30  # Wait for services to start
    
    if curl -f "http://$DROPLET_IP/health" &> /dev/null; then
        echo_status "Health check passed! Application is running."
    else
        echo_error "Health check failed. Please check the logs."
        exit 1
    fi
}

# Cleanup function
cleanup() {
    if [ "$1" = "all" ]; then
        echo_warning "Cleaning up all resources..."
        
        # Stop and remove droplet
        doctl compute droplet delete $DROPLET_NAME --force || true
        
        # Remove images from registry
        doctl registry repository delete-manifest $REGISTRY_NAME trading-screener latest --force || true
        doctl registry repository delete-manifest $REGISTRY_NAME trading-frontend latest --force || true
        
        # Delete registry (uncomment if needed)
        # doctl registry delete $REGISTRY_NAME --force
        
        echo_status "Cleanup complete."
    fi
}

# Main deployment function
main() {
    case "${1:-deploy}" in
        "deploy")
            check_requirements
            setup_registry
            build_and_push
            setup_droplet
            deploy_application
            setup_monitoring
            setup_ssl
            health_check
            echo_status "Deployment complete!"
            ;;
        "cleanup")
            cleanup all
            ;;
        "update")
            build_and_push
            deploy_application
            health_check
            echo_status "Update complete!"
            ;;
        *)
            echo "Usage: $0 [deploy|update|cleanup]"
            exit 1
            ;;
    esac
}

# Run main function
main $@