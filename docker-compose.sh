#!/bin/bash
# Helper script to run docker-compose with environment-specific config files

set -e

# Default to dev if not specified
ENV="${APP_ENV:-dev}"

# Map environment names to config files
case "$ENV" in
  prod|production)
    CONFIG_FILE="configs/prod.env"
    ;;
  staging|stage)
    CONFIG_FILE="configs/staging.env"
    ;;
  test)
    CONFIG_FILE="configs/test.env"
    ;;
  dev|*)
    CONFIG_FILE="configs/dev.env"
    ;;
esac

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
  echo "Error: Config file $CONFIG_FILE not found!"
  echo "Please create $CONFIG_FILE or set APP_ENV to a valid environment (dev, staging, prod, test)"
  exit 1
fi

# Export APP_ENV
export APP_ENV="$ENV"

# Load environment variables from config file
# This makes them available to docker-compose for variable substitution
set -a
source "$CONFIG_FILE"
set +a

# Run docker compose with all arguments passed to this script
docker compose "$@"
