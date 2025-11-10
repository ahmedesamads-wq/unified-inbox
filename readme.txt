# Unified Inbox - Self-Hosted Email Aggregator

A production-ready, self-hosted unified inbox that aggregates Gmail and Outlook accounts via OAuth 2.0.

## Features

- 🔐 OAuth 2.0 integration for Gmail and Outlook
- 📧 Unified inbox view across all connected accounts
- 🔄 Automatic incremental email sync (every 5 minutes)
- 💬 Reply from the correct originating account
- 📎 Attachment download support
- 🧵 Thread grouping
- 👥 Multi-user support with roles
- 🐳 Fully Dockerized
- 🔒 Encrypted token storage
- ⚡ Scalable to ~800 accounts

## Tech Stack

- **Backend**: Python FastAPI + SQLAlchemy
- **Workers**: Celery + Redis
- **Database**: PostgreSQL
- **Frontend**: React + Vite + TailwindCSS
- **Proxy**: Nginx
- **Deployment**: Docker Compose

## Prerequisites

- Ubuntu 22.04 (or similar Linux)
- Docker & Docker Compose
- Domain name pointing to your server
- Google OAuth App credentials
- Microsoft Azure App credentials

## Quick Start

### 1. Clone the Repository

```bash
git clone <your-repo-url> unified-inbox
cd unified-inbox
```

### 2. Generate Encryption Keys

```bash
python3 scripts/generate_keys.py
```

This will output:
- `FERNET_KEY` - for encrypting refresh tokens
- `SECRET_KEY` - for JWT tokens

### 3. Create OAuth Applications

#### Google OAuth App

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Gmail API
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
5. Application type: Web application
6. Authorized redirect URIs:
   - `https://your-domain.com/api/v1/oauth/gmail/callback`
   - `http://localhost/api/v1/oauth/gmail/callback` (for testing)
7. Copy Client ID and Client Secret

#### Microsoft OAuth App

