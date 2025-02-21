import json
import requests
import bs4
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor
import os
from web_helper import crawl_web, is_tag_visible

class SerperSearch:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://google.serper.dev/search"
        self.headers = {
            'X-API-KEY': api_key,
            'Content-Type': 'application/json'
        }

    def search(self, query: str, num_results: int = 3, extend_snippets: bool = True) -> List[Dict]:
        # Initial search request
        payload = {
            'q': query,
            'num': num_results,
            'autocorrect': False
        }
        
        response = requests.post(
            self.base_url,
            headers=self.headers,
            json=payload
        )
        
        if response.status_code != 200:
            return []

        results = response.json()
        
        # Handle answer box if present
        if 'answerBox' in results:
            answer_box = results['answerBox']
            return [{
                'title': 'Google Answer Box',
                'link': answer_box.get('link', 'Google Answer Box'),
                'snippet': answer_box.get('answer', answer_box.get('snippet', '')),
                'position': 0,
                'domain': 'Google Answer Box'
            }]

        # Process organic results
        organic_results = results.get('organic', [])[:num_results]
        
        # Prepare for web crawling if snippet extension is requested
        if extend_snippets:
            query_url_dict = {
                str(query): [result['link'] for result in organic_results]
            }
            
            # Crawl web pages for extended content
            crawl_responses = crawl_web(query_url_dict)
            
            # Process crawled content
            extended_snippets = self._process_crawled_content(
                crawl_responses, 
                [result.get('snippet', '') for result in organic_results]
            )
            
            # Combine original results with extended snippets
            return [
                {
                    'title': result.get('title', ''),
                    'link': result.get('link', ''),
                    'snippet': extended_snippet,
                    'position': result.get('position', i),
                    'domain': result.get('domain', ''),
                    'date': result.get('date', '')
                }
                for i, (result, extended_snippet) in enumerate(zip(organic_results, extended_snippets))
            ][:4]
        
        return [
            {
                'title': result.get('title', ''),
                'link': result.get('link', ''),
                'snippet': result.get('snippet', ''),
                'position': result.get('position', i),
                'domain': result.get('domain', ''),
                'date': result.get('date', '')
            }
            for i, result in enumerate(organic_results)
        ][:4]

    def _process_crawled_content(self, crawl_responses, original_snippets) -> List[str]:
        def extend_snippet(response, original_snippet, flag):
            if not flag or not response or '.pdf' in str(response.url):
                return original_snippet
            
            try:
                soup = bs4.BeautifulSoup(response.text, 'html.parser')
                text = soup.get_text()
                
                # Find the snippet context
                snippet_start = text.find(original_snippet[:50])  # Use first 50 chars to find match
                if snippet_start == -1:
                    return original_snippet
                
                # Extract extended context
                pre_context = 0
                post_context = 500
                start = max(0, snippet_start - pre_context)
                end = min(len(text), snippet_start + len(original_snippet) + post_context)
                
                extended_text = text[start:end].strip()
                return f"{extended_text}..."
            except Exception:
                return original_snippet

        with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            extended_snippets = list(executor.map(
                lambda x: extend_snippet(x[0][1], x[1], x[0][0]),
                zip(crawl_responses, original_snippets)
            ))
            
        return extended_snippets

    def batch_search(self, queries: List[str], num_results: int = 5) -> Dict[str, List[Dict]]:
        """
        Perform batch searches for multiple queries
        """
        url = "https://google.serper.dev/search"
        
        queries_data = [{"q": query, "autocorrect": False} for query in queries]
        payload = json.dumps(queries_data)
        
        response = requests.post(url, headers=self.headers, data=payload)
        
        if response.status_code != 200:
            return {}
            
        results = response.json()
        return {
            query: self._process_single_response(response_data, num_results)
            for query, response_data in zip(queries, results)
        }
    
    def _process_single_response(self, response_data: Dict, num_results: int) -> List[Dict]:
        if 'answerBox' in response_data:
            return [{
                'title': 'Google Answer Box',
                'link': 'Answer Box',
                'snippet': response_data['answerBox'].get('answer', response_data['answerBox'].get('snippet', '')),
                'position': 0,
                'domain': 'Google Answer Box'
            }]
            
        return [
            {
                'title': result.get('title', ''),
                'link': result.get('link', ''),
                'snippet': result.get('snippet', ''),
                'position': i,
                'domain': result.get('domain', ''),
                'date': result.get('date', '')
            }
            for i, result in enumerate(response_data.get('organic', [])[:num_results])
        ]
