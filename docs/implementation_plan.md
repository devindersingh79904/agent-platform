# Yuno Agent Studio - Implementation Plan

This document outlines the end-to-end plan to implement the Yuno Agent Studio local-first AI Agent Orchestration Platform based on the provided HLD and LLD, and the latest user requirements.

## Goal
Build a working end-to-end platform for creating, configuring, executing, and monitoring collaborative AI agents in a LangGraph-based workflow, complete with a React Flow visual builder, local SQLite persistence, and Telegram integration.

## Proposed Architecture

1. **Backend (Python / FastAPI / LangGraph / SQLAlchemy)**
   - **API Layer**: REST endpoints for managing agents, workflows, templates, and runs. WebSocket endpoint for live execution monitoring.
   - **Service Layer**: Business logic for agents, workflows, tools, memory, limits, and guards.
   - **Runtime Layer**: Converts workflow graph definitions into LangGraph executable states, persisting agent messages and events.
   - **Database Layer**: SQLite (via SQLAlchemy and Pydantic schemas) storing configuration and runtime history. Database will persist across `make dev` commands.
   - **Channel Integration**: Polling-based Telegram handler that triggers workflows and posts responses back.

2. **Frontend (React + Vite / TypeScript / React Flow)**
   - **Pages**: Dashboard, Agents (CRUD), Workflow Builder, Templates Gallery, Run Monitor, Message History.
   - **Components**: AgentForm, WorkflowCanvas, MessagePanel, ToolCallPanel, LogConsole, CostPanel.
   - **Styling**: Tailwind CSS for a clean, simple UI.

3. **Deployment & Scripts**
   - Monorepo structure containing `backend/`, `frontend/`, `docker-compose.yml`, and `Makefile`.
   - Setup designed to run completely locally (`make dev`) without strict dependencies on paid APIs (mock LLMs will be provided if no OpenAI key is set).
   - `make dev` maintains the database state.
   - `make reset-db` added for cleaning to a fresh seed state.
   - **Documentation**: Swagger UI available out of the box via FastAPI at `/docs`. A dedicated `docs` folder will contain guidance on coding and architecture.

## Repository Structure

```text
backend/app/api
backend/app/models
backend/app/schemas
backend/app/services
backend/app/runtime
backend/app/tools
backend/app/channels
backend/app/websocket
backend/app/db
frontend/src/pages
frontend/src/components
frontend/src/api
frontend/src/types
```

## Environment Variables

```text
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
USE_MOCK_LLM=true
MOCK_LLM_DELAY_MS=800
TELEGRAM_BOT_TOKEN=
DEFAULT_TELEGRAM_WORKFLOW_ID=
DATABASE_URL=sqlite:///./yuno_agent_studio.db
```

## API Contract

**Agent APIs:**
- `POST /api/agents`
- `GET /api/agents`
- `GET /api/agents/{agent_id}`
- `PUT /api/agents/{agent_id}`
- `DELETE /api/agents/{agent_id}`

**Workflow APIs:**
- `POST /api/workflows`
- `GET /api/workflows`
- `GET /api/workflows/{workflow_id}`
- `PUT /api/workflows/{workflow_id}`
- `DELETE /api/workflows/{workflow_id}`

**Template APIs:**
- `GET /api/templates`
- `POST /api/templates/{template_id}/create-workflow`

