from newsapi.newsapi_client import NewsApiClient
import os
from dotenv import load_dotenv
from .news_summ import get_news
import uuid
from db.database_service import DatabaseService
from factcheck_instance import fact_checker_instance

load_dotenv(dotenv_path=".env")

class NewsFetcher:
    def __init__(self):
        self.newsapi = NewsApiClient(api_key=os.environ.get('NEWS_API_KEY'))
        self.db_service = DatabaseService()
        self.fact_checker = fact_checker_instance

    def fetch_initial_news(self):
    # Fetch first batch of 200 news articles
        news = self.newsapi.get_top_headlines(language='en', page=1, page_size=100)
        
        if news['articles']:
            # Store news articles in database with processed=False flag
            processed_articles = [article for article in news['articles']]
            self.db_service.store_news(processed_articles)
            return True
        return False

        
    def process_single_news(self):
        news = self.db_service.get_unprocessed_news()

        if not news:
            # Pre-fetch new news before clearing database
            new_news = self.newsapi.get_top_headlines(language='en', page=1, page_size=100)
            if new_news['articles']:
                # Start batch operations
                batch = self.db_service.db.batch()
                
                # Get all processed news
                old_docs = self.db_service.news_ref.where('processed', '==', True).get()
                
                # Delete old news and their factchecks
                for doc in old_docs:
                    batch.delete(doc.reference)  # Delete news
                    batch.delete(self.db_service.factcheck_ref.document(doc.id))  # Delete factcheck
                
                # Commit deletions
                batch.commit()
                
                # Store new news
                self.db_service.store_news(new_news['articles'])
                # Process first new article immediately
                return self.process_single_news()
            
            self.fetch_initial_news()
            return {'status': 'refresh', 'content': 'Refreshing news database'}
        
        news_text = get_news(news['url'])
        if news_text['status'] == 'error' or len(news_text["summary"]) == 0:
            # remove the news from the database
            self.db_service.news_ref.document(news['id']).delete()
            return { "status": "error", "content": "Error fetching news" }
        
        fact_check_result = self.fact_checker.generate_report(news_summ=news_text['summary'])
        
        article_object = {
            "id": str(uuid.uuid4()),
            "article": news['title'],
            "full_text": news_text,
            "fact_check": {
                "detailed_analysis" : {
                    "overall_analysis" : fact_check_result["detailed_analysis"]["overall_analysis"],
                    "claim_analysis" : fact_check_result["detailed_analysis"]["claim_analysis"],
                    "source_analysis" : fact_check_result["source_credibility"]
                }
            },
            "sources": fact_check_result["sources"]
        }

        self.db_service.store_factcheck(news['id'], article_object)
        return {
            "status": "success",
            "content": article_object,
        }

    # def fetch_and_produce(self):
        # try:
        #     # If pending news exists, return random articles from it
        #     print("Pending news exists")
        #     if self.pending_news:
        #        ans = self.process_single_news()
        #        return ans
            
        #     news = self.newsapi.get_top_headlines(language='en', page=1, page_size=20)
            
        #     if not news['articles']:
        #         print(len(news['articles']))
        #         print(news['articles'])
        #         raise Exception("No news found")
            
        #     self.pending_news.extend(news['articles'])
        #     print(f"Pending news: {len(self.pending_news)}")
        #     print(self.pending_news)
            
        #     ans = self.process_single_news()
        #     return ans
        
        # except Exception as e:
        #     print(f"Error fetching news: {e}")
        #     return {
        #         "status": "error",
        #         "content": None
        #     }