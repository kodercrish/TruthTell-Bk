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

    async def fetch_and_produce(self):
        try:
            # If pending news exists, return random articles from it
            if self.pending_news:
                selected_articles = []
                num_articles = min(2, len(self.pending_news))
                
                for _ in range(num_articles):
                    random_article = random.choice(self.pending_news)
                    self.pending_news.remove(random_article)
                    selected_articles.append(random_article)
                
                return {
                    "status": "success",
                    "content": selected_articles
                }

            # If no pending news, fetch new batch
            print("Fetching news...")
            page = 1
            final_articles = []
            
            while len(final_articles) < 1:
                news = self.newsapi.get_top_headlines(language='en', page=page, page_size=20)
                
                if not news['articles']:
                    break
                
                for article in news["articles"]:
                    url = article['url']
                    
                    # Get full text
                    news_text = get_news(url)
                    if news_text['status'] == 'error':
                        continue
                    
                    # Run fact check
                    fact_check_result = self.fact_checker.generate_report(news_text['text'])
                    explanation = explain_factcheck_result(fact_check_result)
                    viz_data = generate_visual_explanation(explanation["explanation"])
                
                    article_object = {
                        "id": str(uuid.uuid4()),
                        "article": article['title'],
                        "full_text": news_text,
                        "fact_check": {
                            "detailed_analysis" : {
                                "overall_analysis" : fact_check_result["detailed_analysis"]["overall_analysis"],
                            }
                        }
                    }
                    
                    final_articles.append(article_object)
                    
                    if len(final_articles) >= 1:
                        break

                self.pending_news = news[1:]
                page += 1

            # Store 18 articles in pending_news and return 2
            print("INFO::  Pending news:", final_articles[0])
            return {
                "status": "success",
                "content": final_articles[0]
            }

        except Exception as e:
            print(f"Error fetching news: {e}")
            return {
                "status": "error",
                "content": None
            }