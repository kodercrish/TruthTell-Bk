from fastapi import APIRouter
from dotenv import load_dotenv
from db.database_service import DatabaseService

from pydantic import BaseModel

class UrlInput(BaseModel):
    url: str

class TextInput(BaseModel):
    text: str

load_dotenv()

news_router = APIRouter()

@news_router.get("/all-news")
async def get_all_news():
    db_service = DatabaseService()
    news_with_factchecks = db_service.get_all_news_with_factchecks()
    return {
        "status": "success",
        "content": news_with_factchecks
    }