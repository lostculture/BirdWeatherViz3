# Cloudflare Tunnel Setup for BirdWeatherViz3

This guide explains how to expose BirdWeatherViz3 to the internet using Cloudflare Tunnel.

## Architecture

```
Internet → Cloudflare Edge → cloudflared container → nginx (frontend) → backend API
                                                   ↓
                                              Static files (React app)
```

The frontend nginx container serves both static files and proxies API requests to the backend.

## Prerequisites

- Docker and Docker Compose installed
- A Cloudflare account with a domain configured
- Access to Cloudflare Zero Trust dashboard

## Step 1: Create Data Directory

```bash
mkdir -p /home/richardj/birdweatherviz3-public-data/data/db
mkdir -p /home/richardj/birdweatherviz3-public-data/data/logs
```

## Step 2: Create a Cloudflare Tunnel

1. Go to [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/)
2. Navigate to **Networks > Tunnels**
3. Click **Create a tunnel**
4. Choose **Cloudflared** as the connector type
5. Name your tunnel (e.g., `birdweatherviz3-tunnel`)
6. Copy the tunnel token - you'll need this for the Docker configuration

The token looks like:
```
eyJhIjoiODgyMDA0NTY2YTY2MDc3M2FhMGMwN2NhNWE1YTZlMjAi...
```

## Step 3: Configure the Tunnel Public Hostname

In the tunnel configuration:

1. Go to the **Public Hostname** tab
2. Add a new public hostname:
   - **Subdomain:** your-subdomain (e.g., `birds`)
   - **Domain:** your-domain.com (e.g., `bionaught.com`)
   - **Path:** (leave empty)
   - **Service Type:** HTTP
   - **URL:** `birdweatherviz3-frontend-public:80`

> **Important:** Use the Docker container name (`birdweatherviz3-frontend-public`) not `localhost`. The cloudflared container connects to the frontend via Docker's internal network.

## Step 4: Configure Environment Variables

```bash
# Copy the example file
cp .env.public.example .env.public

# Edit with your values
nano .env.public
```

Required variables:
```bash
# Strong password for configuration page (min 8 characters)
CONFIG_PASSWORD=your-very-strong-password-here

# JWT secret (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
JWT_SECRET=your-random-jwt-secret-at-least-32-chars

# Cloudflare tunnel token
CLOUDFLARE_TUNNEL_TOKEN=eyJhIjoiODgyMDA0...
```

## Step 5: Start the Public Instance

```bash
# Pull cloudflared image
docker pull cloudflare/cloudflared:latest

# Start all containers
docker compose -f docker-compose.public.yml --env-file .env.public up -d
```

## Step 6: Verify the Tunnel

Check that the tunnel is connected:

```bash
docker logs birdweatherviz3-cloudflared
```

You should see messages like:
```
INF Registered tunnel connection connIndex=0 ... location=iad09 protocol=quic
INF Registered tunnel connection connIndex=1 ... location=iad11 protocol=quic
```

## Step 7: Verify DNS

Cloudflare automatically creates a CNAME record when you add a public hostname. Verify it exists:

1. Go to Cloudflare Dashboard > your domain > **DNS > Records**
2. You should see a CNAME record:
   - **Name:** your-subdomain
   - **Target:** `<tunnel-id>.cfargotunnel.com`
   - **Proxy status:** Proxied (orange cloud)

## Running Both Local and Public Instances

You can run both instances simultaneously since they use:
- Different container names (`*-public` suffix)
- Different networks
- Different data volumes

```bash
# Local development instance
docker compose up -d

# Public instance
docker compose -f docker-compose.public.yml --env-file .env.public up -d
```

## Managing the Public Instance

```bash
# View logs
docker compose -f docker-compose.public.yml logs -f

# Stop
docker compose -f docker-compose.public.yml down

# Restart
docker compose -f docker-compose.public.yml restart

# Rebuild after code changes
docker compose -f docker-compose.public.yml up --build -d
```

## Password Management

If you need to reset the password on the public instance:

```bash
# Interactive reset
docker exec -it birdweatherviz3-backend-public python reset_password.py

# Set specific password
docker exec birdweatherviz3-backend-public python reset_password.py --password "new-secure-password"

# Reset to environment variable default
docker exec birdweatherviz3-backend-public python reset_password.py --reset-to-default
```

## Troubleshooting

### Error 1034: CNAME Cross-User Banned
- The public hostname isn't configured in the tunnel
- Go to **Zero Trust > Networks > Tunnels > [your tunnel] > Public Hostname**
- Re-add or verify the hostname configuration

### 502 Bad Gateway
- The cloudflared container can't reach the frontend container
- Verify all containers are on the same Docker network
- Check: `docker network inspect birdweatherviz3_birdweather-public-net`
- Use the container name (`birdweatherviz3-frontend-public:80`) not `localhost`

### 403 Forbidden
- Check **Zero Trust > Access > Applications** - delete any access policies blocking the subdomain
- Check **Security > Bots** - disable Bot Fight Mode if enabled
- Check **Security > Settings** - ensure Under Attack Mode is off

### API Errors (401, 500)
- Check backend logs: `docker logs birdweatherviz3-backend-public`
- Verify environment variables are set correctly

### DNS Not Resolving
- Wait a few minutes for DNS propagation
- Verify the CNAME record exists in Cloudflare DNS
- Test with: `dig your-subdomain.your-domain.com`

## No Port Forwarding Required

Cloudflare Tunnel makes **outbound** connections to Cloudflare's edge. No router/firewall configuration is needed:
- No port forwarding
- No firewall rules
- Works behind NAT

## Security Notes

- Keep your tunnel token secret - treat it like a password
- Use a strong, unique CONFIG_PASSWORD (the configuration page has sensitive operations)
- Generate a random JWT_SECRET (don't reuse secrets)
- The `.env.public` file should never be committed to version control
- Consider enabling Cloudflare Access policies for additional authentication
- The public instance doesn't expose any ports to the host - all traffic goes through Cloudflare
