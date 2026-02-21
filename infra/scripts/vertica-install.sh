#!/bin/bash
# =============================================================================
# Vertica Community Edition Container Setup
# Runs as startup script on CentOS Stream 9
#
# This script:
# 1. Installs Docker
# 2. Pulls the official Vertica CE container image
# 3. Runs Vertica CE with persistent data volume
# 4. Creates the 'demo' database
#
# After completion, connect with:
#   vsql -h <vm-ip> -p 5433 -U dbadmin -d VMart
#
# Container image: https://hub.docker.com/r/vertica/vertica-ce
# =============================================================================

set -e

LOG_FILE="/var/log/vertica-install.log"
MARKER_FILE="/var/lib/vertica-container-installed"
CONTAINER_NAME="vertica-ce"
# Community image - Vertica 9.2 CE (well-documented, functional for demo)
# https://github.com/jbfavre/docker-vertica
VERTICA_IMAGE="jbfavre/vertica:9.2.0-7_debian-8"

# Redirect all output to log file
exec > >(tee -a "$LOG_FILE") 2>&1

echo "=== Vertica Container Setup Starting: $(date) ==="

# Check if already installed (idempotent)
if [ -f "$MARKER_FILE" ]; then
    echo "Vertica container already configured. Ensuring it's running..."
    docker start "$CONTAINER_NAME" 2>/dev/null || true
    echo "=== Vertica startup complete: $(date) ==="
    exit 0
fi

# -----------------------------------------------------------------------------
# Install Docker
# -----------------------------------------------------------------------------
echo "Installing Docker..."

# Install required packages
dnf install -y dnf-plugins-core

# Add Docker repository
dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# Install Docker
dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Start and enable Docker
systemctl start docker
systemctl enable docker

# Verify Docker is running
docker --version
echo "Docker installed successfully."

# -----------------------------------------------------------------------------
# Pull Vertica CE Image
# -----------------------------------------------------------------------------
echo "Pulling Vertica CE container image..."
docker pull "$VERTICA_IMAGE"

# -----------------------------------------------------------------------------
# Create Data Volume and Run Container
# -----------------------------------------------------------------------------
echo "Creating Vertica data volume..."
docker volume create vertica-data

echo "Starting Vertica CE container..."
docker run -d \
    --name "$CONTAINER_NAME" \
    --restart unless-stopped \
    -p 5433:5433 \
    -v vertica-data:/home/dbadmin/docker \
    -e DATABASE_NAME=demo \
    -e DATABASE_PASSWORD="" \
    "$VERTICA_IMAGE"

# -----------------------------------------------------------------------------
# Wait for Vertica to be Ready
# -----------------------------------------------------------------------------
echo "Waiting for Vertica to initialize (this may take a few minutes)..."

MAX_ATTEMPTS=60
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if docker exec "$CONTAINER_NAME" /opt/vertica/bin/vsql -U dbadmin -c "SELECT 1" 2>/dev/null; then
        echo "Vertica is ready!"
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    echo "Waiting for Vertica... (attempt $ATTEMPT/$MAX_ATTEMPTS)"
    sleep 10
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo "WARNING: Vertica may not be fully ready yet. Check container logs:"
    echo "  docker logs $CONTAINER_NAME"
fi

# -----------------------------------------------------------------------------
# Create Demo Database (if not using default VMart)
# -----------------------------------------------------------------------------
echo "Creating 'demo' database..."
docker exec "$CONTAINER_NAME" /opt/vertica/bin/vsql -U dbadmin -c "
    CREATE DATABASE IF NOT EXISTS demo;
" 2>/dev/null || echo "Note: Using default database (VMart) - demo database creation skipped"

# Mark installation complete
touch "$MARKER_FILE"

echo ""
echo "=== Vertica Container Setup Complete: $(date) ==="
echo ""
echo "Container: $CONTAINER_NAME"
echo "Image:     $VERTICA_IMAGE"
echo "Port:      5433"
echo ""
echo "Connect with:"
echo "  docker exec -it $CONTAINER_NAME vsql -U dbadmin"
echo ""
echo "Or remotely:"
echo "  vsql -h <this-vm-ip> -p 5433 -U dbadmin"
echo ""
