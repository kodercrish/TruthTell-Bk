from newspaper import Article
import nltk
import os


nltk_data_dir = "nltk_data"
nltk.data.path.insert(0, nltk_data_dir)

def get_news(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        article.nlp()
        
        return {
            'status': 'success',
            'summary': article.summary,
            'title': article.title,
            'url': url
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }
