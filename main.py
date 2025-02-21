from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from routes.news_fetch import news_router
from routes.user_inputs import input_router
import nest_asyncio
nest_asyncio.apply()
from fc.newsfetcher import NewsFetcher
from pusher import pusher
import os
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler

news_fetcher = NewsFetcher()

pusher_client = pusher.Pusher(
    app_id=os.getenv('PUSHER_APP_ID'),
    key=os.getenv('PUSHER_KEY'),
    secret=os.getenv('PUSHER_SECRET'),
    cluster=os.getenv('PUSHER_CLUSTER'),
    ssl=True
)

async def fetch_and_broadcast_news():
    print("Fetching and broadcasting news...")
    try:
        
        news_data = await news_fetcher.fetch_and_produce()

        if news_data["status"] == "success" :
            pusher_client.trigger('news-channel', 'news-update', news_data["content"])
            print(f"Successfully broadcasted article: {news_data['content']}")
    except Exception as e:
        print(f"Error in fetch_and_broadcast_news: {e}")

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(fetch_and_broadcast_news, 'interval', minutes=3)
    print("Scheduler started. Job Added.")
    await fetch_and_broadcast_news()
    print("First time")
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
