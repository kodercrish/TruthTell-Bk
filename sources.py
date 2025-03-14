import requests
import os
import json

# send a get request to this url
# https://newsdata.io/api/1/news?apikey=YOUR_API_KEY&country=ru,ua
def get_news():
    url = f"https://newsdata.io/api/1/sources?apikey={os.environ.get("NEWSDATA_API_KEY")}&country=in&prioritydomain=top&language=en"
    response = requests.get(url)
    return response.json()

def save_news_to_file(filename="news_sources_en.json"):
    """
    Get news data and save it to a JSON file
    
    Args:
        filename (str): The name of the file to save the data to
    
    Returns:
        dict: The news data that was saved
    """
    news_data = get_news()
    
    # Save to file
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(news_data, f, indent=4)
    
    print(f"News data saved to {filename}")
    return news_data

# If this file is run directly, save the news data
if __name__ == "__main__":
    save_news_to_file()
