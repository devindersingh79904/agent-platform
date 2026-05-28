from pydantic import BaseModel
from typing import Any, Dict, Optional

class ToolResult(BaseModel):
    success: bool
    output: Dict[str, Any]
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}

class ToolInterface:
    name: str
    description: str
    input_schema: Dict[str, Any]
    
    async def execute(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> ToolResult:
        raise NotImplementedError
