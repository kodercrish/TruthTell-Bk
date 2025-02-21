from newspaper import Article
import nltk
import os


nltk_data_dir = "nexus-backend/nltk_data"
nltk.data.path.insert(0, nltk_data_dir)

print(f"Looking for nltk data in: {nltk_data_dir}")

def get_news(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        article.nlp()
        
        return {
            'status': 'success',
            'summary': article.summary,
            'keywords': article.keywords,
            'title': article.title,
            'text': article.text,
            'url': url
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }
