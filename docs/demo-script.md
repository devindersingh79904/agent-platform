# Final Target Demo Script

Follow these steps to demonstrate the end-to-end execution of Devinder AI Agent Studio:

1. **Reset Database**:
   ```bash
   make reset-db
   ```
   *Assert terminal prints:*
   ```text
   Database reset and seeded successfully.
   Seeded agents: 8
   Templates available: 2
   ```

2. **Start Dev Servers**:
   ```bash
   make dev
   ```

3. **Navigate to App**:
   Open `http://localhost:3000`.

4. **Verify Agents**:
   Go to the **Agents** tab. Verify the following 8 agents are listed:
   - Coordinator Agent, Research Agent, Writer Agent, Reviewer Agent, Support Agent, Knowledge Agent, Resolution Agent, Escalation Agent.

5. **Instantiate Template**:
   Go to the **Templates** tab. Locate the "Research → Write → Review" template card and click **Create Workflow**.

6. **Graph Observability**:
   You will be redirected to the **Workflow Builder**. Verify that the React Flow workspace correctly loads the real nodes and edges from the backend template definition.

7. **Graph Coordinate Preservation**:
   Drag any agent node to a new location. Click **Save**. Refresh the page. Verify the node maintains the updated position coordinates.

8. **Tool Node Configuration**:
   Click **Tool** in the Workflow Builder toolbar. Select `calculator_tool`, set:
   ```json
   {"expression": "10 + 20"}
   ```
   Add the node, connect it into the workflow, click **Save**, and refresh. Verify the tool node still displays the selected tool and saved config.

9. **LLM-Directed Tool Calling**:
   Edit or add an **Agent** node and select an agent whose `tools_json` includes `calculator_tool`. Run with:
   ```text
   calculate 10 + 20
   ```
   Verify the AGENT node sends the calculator schema to the LLM, the LLM requests `calculator_tool`, the runtime executes the requested tool, the tool result is sent back to the LLM, and the final Agent Message uses the result. In Run Monitor, the tool call should appear with source `LLM_TOOL_CALL`.

10. **Execute Run**:
   Type the input query in the text input box:
   ```text
   needs revision: Research AI agents for customer support and create an executive summary.
   ```
   *(The "needs revision" prefix will trigger a conditional loop rejection by the Reviewer Agent on the first pass).*
   Click **Run**.

11. **Observability Event Stream**:
   You will automatically navigate to `/runs/{real_run_id}`.
   Verify that:
   - Status transitions from QUEUED → RUNNING → COMPLETED.
   - WebSocket events log active states in the logs terminal.
   - Message panel renders `TASK_HANDOFF` messages containing prompt payloads.
   - Tool calls show executing inputs and output results.
   - Token Usage and Cost charts populate.

12. **Persisted History Reload**:
    Refresh the browser page. Verify that all historical messages, tool logs, run metrics, and final output data reloads successfully from the database.

13. **WebSocket Resume**:
    Reconnect Run Monitor with a `last_event_id` query parameter. Verify missed events are replayed from persisted `RunLog` history before new live events are streamed.
