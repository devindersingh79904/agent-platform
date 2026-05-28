from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.messages import ResponseMessage
from app.models.models import ChannelMessage
from app.utils.response_builder import paginated_response

router = APIRouter()

@router.get("")
def get_channel_messages(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(ChannelMessage).order_by(ChannelMessage.created_at.desc())
    total = query.count()
    messages = query.offset((page - 1) * size).limit(size).all()
    return paginated_response(request, ResponseMessage.CHANNEL_MESSAGES_FETCHED, messages, page, size, total)
