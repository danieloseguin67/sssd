# SQL Server Stats Dashboard - Docker Deployment Guide

This guide explains how to deploy the SQL Server Stats Dashboard (SSSD) using Docker.

## Prerequisites

- Docker installed on your system ([Install Docker](https://docs.docker.com/get-docker/))
- Docker Compose installed (usually comes with Docker Desktop)
- SQL Server instance accessible from the Docker container
- Valid SQL Server credentials with monitoring permissions

## Quick Start

### 1. Configure Database Connection

First, create or update your `config.json` file with your SQL Server connection details:

```bash
cp config.example.json config.json
```

Edit `config.json`:

```json
{
    "server": "your_sql_server_hostname",
    "database": "master",
    "username": "monitoring_user",
    "password": "your_secure_password",
    "driver": "ODBC Driver 17 for SQL Server"
}
```

**Important Notes:**
- If SQL Server is on the same host, use `host.docker.internal` as the server name (Docker Desktop) or the host's IP address
- For SQL Server in another container, use the container name or service name
- Ensure the SQL Server allows connections from the Docker container's IP range

### 2. Build and Run with Docker Compose

The easiest way to deploy is using Docker Compose:

```bash
docker-compose up -d
```

This will:
- Build the Docker image
- Start the container in detached mode
- Map port 8050 on your host to port 8050 in the container
- Mount `config.json` as a read-only volume

### 3. Access the Dashboard

Open your web browser and navigate to:

```
http://localhost:8050
```

### 4. View Logs

To check if the application is running correctly:

```bash
docker-compose logs -f sssd
```

Press `Ctrl+C` to exit log viewing.

### 5. Stop the Dashboard

```bash
docker-compose down
```

## Manual Docker Commands

If you prefer not to use Docker Compose:

### Build the Image

```bash
docker build -t sssd:latest .
```

### Run the Container

```bash
docker run -d \
  --name sql-server-stats-dashboard \
  -p 8050:8050 \
  -v "$(pwd)/config.json:/app/config.json:ro" \
  --restart unless-stopped \
  sssd:latest
```

### View Logs

```bash
docker logs -f sql-server-stats-dashboard
```

### Stop and Remove Container

```bash
docker stop sql-server-stats-dashboard
docker rm sql-server-stats-dashboard
```

## Configuration

### Environment Variables

You can customize the application behavior using environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DASH_DEBUG_MODE` | `False` | Enable debug mode (set to `true` for development) |
| `DASH_HOST` | `0.0.0.0` | Host to bind the application |
| `DASH_PORT` | `8050` | Port to run the application |

Example with environment variables in docker-compose.yml:

```yaml
services:
  sssd:
    environment:
      - DASH_DEBUG_MODE=true
      - DASH_PORT=8080
    ports:
      - "8080:8080"
```

### Multiple Database Monitoring

To monitor multiple SQL Server instances, update your `config.json`:

```json
{
    "default": "production",
    "databases": {
        "production": {
            "server": "prod-sql-server",
            "database": "master",
            "username": "monitor_user",
            "password": "password1",
            "driver": "ODBC Driver 17 for SQL Server"
        },
        "development": {
            "server": "dev-sql-server",
            "database": "master",
            "username": "monitor_user",
            "password": "password2",
            "driver": "ODBC Driver 17 for SQL Server"
        }
    }
}
```

## Networking Considerations

### Accessing SQL Server on Host Machine

**Docker Desktop (Windows/Mac):**
Use `host.docker.internal` as the server name:

```json
{
    "server": "host.docker.internal",
    ...
}
```

**Linux:**
Use the host's IP address or add `--add-host=host.docker.internal:host-gateway` to docker run command.

Update docker-compose.yml:

```yaml
services:
  sssd:
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

### SQL Server in Another Container

If SQL Server is running in another Docker container, use Docker networks:

```yaml
version: '3.8'

services:
  sqlserver:
    image: mcr.microsoft.com/mssql/server:2022-latest
    environment:
      - ACCEPT_EULA=Y
      - SA_PASSWORD=Your_Strong_Password123
    networks:
      - monitoring

  sssd:
    build: .
    depends_on:
      - sqlserver
    networks:
      - monitoring
    # Use 'sqlserver' as the server name in config.json
```

## Security Best Practices

1. **Never commit `config.json` with real credentials** to version control
2. **Use SQL Server authentication** with a dedicated monitoring user
3. **Grant minimal permissions** to the monitoring user:
   ```sql
   CREATE LOGIN [monitoring_user] WITH PASSWORD = 'SecurePassword123!';
   CREATE USER [monitoring_user] FOR LOGIN [monitoring_user];
   GRANT VIEW SERVER STATE TO [monitoring_user];
   GRANT VIEW DATABASE STATE TO [monitoring_user];
   GRANT VIEW ANY DEFINITION TO [monitoring_user];
   ```
4. **Use secrets management** for production deployments (Docker Secrets, Azure Key Vault, etc.)
5. **Restrict network access** to the dashboard using firewalls or reverse proxies
6. **Enable HTTPS** using a reverse proxy (nginx, Traefik, etc.)

## Troubleshooting

### Container won't start

Check logs:
```bash
docker-compose logs sssd
```

### Can't connect to SQL Server

1. Verify `config.json` settings
2. Check SQL Server allows remote connections
3. Verify SQL Server port (default 1433) is accessible
4. Check firewall rules
5. Ensure SQL Server authentication mode is set to "SQL Server and Windows Authentication"

### Permission errors

Ensure the monitoring user has appropriate permissions:
```sql
GRANT VIEW SERVER STATE TO [monitoring_user];
GRANT VIEW DATABASE STATE TO [monitoring_user];
```

### Port already in use

Change the host port in docker-compose.yml:
```yaml
ports:
  - "8051:8050"  # Use port 8051 on host instead
```

### Health check failing

The container includes a health check that queries `http://localhost:8050/`. If it fails:
1. Check if the app is starting correctly in logs
2. Verify config.json is valid
3. Ensure SQL Server is accessible

## Production Deployment

For production environments, consider:

1. **Using a reverse proxy** (nginx/Traefik) with HTTPS
2. **Implementing authentication** to restrict dashboard access
3. **Setting up monitoring** for the container itself (Prometheus, CloudWatch, etc.)
4. **Using Docker secrets** for sensitive configuration
5. **Regular image updates** to include security patches
6. **Resource limits** in docker-compose.yml:

```yaml
services:
  sssd:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

## Updating the Dashboard

### Pull latest code and rebuild:

```bash
git pull
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Or using Docker commands:

```bash
docker stop sql-server-stats-dashboard
docker rm sql-server-stats-dashboard
docker build -t sssd:latest .
docker run -d --name sql-server-stats-dashboard -p 8050:8050 -v "$(pwd)/config.json:/app/config.json:ro" sssd:latest
```

## Support

For issues or questions:
- Check the logs: `docker-compose logs -f`
- Review SQL Server connectivity
- Verify monitoring user permissions
- Check the main README.md for application-specific features

## License

See the main project README for license information.
