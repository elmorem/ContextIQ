# Authentication Integration Guide

This guide explains how to integrate authentication into ContextIQ services.

## Overview

ContextIQ provides a flexible authentication system supporting:
- **JWT Bearer Tokens**: For user-based authentication
- **API Keys**: For service-to-service and programmatic access
- **Optional Enforcement**: Can be enabled/disabled per service

## Quick Start

### 1. Generate Configuration

```bash
# Generate JWT secrets and API keys
python scripts/generate_auth_config.py

# Copy example configuration
cp .env.auth.example .env
```

### 2. Configure Environment

Edit `.env` and set your JWT secret:

```bash
AUTH_JWT_SECRET_KEY=your-generated-secret-here
AUTH_REQUIRE_AUTH=true  # or false to disable
```

### 3. Enable Authentication (Optional)

Authentication can be enabled in two ways:

#### Option A: Using Middleware (Recommended)

Add authentication middleware to your FastAPI application:

```python
from shared.auth.middleware import AuthenticationMiddleware
from shared.auth.jwt import JWTHandler
from shared.auth.api_key import APIKeyHandler
from shared.auth.config import AuthSettings

# Load settings
auth_settings = AuthSettings()

# Initialize handlers
jwt_handler = JWTHandler(secret_key=auth_settings.jwt_secret_key)
api_key_handler = APIKeyHandler()

# Add middleware
app.add_middleware(
    AuthenticationMiddleware,
    jwt_handler=jwt_handler,
    api_key_handler=api_key_handler,
    exempt_paths=["/health", "/docs", "/metrics"],
)
```

#### Option B: Using Dependencies

Require authentication per-endpoint:

```python
from typing import Annotated
from fastapi import Depends
from shared.auth.dependencies import get_current_user, require_permissions
from shared.auth.models import UserIdentity, Permission

# Override default dependencies
app.dependency_overrides[get_jwt_handler] = lambda: jwt_handler
app.dependency_overrides[get_api_key_handler] = lambda: api_key_handler

# Require authentication
@app.get("/sessions")
async def list_sessions(
    user: Annotated[UserIdentity, Depends(get_current_user)],
):
    return {"user_id": user.user_id}

# Require specific permissions
@app.post("/sessions")
async def create_session(
    user: Annotated[UserIdentity, Depends(require_permissions(Permission.SESSION_CREATE))],
):
    return {"created_by": user.user_id}
```

## Creating JWT Tokens

### For Users

```python
from shared.auth.jwt import JWTHandler
from shared.auth.models import Permission

jwt_handler = JWTHandler(secret_key="your-secret")

# Create token for user
token = jwt_handler.create_access_token(
    user_id="user_123",
    org_id="org_456",
    email="user@example.com",
    name="John Doe",
    permissions=[
        Permission.SESSION_CREATE,
        Permission.SESSION_READ,
        Permission.MEMORY_READ,
    ],
)

print(f"Token: {token}")
# Use with: curl -H "Authorization: Bearer {token}" http://localhost:8000/...
```

### For Services

```python
# Create service token (no expiration, full permissions)
from datetime import timedelta

service_token = jwt_handler.create_access_token(
    user_id="service_memory_worker",
    org_id=None,
    permissions=[
        Permission.MEMORY_CREATE,
        Permission.MEMORY_READ,
        Permission.SESSION_READ,
    ],
    expires_delta=timedelta(days=365),  # Long-lived for services
)
```

## Managing API Keys

### Generate Keys

```python
from shared.auth.api_key import APIKeyHandler, APIKeyInfo
from shared.auth.models import Permission
from datetime import datetime, timedelta

handler = APIKeyHandler()

# Generate new API key
api_key = handler.generate_api_key()
print(f"API Key: {api_key}")  # "ck_xxxxx..."

# Register key with permissions
key_info = APIKeyInfo(
    key_id="key_001",
    user_id="user_123",
    org_id="org_456",
    permissions=[
        Permission.SESSION_READ,
        Permission.MEMORY_READ,
    ],
    expires_at=datetime.utcnow() + timedelta(days=90),
    rate_limit=1000,  # requests per hour
    is_active=True,
)

handler.register_api_key(api_key, key_info)
```

### Store Keys Securely

**Development**: Store in-memory or config file
**Production**: Store hashed keys in database

```python
# Hash for storage
key_hash = handler.hash_api_key(api_key)

# Store key_hash and key_info in database
# DO NOT store the raw API key
```

## Client Authentication

