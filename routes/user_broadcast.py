from fastapi import APIRouter
from pydantic import BaseModel
from fc.news_summ import get_news
from fc.fact_checker import FactChecker
from db.database_service import DatabaseService
from datetime import datetime
import os
from pusher_api import pusher_client
from factcheck_instance import fact_checker_instance

router = APIRouter()
db_service = DatabaseService()

class UserInput(BaseModel):
    title: str
    text: str
    name: str

@router.post("/user-broadcast")
async def create_user_broadcast(user_input: UserInput):
    fact_checker = fact_checker_instance
    
    factcheck_result = fact_checker.generate_report(user_input.text)
    
    broadcast_data = {
        "title": user_input.title,
        "text": user_input.text,
        "user_name": user_input.name,
        "factcheck": factcheck_result,
        "timestamp": datetime.now().isoformat()
    }
    
    _, doc_id = db_service.store_user_broadcast(broadcast_data)
    broadcast_data['id'] = doc_id
    
    # Trigger pusher event
    pusher_client.trigger('user-channel', 'new-broadcast', broadcast_data)
    
    return {"status": "success", "data": broadcast_data}

@router.get("/user-broadcasts")
async def get_user_broadcasts():
    broadcasts = db_service.get_all_user_broadcasts()
    return {"status": "success", "content": broadcasts}
