# Vinverse Python auth service

## Install

```bash
pip install -r requirements.txt
```

## Environment

```bash
export GOOGLE_CLIENT_ID="your-google-oauth-web-client-id.apps.googleusercontent.com"
export JWT_SECRET="long-random-string"
export ALLOWED_EMAILS="you@vinverse.ai"
export AUTH_AUTO_APPROVE="false"
export CORS_ORIGINS="http://localhost:5173"
```

`GOOGLE_CLIENT_ID` must match `VITE_GOOGLE_CLIENT_ID` in the React app.

## Existing main.py

```python
from auth_google import add_cors, router as auth_router

add_cors(app)                 # skip if CORS is already configured
app.include_router(auth_router)
```

That exposes:

- `POST /api/auth/google`  `{ "credential": "<google-id-token>" }`
- `POST /api/auth/register`
- `GET  /api/auth/session`  header `Authorization: Bearer <token>`
- `POST /api/auth/logout`
- `POST /api/auth/approve?email=someone@domain.com`

## React app

```
VITE_API_BASE=http://localhost:8000/api
VITE_USE_MOCK_API=false
VITE_GOOGLE_CLIENT_ID=<same client id>
```

And send the token on later calls:

```
Authorization: Bearer <token>
```

## Run standalone

```bash
uvicorn main:app --reload --port 8000
```
