# Authentication and Authorization

Shared authentication and authorization utilities for ContextIQ services.

## Features

- **JWT Authentication**: Industry-standard JSON Web Tokens
- **API Key Authentication**: Simple API key-based auth
- **Permission-Based Authorization**: Fine-grained access control
- **FastAPI Integration**: Ready-to-use dependencies
- **Multiple Auth Methods**: Support JWT and API keys simultaneously

## Quick Start

### 1. Configure Authentication

```python
from shared.auth.config import AuthSettings
from shared.auth.jwt import JWTHandler
from shared.auth.api_key import APIKeyHandler, APIKeyInfo
from shared.auth.models import Permission

# Load settings
auth_settings = AuthSettings(
    jwt_secret_key="your-secret-key-here",  # Use env var in production
    jwt_access_token_expire_minutes=60,
)

# Initialize handlers
jwt_handler = JWTHandler(
    secret_key=auth_settings.jwt_secret_key,
    algorithm=auth_settings.jwt_algorithm,
    access_token_expire_minutes=auth_settings.jwt_access_token_expire_minutes,
)

api_key_handler = APIKeyHandler()
```

### 2. Use in FastAPI Endpoints

```python
from typing import Annotated
from fastapi import Depends, FastAPI
from shared.auth.dependencies import get_current_user, require_permissions
from shared.auth.models import UserIdentity, Permission

app = FastAPI()

# Require authentication
@app.get("/protected")
async def protected_endpoint(
    user: Annotated[UserIdentity, Depends(get_current_user)],
):
    return {"user_id": user.user_id, "org_id": user.org_id}

# Require specific permissions
@app.post("/sessions")
async def create_session(
    user: Annotated[UserIdentity, Depends(require_permissions(Permission.SESSION_CREATE))],
):
    return {"message": "Session created"}

# Require any of multiple permissions
@app.get("/admin")
async def admin_endpoint(
    user: Annotated[
        UserIdentity,
        Depends(require_any_permission(Permission.ADMIN_READ, Permission.ADMIN_WRITE)),
    ],
):
    return {"message": "Admin access"}
```

### 3. Override Default Dependencies

```python
from fastapi import FastAPI
from shared.auth.dependencies import get_jwt_handler, get_api_key_handler

app = FastAPI()

# Override JWT handler
app.dependency_overrides[get_jwt_handler] = lambda: jwt_handler

# Override API key handler
app.dependency_overrides[get_api_key_handler] = lambda: api_key_handler
```

## Creating JWT Tokens

```python
from shared.auth.jwt import JWTHandler
from shared.auth.models import Permission

jwt_handler = JWTHandler(secret_key="your-secret")

# Create access token
token = jwt_handler.create_access_token(
    user_id="user_123",
    org_id="org_456",
    email="user@example.com",
    name="John Doe",
    permissions=[Permission.SESSION_CREATE, Permission.MEMORY_READ],
)

# Verify token
identity = jwt_handler.verify_token(token)
print(identity.user_id)  # "user_123"
print(identity.permissions)  # [Permission.SESSION_CREATE, Permission.MEMORY_READ]
```

## Using API Keys

```python
from shared.auth.api_key import APIKeyHandler, APIKeyInfo
from shared.auth.models import Permission
from datetime import datetime, timedelta

api_key_handler = APIKeyHandler()

# Generate API key
api_key = api_key_handler.generate_api_key()  # "ck_xxxxx..."

# Register API key
key_info = APIKeyInfo(
    key_id="key_001",
    user_id="user_123",
    org_id="org_456",
    permissions=[Permission.SESSION_READ, Permission.MEMORY_READ],
    expires_at=datetime.utcnow() + timedelta(days=90),
    rate_limit=1000,
)
api_key_handler.register_api_key(api_key, key_info)

# Verify API key
identity = api_key_handler.verify_api_key(api_key)
print(identity.user_id)  # "user_123"
```

## Client Authentication

### JWT Bearer Token

```bash
curl -H "Authorization: Bearer <jwt-token>" \
  http://localhost:8000/api/v1/sessions
```

### API Key

```bash
curl -H "X-API-Key: ck_xxxxx..." \
  http://localhost:8000/api/v1/sessions
```

## Permission Types

### Session Permissions
- `SESSION_CREATE` - Create new sessions
- `SESSION_READ` - Read session data
- `SESSION_UPDATE` - Update sessions
- `SESSION_DELETE` - Delete sessions
- `SESSION_LIST` - List sessions

### Memory Permissions
- `MEMORY_CREATE` - Create memories
- `MEMORY_READ` - Read memories
- `MEMORY_UPDATE` - Update memories
- `MEMORY_DELETE` - Delete memories
- `MEMORY_SEARCH` - Search memories
- `MEMORY_LIST` - List memories

### Admin Permissions
- `ADMIN_READ` - Read admin data
- `ADMIN_WRITE` - Write admin data

## Security Best Practices

1. **Secret Keys**: Use strong random values (32+ bytes)
2. **Environment Variables**: Never commit secrets to git
3. **Token Expiration**: Set appropriate expiration times
4. **HTTPS**: Always use HTTPS in production
5. **Rate Limiting**: Implement rate limiting for API keys
6. **Permission Scoping**: Grant minimal required permissions
7. **Key Rotation**: Regularly rotate JWT secrets and API keys

## Error Handling

```python
from shared.auth.dependencies import AuthenticationError, AuthorizationError

try:
    identity = await get_current_user(...)
except AuthenticationError:
    # 401 Unauthorized
    print("Authentication failed")
except AuthorizationError:
    # 403 Forbidden
    print("Insufficient permissions")
```
