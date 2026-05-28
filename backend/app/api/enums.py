from fastapi import APIRouter, Request

from app.core.constants import EdgeCondition, ErrorCode, NodeType, RunStatus, WebSocketEventType
from app.core.messages import ResponseMessage
from app.utils.response_builder import success_response

router = APIRouter()


def enum_values(enum_cls):
    return {member.name: member.value for member in enum_cls}


@router.get("")
def get_enums(request: Request):
    return success_response(request, ResponseMessage.ENUMS_FETCHED, {
        "node_types": enum_values(NodeType),
        "run_statuses": enum_values(RunStatus),
        "edge_conditions": enum_values(EdgeCondition),
        "websocket_event_types": enum_values(WebSocketEventType),
        "error_codes": enum_values(ErrorCode),
    })
