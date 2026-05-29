# EasyPanel Deployment

This repository is configured for quick deployment on [EasyPanel](https://easypanel.io/) using SQLite as a persistent database for demonstrations.

## Recommended Services

To fully run Devinder AI Agent Studio, you need to create the following four services in EasyPanel:
1. `backend-api`
2. `frontend`
3. `scheduler-worker`
4. `telegram-worker`

> **Important:**
> - SQLite is acceptable for quick demo deployment.
> - `backend-api`, `scheduler-worker`, and `telegram-worker` must mount the same persistent volume at `/app/data`.
> - Telegram worker uses polling, so it does not need a public port.
> - Scheduler worker does not need a public port.
> - Do not add PostgreSQL now.

## Service 1: backend-api

- **Build Path**: `/backend`
- **Dockerfile**: `Dockerfile`
- **Port**: `8000`
- **Volume**: `/app/data`

**Environment Variables**:
```env
APP_NAME=Devinder AI Agent Studio
DATABASE_URL=sqlite:///./data/agent_studio.db
LLM_PROVIDER=openai
USE_MOCK_LLM=false
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4o-mini
# Use "*" only for demo/testing. For production, set exact frontend domain.
CORS_ALLOWED_ORIGINS=*
```

## Service 2: frontend

- **Build Path**: `/frontend`
- **Dockerfile**: `Dockerfile`
- **Port**: `80`

**Build Arguments** (Vite requires these at build time):
```env
VITE_API_BASE_URL=https://your-backend-domain.com/api
VITE_WS_BASE_URL=wss://your-backend-domain.com
VITE_APP_NAME=Devinder AI Agent Studio
```

## Service 3: scheduler-worker

- **Build Path**: `/backend`
- **Dockerfile**: `Dockerfile.scheduler`
- **Port**: none
- **Volume**: `/app/data`

**Environment Variables**:
```env
DATABASE_URL=sqlite:///./data/agent_studio.db
LLM_PROVIDER=openai
USE_MOCK_LLM=false
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4o-mini
```

## Service 4: telegram-worker

- **Build Path**: `/backend`
- **Dockerfile**: `Dockerfile.telegram`
- **Port**: none
- **Volume**: `/app/data`

**Environment Variables**:
```env
DATABASE_URL=sqlite:///./data/agent_studio.db
TELEGRAM_BOT_TOKEN=your_bot_token
DEFAULT_TELEGRAM_WORKFLOW_ID=your_default_workflow_id
LLM_PROVIDER=openai
USE_MOCK_LLM=false
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4o-mini
BACKEND_URL=https://your-backend-domain.com
```

## Local Build Verification

To verify the Dockerfiles build successfully locally before deploying:

```bash
docker build -t ai-agent-backend ./backend
docker build -t ai-agent-telegram -f backend/Dockerfile.telegram ./backend
docker build -t ai-agent-scheduler -f backend/Dockerfile.scheduler ./backend
```
