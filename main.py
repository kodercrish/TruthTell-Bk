from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from routes.news_fetch import news_router
from routes.user_inputs import input_router
import nest_asyncio
nest_asyncio.apply()
from fc.newsfetcher import NewsFetcher
import os
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from routes.user_broadcast import router
from pusher_api import pusher_client
from routes.video_analysis import video_router
from routes.image_analysis import image_router
from routes.audio_analysis import audio_router
from routes.deepfake_audio import deepfake_audio_router
from routes import video_broadcast
from routes.nlp_analysis import nlp_router
from routes.deepfake_detection import deepfake_router

news_fetcher = NewsFetcher()

async def fetch_and_broadcast_news():
    try:
        news_data = news_fetcher.process_single_news()

        if news_data["status"] == "refresh":
            pusher_client.trigger('news-channel', 'refresh-news', {
                'message': 'Refreshing news database'
            })
        elif news_data["status"] == "success":
            pusher_client.trigger('news-channel', 'fact-check', news_data["content"])
            
    except Exception as e:
        print(f"Error in fetch_and_broadcast_news: {e}")

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    news_docs = news_fetcher.db_service.news_ref.limit(1).get()

    if len(list(news_docs)) == 0:
        news_fetcher.fetch_initial_news()
    
    scheduler.add_job(fetch_and_broadcast_news, 'interval', seconds=60000000)
    # await fetch_and_broadcast_news()
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(news_router, tags=["News"])
app.include_router(input_router, tags=["User Inputs"])
app.include_router(router, tags=["User Broadcast"])
app.include_router(video_router, tags=["Video Analysis"])
app.include_router(image_router, tags=["Image Analysis"])
app.include_router(audio_router, tags=["Audio Analysis"])
app.include_router(deepfake_audio_router, tags=["Audio Detection"])
app.include_router(video_broadcast.router)
app.include_router(nlp_router, prefix="/nlp", tags=["NLP Analysis"])
app.include_router(deepfake_router, prefix="/deepfake", tags=["Deepfake Detection"])
@app.get("/")
def read_root():
    return {"message": "Welcome to the API"}

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
