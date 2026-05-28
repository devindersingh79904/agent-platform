import os
import re

def test_alembic_revision_is_001():
    # Verify migration file exists
    migrations_dir = os.path.join(os.path.dirname(__file__), "..", "alembic", "versions")
    files = [f for f in os.listdir(migrations_dir) if f.endswith(".py")]
    
    assert len(files) == 1, "There should be exactly one initial migration file"
    filename = files[0]
    
    assert filename == "001_initial_complete_schema.py", "Migration must be named 001_initial_complete_schema.py"
    
    # Read the file and check the revision string
    with open(os.path.join(migrations_dir, filename), "r") as f:
        content = f.read()
    
    assert "revision: str = '001'" in content or "revision = '001'" in content or 'revision = "001"' in content, "Revision string '001' not found in migration"