1. Go to [Azure Portal](https://portal.azure.com/)
2. Navigate to "Azure Active Directory" → "App registrations"
3. Click "New registration"
4. Name: Unified Inbox
5. Supported account types: "Accounts in any organizational directory and personal Microsoft accounts"
6. Redirect URI: Web → `https://your-domain.com/api/v1/oauth/outlook/callback`
7. After creation, go to "Certificates & secrets" → Create new client secret
8. Go to "API permissions" → Add:
   - `Mail.Read`
   - `Mail.Send`
   - `offline_access`
9. Copy Application (client) ID and Client Secret

### 4. Configure Environment

```bash
cp .env.example .env
nano .env
```

Fill in all required variables:

```env
# Database
POSTGRES_USER=unifiedinbox
POSTGRES_PASSWORD=<generate-strong-password>
POSTGRES_DB=unifiedinbox

# Redis
REDIS_URL=redis://redis:6379/0

# Security (from step 2)
FERNET_KEY=<generated-fernet-key>
SECRET_KEY=<generated-secret-key>

# App
BASE_URL=https://your-domain.com

# Google OAuth
GOOGLE_CLIENT_ID=<your-google-client-id>
GOOGLE_CLIENT_SECRET=<your-google-client-secret>

# Microsoft OAuth
MS_CLIENT_ID=<your-ms-client-id>
MS_CLIENT_SECRET=<your-ms-client-secret>
MS_TENANT=common
```

### 5. Start Services

```bash
# Build and start all services
docker compose up -d --build

# Check logs
docker compose logs -f

# Wait for all services to be healthy
docker compose ps
```

### 6. Run Database Migrations

```bash
docker compose exec backend alembic upgrade head
```

### 7. Access the Application

Open your browser and navigate to:
- `http://localhost` (or your domain)

Create your first user account via the registration page.

## SSL/TLS Setup (Production)

### Using Certbot (Let's Encrypt)

```bash
# Install certbot
sudo apt update
sudo apt install certbot

# Stop nginx temporarily
docker compose stop nginx

# Obtain certificate
sudo certbot certonly --standalone -d your-domain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem infra/nginx/ssl/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem infra/nginx/ssl/
sudo chmod 644 infra/nginx/ssl/*.pem

# Update nginx.conf to use SSL (uncomment SSL server block)
# Restart nginx
docker compose up -d nginx
```

### Auto-renewal

```bash
# Add to crontab
sudo crontab -e

# Add this line (renew at 2 AM daily)
0 2 * * * certbot renew --quiet && cp /etc/letsencrypt/live/your-domain.com/*.pem /path/to/unified-inbox/infra/nginx/ssl/ && docker compose -f /path/to/unified-inbox/docker-compose.yml restart nginx
```

## Connecting Your First Account

1. Log in to the web interface
2. Go to Dashboard
3. Click "Connect Gmail" or "Connect Outlook"
4. Authorize the application
5. Wait for initial sync (50 most recent emails)
6. View your unified inbox

## Architecture

### Services

- **backend**: FastAPI REST API (port 8000)
- **worker**: Celery worker for async tasks
- **beat**: Celery beat scheduler for periodic syncs
- **frontend**: React SPA (port 3000)
- **postgres**: PostgreSQL database
- **redis**: Redis for Celery queue
- **nginx**: Reverse proxy (port 80/443)

### Sync Strategy

- Initial sync: Last 50 emails per account
- Incremental sync: Every 5 minutes
- Uses Gmail historyId and Outlook delta queries
- Automatic token refresh
- Exponential backoff on rate limits

## Useful Commands

```bash
# View logs
docker compose logs -f backend
docker compose logs -f worker

# Restart a service
docker compose restart backend

# Run migrations
docker compose exec backend alembic upgrade head

# Create new migration
docker compose exec backend alembic revision --autogenerate -m "description"

# Access database
docker compose exec postgres psql -U unifiedinbox -d unifiedinbox

# Access Redis CLI
docker compose exec redis redis-cli

# Run tests
docker compose exec backend pytest

# Manual sync for specific account
docker compose exec backend python -c "
from src.tasks.celery_app import sync_account_task
sync_account_task.delay(account_id=1)
"

# Check Celery status
docker compose exec worker celery -A src.tasks.celery_app inspect active
```

## Scaling for 800+ Accounts

The application is designed to handle ~800 accounts efficiently:

1. **Async I/O**: FastAPI + asyncpg for non-blocking operations
2. **Task Distribution**: Celery distributes sync tasks across workers
3. **Rate Limiting**: Built-in exponential backoff
4. **Staggered Syncs**: Accounts sync at different intervals
5. **Database Indexes**: Optimized queries on account_id, date
6. **Minimal Storage**: Only last 50 emails per account

To scale horizontally:

```bash
# Add more workers
docker compose up -d --scale worker=4
```

## Troubleshooting

### OAuth Errors

**Problem**: "Redirect URI mismatch"
- Ensure the redirect URI in Google/Microsoft console matches exactly
- Format: `https://your-domain.com/api/v1/oauth/{gmail|outlook}/callback`

**Problem**: "Invalid client"
- Verify CLIENT_ID and CLIENT_SECRET in .env
- Check that the OAuth app is enabled

### Token Refresh Issues

**Problem**: Account shows "Token expired"
- The system auto-refreshes tokens, but if refresh token is invalid:
  1. Go to Dashboard → Connected Accounts
  2. Click "Reconnect" on the affected account
  3. Re-authorize

### Sync Not Working

```bash
# Check worker logs
docker compose logs -f worker

# Check if tasks are queued
docker compose exec redis redis-cli
> LLEN celery

# Manually trigger sync
docker compose exec worker celery -A src.tasks.celery_app call src.tasks.sync_tasks.sync_all_accounts
```

### Database Connection Issues

```bash
# Check if postgres is running
docker compose ps postgres

# Check database logs
docker compose logs postgres

# Reset database (WARNING: deletes all data)
docker compose down -v
docker compose up -d postgres
docker compose exec backend alembic upgrade head
```

### Rate Limiting

Gmail and Outlook have API rate limits:
- **Gmail**: 250 quota units/user/second, 1 billion/day
- **Outlook**: Varies by tenant, typically 10,000 requests/10 minutes

The system implements exponential backoff automatically. If you hit limits frequently:
1. Increase sync interval in `backend/src/tasks/sync_tasks.py`
2. Add more workers to distribute load
3. Implement account-based rate limiting

## Security Considerations

- ✅ Refresh tokens encrypted with Fernet (symmetric encryption)
- ✅ JWT tokens for API authentication
- ✅ HTTPS recommended for production
- ✅ OAuth 2.0 authorization code flow
- ✅ Password hashing with bcrypt
- ✅ SQL injection protection via SQLAlchemy ORM
- ✅ CORS configured for frontend origin only

### Recommendations

1. Use strong passwords for POSTGRES_PASSWORD
2. Rotate SECRET_KEY and FERNET_KEY periodically
3. Enable firewall (ufw) and only expose ports 80/443
4. Regular backups of PostgreSQL database
5. Monitor logs for suspicious activity

## Backup & Restore

### Backup

```bash
# Database backup
docker compose exec postgres pg_dump -U unifiedinbox unifiedinbox > backup_$(date +%Y%m%d).sql

# Backup .env file
cp .env .env.backup
```

### Restore

```bash
# Restore database
cat backup_20240101.sql | docker compose exec -T postgres psql -U unifiedinbox -d unifiedinbox
```

## Development

### Running Locally

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

### Running Tests

```bash
# Backend tests
docker compose exec backend pytest -v

# Frontend tests
cd frontend
npm test
```

## Monitoring

Consider adding monitoring tools:

- **Prometheus + Grafana**: Metrics and dashboards
- **Sentry**: Error tracking
- **Uptime Kuma**: Service availability monitoring

## License

MIT License - See LICENSE file

## Support

For issues, please check:
1. Docker logs: `docker compose logs`
2. Application logs in the containers
3. This README's troubleshooting section

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request
