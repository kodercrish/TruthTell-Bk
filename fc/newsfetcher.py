from newsapi.newsapi_client import NewsApiClient
import os
from dotenv import load_dotenv
from .news_summ import get_news
from .fact_checker import FactChecker
from .expAi import explain_factcheck_result, generate_visual_explanation
import uuid
import random

load_dotenv(dotenv_path=".env")

class NewsFetcher:
    def __init__(self):
        self.newsapi = NewsApiClient(api_key=os.environ.get('NEWS_API_KEY'))
        self.pending_news = []
        self.fact_checker = FactChecker(
            groq_api_key=os.getenv("GROQ_API_KEY"),
            serper_api_key=os.getenv("SERPER_API_KEY")
        )
        
    def process_single_news(self):
        article =  self.pending_news[-1]
        self.pending_news.pop()
        url = article['url']
        
        # Get full text
        news_text = get_news(url)
        if news_text['status'] == 'error':
            self.process_single_news()
        
        fact_check_result = self.fact_checker.generate_report(news_text['summary'])
        
        article_object = {
            "id": str(uuid.uuid4()),
            "article": article['title'],
            "full_text": news_text,
            "fact_check": {
                "detailed_analysis" : {
                    "overall_analysis" : fact_check_result["detailed_analysis"]["overall_analysis"],
                    "claim_analysis" : fact_check_result["detailed_analysis"]["claim_analysis"]
                }
            }
        }
        
        return {
            "status": "success",
            "content": article_object,
        }

    def fetch_and_produce(self):
        try:
            # If pending news exists, return random articles from it
            print("Pending news exists")
            if self.pending_news:
               ans = self.process_single_news()
               return ans
            
            news = self.newsapi.get_top_headlines(language='en', page=1, page_size=20)
            
            if not news['articles']:
                print(len(news['articles']))
                print(news['articles'])
                raise Exception("No news found")
            
            self.pending_news.extend(news['articles'])
            print(f"Pending news: {len(self.pending_news)}")
            print(self.pending_news)
            
            ans = self.process_single_news()
            return ans
        
        except Exception as e:
            print(f"Error fetching news: {e}")
            return {
                "status": "error",
                "content": None
            }