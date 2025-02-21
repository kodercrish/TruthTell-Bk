from newsapi import NewsApiClient
import os
from dotenv import load_dotenv
from .news_summ import get_news
from .fact_checker import FactChecker
from .expAi import explain_factcheck_result, generate_visual_explanation
import uuid
import json

load_dotenv()

class NewsFetcher:
    def __init__(self):
        self.newsapi = NewsApiClient(api_key=os.getenv('NEWS_API_KEY'))
        self.fetched_pages = self.load_fetched_pages()
        self.fact_checker = FactChecker(
            groq_api_key=os.getenv("GROQ_API_KEY"),
            serper_api_key=os.getenv("SERPER_API_KEY")
        )

    def load_fetched_pages(self):
        try:
            with open('fetched_pages.json', 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            return []

    def save_fetched_pages(self):
        with open('fetched_pages.json', 'w') as file:
            json.dump(self.fetched_pages, file)
        
    async def fetch_and_produce(self):
        try:
            page = 1
            final_articles = []
            
            while len(final_articles) < 2:  # Fetch until we have at least 5 unique articles
                news = self.newsapi.get_top_headlines(language='en', page=page, page_size=5)

                #print("#"*50)
                #print(f"News: {news}")
                #print("#"*60)
                
                if not news['articles']:
                    break
                
                for article in news["articles"]:
                    url = article['url']
                    if url in self.fetched_pages:
                        continue
                    
                    self.fetched_pages.append(url)

                    # Get full text
                    news_text = get_news(url)
                    if news_text['status'] == 'error':
                        continue
                    
                    # Run fact check - it will be run through transformation pipeline
                    fact_check_result = self.fact_checker.generate_report(news_text['text'])
                    
                    
                    explanation = explain_factcheck_result(fact_check_result)

                    # Get visualization data
                    viz_data = generate_visual_explanation(explanation["explanation"])
                
                    # Create article object with unique ID
                    article_object = {
                        "id": str(uuid.uuid4()),
                        "article": article,
                        "full_text": news_text,
                        "fact_check": fact_check_result,
                        "explanation": explanation,
                        "visualization": viz_data
                    }
                    #print("ARTICLE ID: " + article_object["id"])
                    
                    final_articles.append(article_object)
                    
                    if (len(final_articles) >= 1):
                        break

                page += 1  # Move to the next page

            self.save_fetched_pages()
            return {
                "status": "success",
                "content": final_articles
            }

        except Exception as e:
            print(f"Error fetching news: {e}")
            return {
                "status": "error",
                "content": None
            }