**Run APIs:**
- `POST /api/workflows/{workflow_id}/runs`
- `GET /api/runs`
- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/messages`
- `GET /api/runs/{run_id}/logs`
- `GET /api/runs/{run_id}/tool-calls`
- `GET /api/runs/{run_id}/token-usage`

**WebSocket:**
- `WS /ws/runs/{run_id}`

## Supported Workflow Node Types
- `START`
- `AGENT`
- `TOOL`
- `CONDITION`
- `HUMAN_REVIEW`
- `END`

## Tool Interface
**Tool Interface:**
- `name`
- `description`
- `input_schema`
- `execute(input, context) -> ToolResult`

**ToolResult:**
- `success`
- `output`
- `error`
- `metadata`

## Database Schema Constraints
To ensure accurate persistence, the exact database fields are defined below:

- **Agent**: `id`, `name`, `description`, `role`, `system_prompt`, `model`, `tools_json`, `memory_enabled`, `guardrails_json`, `schedule_config_json`, `channel_config_json`, `limits_json`, `created_at`, `updated_at`
- **Workflow**: `id`, `name`, `description`, `created_at`, `updated_at`
- **WorkflowNode**: `id`, `workflow_id`, `node_type`, `agent_id`, `tool_name`, `config_json`, `position_x`, `position_y`
- **WorkflowEdge**: `id`, `workflow_id`, `source_node_id`, `target_node_id`, `condition_type`, `condition_expression`
- **WorkflowRun**: `id`, `workflow_id`, `status`, `input_json`, `output_json`, `started_at`, `completed_at`, `error_message`
- **AgentMessage**: `id`, `run_id`, `from_agent_id`, `to_agent_id`, `message_type`, `content`, `status`, `created_at`
- **RunLog**: `id`, `run_id`, `level`, `event_type`, `message`, `metadata_json`, `created_at`
- **ToolCall**: `id`, `run_id`, `agent_id`, `tool_name`, `input_json`, `output_json`, `status`, `started_at`, `completed_at`, `error_message`
- **TokenUsage**: `id`, `run_id`, `agent_id`, `model`, `prompt_tokens`, `completion_tokens`, `total_tokens`, `estimated_cost`, `created_at`
- **Memory**: `id`, `agent_id`, `user_id`, `key`, `value`, `created_at`, `updated_at`

## Additional Implementation Requirements

### Acceptance Criteria
- User can create, edit, and delete agents from UI.
- User can create a workflow from a template.
- Workflow graph is visible using React Flow.
- User can run a workflow with custom input.
- Runtime executes through LangGraph, not mocked UI events.
- Each agent handoff is persisted as `AgentMessage`.
- Each tool execution is persisted as `ToolCall`.
- Each important runtime state change is persisted as `RunLog`.
- Token usage and estimated cost are persisted.
- WebSocket streams live run events to the UI.
- Refreshing the run page still shows message history from DB.
- Telegram bot can trigger a workflow and return final response.
- App runs locally with MockLLM even without OpenAI or Telegram keys. MockLLM supports configurable delay via `MOCK_LLM_DELAY_MS`.
- Real OpenAI mode is implemented through `OpenAIClient`; set `USE_MOCK_LLM=false`, `OPENAI_API_KEY`, and `OPENAI_MODEL` to call OpenAI from agent nodes.

### Do Not Fake
- Do not hardcode final outputs.
- Do not generate frontend-only fake logs.
- Do not bypass `RuntimeService`.
- Do not skip message persistence.
- Do not make Telegram required for local startup.

### WebSocket Event Contract
Each event should include the following payload structure:
`event_type, run_id, node_id, agent_id, message, payload, timestamp`

**Supported Event Types:**
`RUN_STARTED`, `RUN_COMPLETED`, `RUN_FAILED`, `NODE_STARTED`, `NODE_COMPLETED`, `AGENT_MESSAGE_CREATED`, `TOOL_CALL_STARTED`, `TOOL_CALL_COMPLETED`, `CONDITION_EVALUATED`, `TOKEN_USAGE_RECORDED`.

### MVP Guardrails
- `max_iterations`, `max_tool_calls`, `allowed_tools`, `blocked_keywords`, `require_review_before_final`

### Seed Agents
The following default agents will be seeded in the database:
- Coordinator Agent
- Research Agent
- Writer Agent
- Reviewer Agent
- Support Agent
- Knowledge Agent
- Resolution Agent
- Escalation Agent

## Tests Required (pytest)
- Create agent
- Update agent
- Delete agent
- Create workflow
- Create workflow from template
- Start workflow run
- Persist agent messages
- Persist tool calls
- Persist token usage
- Enforce `max_iterations`
- WebSocket event emission
- Telegram handler works without real network call

## Demo Script

The final deliverables will be verified using the following script:
1. Run `make dev`.
2. Open http://localhost:3000.
3. Show seeded agents.
4. Create/edit one agent.
5. Open Templates page.
6. Create workflow from Research → Write → Review.
7. Open Workflow Builder and show nodes/edges.
8. Run workflow with: "Research AI agents for customer support and create an executive summary."
9. Open Run Monitor.
10. Show live logs, messages, tool calls, token/cost.
11. Refresh page and show persisted history.
12. Send message from Telegram bot.
13. Show Telegram response and corresponding run in UI.

## README Checklist
The `README.md` must include:
- architecture diagram
- why LangGraph
- why FastAPI
- why Telegram
- setup steps
- demo script
- how to add new agent
- how to add new tool
- how to add new workflow template
- how to add new messaging channel
- known tradeoffs
