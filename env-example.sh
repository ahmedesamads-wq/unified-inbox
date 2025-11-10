# Database Configuration
POSTGRES_USER=unifiedinbox
POSTGRES_PASSWORD=change_this_to_a_strong_password_123!
POSTGRES_DB=unifiedinbox

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# Security Keys (Generate using: python scripts/generate_keys.py)
# FERNET_KEY is used to encrypt refresh tokens in the database
FERNET_KEY=your_fernet_key_here_use_generate_keys_script
# SECRET_KEY is used for JWT token signing
SECRET_KEY=your_secret_key_here_use_generate_keys_script

# Application Configuration
BASE_URL=http://localhost
# BASE_URL=https://mail.yourdomain.com  # For production

# Google OAuth Configuration
# Create at: https://console.cloud.google.com/apis/credentials
# Redirect URI: ${BASE_URL}/api/v1/oauth/gmail/callback
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Microsoft OAuth Configuration
# Create at: https://portal.azure.com/ (App registrations)
# Redirect URI: ${BASE_URL}/api/v1/oauth/outlook/callback
MS_CLIENT_ID=your-microsoft-client-id
MS_CLIENT_SECRET=your-microsoft-client-secret
MS_TENANT=common

# Email Sync Configuration
SYNC_INTERVAL_MINUTES=5
MAX_MESSAGES_PER_ACCOUNT=50

# JWT Configuration
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Celery Configuration
CELERY_BROKER_URL=${REDIS_URL}
CELERY_RESULT_BACKEND=${REDIS_URL}

# CORS Configuration (Frontend URL)
CORS_ORIGINS=http://localhost:3000,http://localhost

# Environment
ENVIRONMENT=production
