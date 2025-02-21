from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from fc.newsfetcher import NewsFetcher
import asyncio

from pydantic import BaseModel

class UrlInput(BaseModel):
    url: str

class TextInput(BaseModel):
    text: str

load_dotenv()

news_router = APIRouter()

@news_router.websocket("/ws/news")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    while True:
        try:
            news_fetcher = NewsFetcher()
            news_data = await news_fetcher.fetch_and_produce()
            
            if news_data["status"] == "success":
                await websocket.send_json(news_data)
            
            # Wait for 1 minutes before fetching new data
            await asyncio.sleep(75)
            
        except WebSocketDisconnect:
            break
        except Exception as e:
            error_message = {"status": "error", "message": str(e)}
            await websocket.send_json(error_message)