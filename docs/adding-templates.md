# How to Add a New Workflow Template

Follow these steps to register a new workflow template:

1. **Update templates.py**:
   In `backend/app/api/templates.py`, append your config to the `TEMPLATES` dict:
   ```python
   TEMPLATES = {
       # ...
       "tpl_custom_translation": {
           "name": "Translation Workflow",
           "description": "START -> Translator Agent -> Reviewer -> END",
           "nodes": [
               {"id": "t_start", "type": "START", "agent_id": None, "x": 100, "y": 150},
               {"id": "t_trans", "type": "AGENT", "agent_id": "translator_agent", "x": 300, "y": 150},
               {"id": "t_review", "type": "AGENT", "agent_id": "reviewer_agent", "x": 500, "y": 150},
               {"id": "t_end", "type": "END", "agent_id": None, "x": 700, "y": 150}
           ],
           "edges": [
               {"source": "t_start", "target": "t_trans", "type": "always"},
               {"source": "t_trans", "target": "t_review", "type": "always"},
               {"source": "t_review", "target": "t_end", "type": "always"}
           ]
       }
   }
   ```

2. **Restart Server**:
   Restart the backend container or local server. The new template card will instantly render on the **Templates** UI page.
