import json
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException
from app.api.models import FeedbackRequest, FeedbackResponse

logger = logging.getLogger(__name__)
router = APIRouter()

FEEDBACK_FILE = "feedback.jsonl"

@router.post("/feedback", response_model=FeedbackResponse, summary="Submit feedback on an answer")
async def submit_feedback(request: FeedbackRequest):
    logger.info(f"Received feedback for query {request.query_id}: {request.rating}")
    
    if request.rating not in ["up", "down"]:
        raise HTTPException(status_code=400, detail="Rating must be 'up' or 'down'")
        
    feedback_data = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "query_id": request.query_id,
        "rating": request.rating,
        "comment": request.comment
    }
    
    try:
        # Append to a local JSON Lines file
        with open(FEEDBACK_FILE, "a") as f:
            f.write(json.dumps(feedback_data) + "\n")
            
        return FeedbackResponse(
            status="success",
            message="Feedback submitted successfully. Thank you!"
        )
    except Exception as e:
        logger.error(f"Error saving feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to save feedback")
