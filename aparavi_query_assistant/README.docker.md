# Aparavi Query Assistant - Docker Guide

This guide provides instructions for running the Aparavi Query Assistant in Docker.

## Prerequisites

- Docker and Docker Compose installed on your system
- Access to the Aparavi Data Service API endpoint

## Quick Start

### Option 1: Using Docker Compose (Recommended)

1. Build and start the container:
   ```bash
   docker-compose up -d
   ```

2. Access the application:
   Open your browser and navigate to `http://localhost:8080`

3. Stop the container:
   ```bash
   docker-compose down
   ```

### Option 2: Using Docker Directly

1. Build the Docker image:
   ```bash
   docker build -t aparavi-query-assistant .
   ```

2. Run the container:
   ```bash
   docker run -p 8080:8080 -v aparavi_data:/root/.aparavi-query-assistant aparavi-query-assistant
   ```

## Configuration

The application uses environment variables for configuration. You can modify these in the `docker-compose.yml` file:

```yaml
environment:
  - DEBUG=False
  - DEFAULT_APARAVI_SERVER=your_server_address
  # Add other environment variables as needed
```

## Persistent Storage

User settings, query history, and credentials are stored in a Docker volume named `aparavi_data`.

## Development Mode

For development, you can mount the local code directory by uncommenting the volume mount in `docker-compose.yml`:

```yaml
volumes:
  # Mount config and logs for persistence
  - aparavi_data:/root/.aparavi-query-assistant
  # For development: uncomment to mount code directory for live changes
  - .:/app
```

## Troubleshooting

If you encounter issues:

1. Check container logs:
   ```bash
   docker-compose logs
   ```

2. Verify connectivity to the Aparavi Data Service API endpoint
3. Ensure required API keys are configured for LLM providers
