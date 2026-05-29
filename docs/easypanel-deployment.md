# EasyPanel Deployment

This repository is configured for quick deployment on [EasyPanel](https://easypanel.io/) using SQLite as a persistent database for demonstrations.

## Recommended Services

To fully run Devinder AI Agent Studio, you need to create the following four services in EasyPanel:
1. `backend-api`
2. `frontend`
3. `scheduler-worker`
4. `telegram-worker`

All backend-based services (`backend-api`, `scheduler-worker`, `telegram-worker`) must share the exact same persistent volume mounted at `/app/data` to use the same SQLite database.

## Service 1: backend-api

- **Type**: App
- **Build context**: `backend/`
- **Dockerfile**: `backend/Dockerfile`
- **Public port**: `8000`
- **Command**:
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port 8000
  ```

**Volume**:
Host/EasyPanel volume -> `/app/data`

**Environment Variables**:
```env
APP_NAME=Devinder AI Agent Studio
DATABASE_URL=sqlite:///./data/agent_studio.db
LLM_PROVIDER=openai
USE_MOCK_LLM=false
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4o-mini
BACKEND_URL=https://your-backend-domain.com
CORS_ALLOWED_ORIGINS=https://your-frontend-domain.com
API_AUTH_ENABLED=false
```

## Service 2: frontend

- **Type**: App
- **Build context**: `frontend/`
- **Dockerfile**: `frontend/Dockerfile`
- **Public port**: `80`

**Build Arguments** (Vite requires these at build time):
```env
VITE_API_BASE_URL=https://your-backend-domain.com/api
VITE_WS_BASE_URL=wss://your-backend-domain.com
VITE_APP_NAME=Devinder AI Agent Studio
VITE_API_KEY=
```

**Environment Variables** (For completeness, though Vite uses Build Args):
```env
VITE_API_BASE_URL=https://your-backend-domain.com/api
VITE_WS_BASE_URL=wss://your-backend-domain.com
VITE_APP_NAME=Devinder AI Agent Studio
```
*Note: If backend or frontend domains change, you must rebuild the frontend service.*

## Service 3: scheduler-worker

- **Type**: App
- **Build context**: `backend/`
- **Dockerfile**: `backend/Dockerfile`
- **Public port**: none
- **Command**:
  ```bash
  python -m app.scheduler.scheduler_worker
  ```

**Volume**:
Mount the *same persistent volume* used by backend-api -> `/app/data`

**Environment Variables**:
Use the same `DATABASE_URL` and OpenAI settings as `backend-api`.

## Service 4: telegram-worker

- **Type**: App
- **Build context**: `backend/`
- **Dockerfile**: `backend/Dockerfile`
- **Public port**: none
- **Command**:
  ```bash
  python -m app.channels.telegram_worker
  ```

**Volume**:
Mount the *same persistent volume* used by backend-api -> `/app/data`

**Environment Variables**:
```env
DATABASE_URL=sqlite:///./data/agent_studio.db
TELEGRAM_BOT_TOKEN=your_bot_token
DEFAULT_TELEGRAM_WORKFLOW_ID=your_default_workflow_id
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4o-mini
BACKEND_URL=https://your-backend-domain.com
```
