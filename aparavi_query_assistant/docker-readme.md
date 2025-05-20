# Docker Setup for Aparavi Query Assistant

This document explains how to run the Aparavi Query Assistant using Docker, which provides a consistent, isolated environment for the application.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/) (usually included with Docker Desktop)

## Quick Start

The application is available as a pre-built Docker image at [nowakemc/aql-studio](https://hub.docker.com/r/nowakemc/aql-studio).

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file to configure your settings:
   - Set your API keys for OpenAI, Anthropic, or other LLM providers
   - Configure the Aparavi server connection
   - Set any other environment variables as needed

3. Start the application:
   ```bash
   docker-compose up -d
   ```

4. Access the application at [http://localhost:8080](http://localhost:8080) (or your configured port)

## Building Locally (Alternative)

If you prefer to build the Docker image locally instead of using the pre-built image:

1. Modify the docker-compose.yml file to use a local build:
   ```yaml
   aparavi-query-assistant:
     build:
       context: .
       dockerfile: Dockerfile
   ```

2. Build and start the container:
   ```bash
   docker-compose build
   docker-compose up -d
   ```

## Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AQL_HOST_PORT` | Port on the host machine | 8080 |
| `DEBUG` | Enable debug mode | False |
| `APARAVI_SERVER` | Aparavi server address | localhost |
| `OPENAI_API_KEY` | Your OpenAI API key | - |
| `ANTHROPIC_API_KEY` | Your Anthropic API key | - |
| `OLLAMA_HOST` | Ollama service address | http://ollama:11434 |
| `OLLAMA_MODEL` | Ollama model to use | llama2 |

## Using Local LLM with Ollama

This setup includes an optional Ollama integration for running LLMs locally instead of using cloud APIs:

1. Uncomment the Ollama service section in `docker-compose.yml`
2. Uncomment the `ollama_data` volume 
3. Uncomment the Ollama configuration in `.env`
4. Uncomment the `depends_on` section for the aparavi-query-assistant service
5. Start the services with `docker-compose up -d`

If using GPU acceleration:
- Make sure you have the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) installed
- The `deploy` section in the Ollama service is already configured for GPU usage

## Development Mode

For development, you can mount your local code into the container:

1. Uncomment the volume mount in `docker-compose.yml`:
   ```yaml
   - .:/app
   ```

2. Restart the container:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

## Troubleshooting

### Container doesn't start
- Check the logs: `docker-compose logs -f aparavi-query-assistant`
- Verify your environment variables in the `.env` file
- Ensure the ports are not already in use

### Can't connect to Ollama
- Verify Ollama is running: `docker-compose ps ollama`
- Check Ollama logs: `docker-compose logs -f ollama`
- Make sure the Ollama service is uncommented in `docker-compose.yml`

### Persistent Data

Application data is stored in a Docker volume named `aparavi_data`. This ensures your settings, query history, and other data persist between container restarts.

To back up this data:
```bash
docker run --rm -v aparavi_data:/data -v $(pwd):/backup busybox tar -zcvf /backup/aparavi_data_backup.tar.gz /data
```

To restore from a backup:
```bash
docker run --rm -v aparavi_data:/data -v $(pwd):/backup busybox tar -xzvf /backup/aparavi_data_backup.tar.gz -C /
```