### Using JWT

```bash
# Get token from your auth system
TOKEN="eyJ0eXAiOiJKV1QiLCJhbGc..."

# Use in requests
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/sessions
```

### Using API Key

```bash
API_KEY="ck_xxxxx..."

curl -H "X-API-Key: $API_KEY" \
  http://localhost:8000/api/v1/sessions
```

## Permission System

### Available Permissions

**Session Permissions**:
- `SESSION_CREATE` - Create new sessions
- `SESSION_READ` - Read session data
- `SESSION_UPDATE` - Update sessions
- `SESSION_DELETE` - Delete sessions
- `SESSION_LIST` - List sessions

**Memory Permissions**:
- `MEMORY_CREATE` - Create memories
- `MEMORY_READ` - Read memories
- `MEMORY_UPDATE` - Update memories
- `MEMORY_DELETE` - Delete memories
- `MEMORY_SEARCH` - Search memories
- `MEMORY_LIST` - List memories

**Admin Permissions**:
- `ADMIN_READ` - Read admin data
- `ADMIN_WRITE` - Write admin data

### Permission Checking

```python
from shared.auth.models import UserIdentity, Permission

user = UserIdentity(...)

# Check single permission
if user.has_permission(Permission.SESSION_CREATE):
    # Create session

# Check any permission
if user.has_any_permission([Permission.ADMIN_READ, Permission.ADMIN_WRITE]):
    # Admin access

# Check all permissions
if user.has_all_permissions([Permission.SESSION_READ, Permission.MEMORY_READ]):
    # Read access
```

## Service Integration Examples

### API Gateway

```python
# services/gateway/app/main.py

from shared.auth.middleware import AuthenticationMiddleware
from shared.auth.jwt import JWTHandler
from shared.auth.config import AuthSettings

auth_settings = AuthSettings()

if auth_settings.require_auth:
    jwt_handler = JWTHandler(secret_key=auth_settings.jwt_secret_key)

    app.add_middleware(
        AuthenticationMiddleware,
        jwt_handler=jwt_handler,
        exempt_paths=auth_settings.require_auth_exceptions,
    )
```

### Memory Service

```python
# services/memory/app/main.py

from shared.auth.dependencies import get_current_user, require_permissions

# Protected endpoint
@app.post("/api/v1/memories")
async def create_memory(
    request: CreateMemoryRequest,
    user: Annotated[UserIdentity, Depends(require_permissions(Permission.MEMORY_CREATE))],
):
    # User is authenticated and has MEMORY_CREATE permission
    memory = await service.create_memory(...)
    return MemoryResponse.model_validate(memory)
```

## Security Best Practices

1. **Secrets Management**
   - Never commit JWT secrets to git
   - Use environment variables
   - Rotate secrets periodically

2. **Token Expiration**
   - Set appropriate expiration times (default: 60 minutes)
   - Implement token refresh for long-lived sessions
   - Use short-lived tokens for high-security operations

3. **API Keys**
   - Hash keys before storage (SHA-256)
   - Store only hashes in database
   - Implement rate limiting
   - Set expiration dates
   - Allow key revocation

4. **HTTPS**
   - Always use HTTPS in production
   - JWT and API keys in transit must be encrypted

5. **Permissions**
   - Grant minimal required permissions
   - Use scoped permissions per service
   - Audit permission usage regularly

6. **Error Handling**
   - Don't leak authentication details in errors
   - Return generic 401/403 responses
   - Log authentication failures

## Troubleshooting

### "JWT handler not configured"

```python
# Make sure to override the dependency
from shared.auth.dependencies import get_jwt_handler

app.dependency_overrides[get_jwt_handler] = lambda: jwt_handler
```

### "Token has expired"

- Check token expiration time
- Implement token refresh
- Increase `AUTH_JWT_ACCESS_TOKEN_EXPIRE_MINUTES`

### "Invalid or missing authentication credentials"

- Verify Authorization header format: `Bearer <token>`
- Check API key header: `X-API-Key: <key>`
- Ensure handlers are configured correctly

### Authentication disabled but still getting 401

- Check `AUTH_REQUIRE_AUTH=false` in .env
- Verify exempt_paths includes your endpoint
- Ensure middleware is configured correctly

## Example: Complete Integration

See `examples/auth_integration.py` for a complete working example.

## References

- [Authentication Package README](../shared/auth/README.md)
- [Permission Types](../shared/auth/models.py)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [JWT Specification](https://jwt.io/)
