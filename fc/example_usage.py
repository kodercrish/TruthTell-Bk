from newsfetcher import NewsFetcher
import nest_asyncio
nest_asyncio.apply()

news_fetcher = NewsFetcher()

async def bhaago():
    res = await news_fetcher.fetch_and_produce()
    res_consume = news_fetcher.glassflow.data_sink.consume()

if __name__ == "__main__":
    import asyncio
    asyncio.run(bhaago())