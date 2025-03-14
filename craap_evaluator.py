import json
import requests
from bs4 import BeautifulSoup
import datetime
import time
import random
import pandas as pd
from urllib.parse import urlparse
import re
import os
from concurrent.futures import ThreadPoolExecutor

class CRAAPEvaluator:
    def __init__(self, sources_file="news_sources_en.json"):
        """Initialize the CRAAP evaluator with the news sources file."""
        self.sources_file = sources_file
        self.sources = self._load_sources()
        self.results = []
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
    def _load_sources(self):
        """Load news sources from the JSON file."""
        with open(self.sources_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data['results']
    
    def evaluate_all_sources(self, max_sources=None, threads=5):
        """Evaluate all sources or a subset if max_sources is specified."""
        sources_to_evaluate = self.sources[:max_sources] if max_sources else self.sources
        
        print(f"Evaluating {len(sources_to_evaluate)} news sources...")
        
        with ThreadPoolExecutor(max_workers=threads) as executor:
            results = list(executor.map(self.evaluate_source, sources_to_evaluate))
        
        self.results = [r for r in results if r]  # Filter out None results
        return self.results
    
    def evaluate_source(self, source):
        """Evaluate a single news source using the CRAAP method."""
        try:
            print(f"Evaluating: {source['name']} ({source['url']})")
            
            # Basic source info
            evaluation = {
                'id': source['id'],
                'name': source['name'],
                'url': source['url'],
                'description': source['description'],
                'categories': ', '.join(source['category']),
                'languages': ', '.join(source['language']),
                'countries': ', '.join(source['country']),
            }
            
            # Scrape additional data
            site_data = self._scrape_site_data(source['url'])
            
            # Calculate CRAAP scores
            currency_score = self._evaluate_currency(source, site_data)
            relevance_score = self._evaluate_relevance(source, site_data)
            authority_score = self._evaluate_authority(source, site_data)
            accuracy_score = self._evaluate_accuracy(source, site_data)
            purpose_score = self._evaluate_purpose(source, site_data)
            
            # Add scores to evaluation
            evaluation.update({
                'currency_score': currency_score,
                'relevance_score': relevance_score,
                'authority_score': authority_score,
                'accuracy_score': accuracy_score,
                'purpose_score': purpose_score,
                'total_score': currency_score + relevance_score + authority_score + accuracy_score + purpose_score,
                'max_possible_score': 50,  # 10 points max for each of the 5 criteria
                'rating': self._calculate_rating(currency_score + relevance_score + authority_score + accuracy_score + purpose_score)
            })
            
            # Add detailed evaluation notes
            evaluation.update(site_data)
            
            time.sleep(random.uniform(1, 3))  # Be nice to the servers
            return evaluation
            
        except Exception as e:
            print(f"Error evaluating {source['name']}: {str(e)}")
            return None
    
    def _scrape_site_data(self, url):
        """Scrape additional data from the news source website."""
        try:
            data = {
                'has_about_page': False,
                'has_contact_info': False,
                'has_privacy_policy': False,
                'has_terms_of_service': False,
                'has_copyright_info': False,
                'domain_age_years': 0,
                'last_updated': None,
                'social_media_presence': [],
                'ads_level': 'Unknown',
                'citations_found': False,
                'https_enabled': url.startswith('https'),
                'domain': urlparse(url).netloc,
            }
            
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                return data
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check for about page
            about_links = soup.find_all('a', href=True, text=re.compile(r'about', re.I))
            data['has_about_page'] = len(about_links) > 0
            
            # Check for contact info
            contact_links = soup.find_all('a', href=True, text=re.compile(r'contact', re.I))
            data['has_contact_info'] = len(contact_links) > 0
            
            # Check for privacy policy
            privacy_links = soup.find_all('a', href=True, text=re.compile(r'privacy', re.I))
            data['has_privacy_policy'] = len(privacy_links) > 0
            
            # Check for terms of service
            tos_links = soup.find_all('a', href=True, text=re.compile(r'terms', re.I))
            data['has_terms_of_service'] = len(tos_links) > 0
            
            # Check for copyright info
            copyright_text = soup.find(text=re.compile(r'copyright|©', re.I))
            data['has_copyright_info'] = copyright_text is not None
            
            # Check for last updated date
            date_patterns = [
                r'updated on (\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'last updated:? (\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'updated:? (\w+ \d{1,2},? \d{4})'
            ]
            
            for pattern in date_patterns:
                date_match = soup.find(text=re.compile(pattern, re.I))
                if date_match:
                    data['last_updated'] = date_match
                    break
            
            # Check for social media presence
            social_media = ['facebook', 'twitter', 'instagram', 'youtube', 'linkedin']
            for platform in social_media:
                social_links = soup.find_all('a', href=re.compile(platform, re.I))
                if social_links:
                    data['social_media_presence'].append(platform)
            
            # Estimate ad level
            ad_elements = soup.find_all('div', class_=re.compile(r'ad|banner|sponsor', re.I))
            if len(ad_elements) > 10:
                data['ads_level'] = 'High'
            elif len(ad_elements) > 5:
                data['ads_level'] = 'Medium'
            elif len(ad_elements) > 0:
                data['ads_level'] = 'Low'
            else:
                data['ads_level'] = 'Minimal/None'
            
            # Check for citations
            citations = soup.find_all(['cite', 'blockquote'])
            data['citations_found'] = len(citations) > 0
            
            return data
            
        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
            return {}
    
    def _evaluate_currency(self, source, site_data):
        """Evaluate the Currency criterion (0-10 points)."""
        score = 0
        
        # Check if last_fetch date is recent (within last week)
        try:
            last_fetch = datetime.datetime.strptime(source['last_fetch'], "%Y-%m-%d %H:%M:%S")
            days_since_fetch = (datetime.datetime.now() - last_fetch).days
            if days_since_fetch < 1:
                score += 5
            elif days_since_fetch < 7:
                score += 3
            elif days_since_fetch < 30:
                score += 1
        except:
            pass
        
        # Check if the site has been updated recently
        if site_data.get('last_updated'):
            score += 2
        
        # Check if HTTPS is enabled (modern security practice)
        if site_data.get('https_enabled'):
            score += 3
            
        return min(score, 10)  # Cap at 10
    
    def _evaluate_relevance(self, source, site_data):
        """Evaluate the Relevance criterion (0-10 points)."""
        score = 0
        
        # More categories = more relevant to diverse audience
        categories_count = len(source['category'])
        if categories_count > 8:
            score += 5
        elif categories_count > 5:
            score += 3
        elif categories_count > 2:
            score += 2
        else:
            score += 1
            
        # More countries = more global relevance
        countries_count = len(source['country'])
        if countries_count > 10:
            score += 3
        elif countries_count > 5:
            score += 2
        elif countries_count > 1:
            score += 1
            
        # More languages = accessible to more people
        languages_count = len(source['language'])
        if languages_count > 2:
            score += 2
        elif languages_count > 1:
            score += 1
            
        return min(score, 10)  # Cap at 10
    
    def _evaluate_authority(self, source, site_data):
        """Evaluate the Authority criterion (0-10 points)."""
        score = 0
        
        # Check for about page
        if site_data.get('has_about_page'):
            score += 2
            
        # Check for contact information
        if site_data.get('has_contact_info'):
            score += 2
            
        # Check for privacy policy and terms of service
        if site_data.get('has_privacy_policy'):
            score += 1
        if site_data.get('has_terms_of_service'):
            score += 1
            
        # Check priority (lower number typically means higher authority)
        priority = source.get('priority', 10000)
        if priority < 200:
            score += 4
        elif priority < 1000:
            score += 2
        elif priority < 3000:
            score += 1
            
        return min(score, 10)  # Cap at 10
    
    def _evaluate_accuracy(self, source, site_data):
        """Evaluate the Accuracy criterion (0-10 points)."""
        score = 0
        
        # Check for citations
        if site_data.get('citations_found'):
            score += 3
            
        # Check total articles (more content = more opportunity to verify accuracy)
        total_articles = source.get('total_article', 0)
        if total_articles > 100000:
            score += 4
        elif total_articles > 50000:
            score += 3
        elif total_articles > 10000:
            score += 2
        elif total_articles > 1000:
            score += 1
            
        # Check for copyright info (indicates accountability)
        if site_data.get('has_copyright_info'):
            score += 3
            
        return min(score, 10)  # Cap at 10
    
    def _evaluate_purpose(self, source, site_data):
        """Evaluate the Purpose criterion (0-10 points)."""
        score = 0
        
        # Check description length (more detailed = clearer purpose)
        description_length = len(source.get('description', ''))
        if description_length > 200:
            score += 3
        elif description_length > 100:
            score += 2
        elif description_length > 50:
            score += 1
            
        # Check ad level (fewer ads = less commercial bias)
        ads_level = site_data.get('ads_level', 'Unknown')
        if ads_level == 'Minimal/None':
            score += 4
        elif ads_level == 'Low':
            score += 3
        elif ads_level == 'Medium':
            score += 2
        elif ads_level == 'High':
            score += 1
            
        # Check social media presence (engagement with audience)
        social_count = len(site_data.get('social_media_presence', []))
        if social_count > 3:
            score += 3
        elif social_count > 1:
            score += 2
        elif social_count > 0:
            score += 1
            
        return min(score, 10)  # Cap at 10
    
    def _calculate_rating(self, total_score):
        """Calculate a letter rating based on the total score."""
        if total_score >= 45:
            return "A+ (Excellent)"
        elif total_score >= 40:
            return "A (Very Good)"
        elif total_score >= 35:
            return "B+ (Good)"
        elif total_score >= 30:
            return "B (Above Average)"
        elif total_score >= 25:
            return "C+ (Average)"
        elif total_score >= 20:
            return "C (Below Average)"
        elif total_score >= 15:
            return "D (Poor)"
        else:
            return "F (Unreliable)"
    
    def save_results_to_csv(self, filename="craap_evaluation_results.csv"):
        """Save evaluation results to a CSV file."""
        if not self.results:
            print("No results to save.")
            return
            
        df = pd.DataFrame(self.results)
        df.to_csv(filename, index=False)
        print(f"Results saved to {filename}")
    
    def save_results_to_json(self, filename="craap_evaluation_results.json"):
        """Save evaluation results to a JSON file."""
        if not self.results:
            print("No results to save.")
            return
            
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=4)
        print(f"Results saved to {filename}")
    
    def generate_html_report(self, filename="craap_evaluation_report.html"):
        """Generate an HTML report with the evaluation results."""
        if not self.results:
            print("No results to generate report.")
            return
            
        # Sort results by total score (descending)
        sorted_results = sorted(self.results, key=lambda x: x.get('total_score', 0), reverse=True)
        
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>CRAAP Evaluation of News Sources</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    margin: 0;
                    padding: 20px;
                    color: #333;
                }
                h1, h2, h3 {
                    color: #2c3e50;
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                }
                .summary {
                    background-color: #f8f9fa;
                    padding: 20px;
                    border-radius: 5px;
                    margin-bottom: 30px;
                }
                .source-card {
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    padding: 20px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .source-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 15px;
                }
                .source-name {
                    font-size: 1.5em;
                    font-weight: bold;
                    margin: 0;
                }
                .source-rating {
                    font-size: 1.2em;
                    font-weight: bold;
                    padding: 5px 10px;
                    border-radius: 3px;
                    color: white;
                }
                .rating-a-plus {
                    background-color: #2ecc71;
                }
                .rating-a {
                    background-color: #27ae60;
                }
                .rating-b-plus {
                    background-color: #3498db;
                }
                .rating-b {
                    background-color: #2980b9;
                }
                .rating-c-plus {
                    background-color: #f39c12;
                }
                .rating-c {
                    background-color: #e67e22;
                }
                .rating-d {
                    background-color: #e74c3c;
                }
                .rating-f {
                    background-color: #c0392b;
                }
                .score-bar {
                    height: 20px;
                    background-color: #ecf0f1;
                    border-radius: 10px;
                    margin-bottom: 10px;
                    overflow: hidden;
                }
                .score-fill {
                    height: 100%;
                    background-color: #3498db;
                }
                .criteria-scores {
                    display: flex;
                    justify-content: space-between;
                    margin-top: 20px;
                }
                .criteria-score {
                    flex: 1;
                    text-align: center;
                    padding: 10px;
                    border-radius: 5px;
                    margin: 0 5px;
                    background-color: #f8f9fa;
                }
                .criteria-score h4 {
                    margin-top: 0;
                }
                .source-details {
                    margin-top: 20px;
                }
                .detail-row {
                    display: flex;
                    border-bottom: 1px solid #eee;
                    padding: 8px 0;
                }
                .detail-label {
                    flex: 1;
                    font-weight: bold;
                }
                .detail-value {
                    flex: 2;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }
                th, td {
                    padding: 12px 15px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }
                th {
                    background-color: #f8f9fa;
                }
                tr:hover {
                    background-color: #f5f5f5;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>CRAAP Evaluation of News Sources</h1>
                <div class="summary">
                    <h2>Evaluation Summary</h2>
                    <p>Total sources evaluated: {total_sources}</p>
                    <p>Average CRAAP score: {avg_score:.2f}/50</p>
                    <p>Evaluation date: {eval_date}</p>
                </div>
                
                <h2>Sources Ranked by CRAAP Score</h2>
                
                {source_cards}
                
                <h2>Comparison Table</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Source</th>
                            <th>Total Score</th>
                            <th>Rating</th>
                            <th>Currency</th>
                            <th>Relevance</th>
                            <th>Authority</th>
                            <th>Accuracy</th>
                            <th>Purpose</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>
                
                <div class="footer">
                    <p>Generated by CRAAP Evaluator on {eval_date}</p>
                    <p>The CRAAP Test evaluates sources based on Currency, Relevance, Authority, Accuracy, and Purpose.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Calculate summary statistics
        total_sources = len(sorted_results)
        avg_score = sum(r.get('total_score', 0) for r in sorted_results) / total_sources if total_sources > 0 else 0
        eval_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Generate source cards HTML
        source_cards = ""
        for result in sorted_results:
            rating_class = "rating-" + result.get('rating', '').lower().split()[0].replace('+', '-plus')
            
            # Calculate percentage for score bar
            score_percent = (result.get('total_score', 0) / result.get('max_possible_score', 50)) * 100
            
            source_card = f"""
            <div class="source-card">
                <div class="source-header">
                    <h3 class="source-name">{result.get('name', 'Unknown')}</h3>
                    <span class="source-rating {rating_class}">{result.get('rating', 'Not Rated')}</span>
                </div>
                
                <p><a href="{result.get('url', '#')}" target="_blank">{result.get('url', 'No URL')}</a></p>
                <p>{result.get('description', 'No description available.')}</p>
                
                <div class="score-bar">
                    <div class="score-fill" style="width: {score_percent}%;"></div>
                </div>
                <p>Total Score: {result.get('total_score', 0)}/{result.get('max_possible_score', 50)}</p>
                
                <div class="criteria-scores">
                    <div class="criteria-score">
                        <h4>Currency</h4>
                        <p>{result.get('currency_score', 0)}/10</p>
                    </div>
                    <div class="criteria-score">
                        <h4>Relevance</h4>
                        <p>{result.get('relevance_score', 0)}/10</p>
                    </div>
                    <div class="criteria-score">
                        <h4>Authority</h4>
                        <p>{result.get('authority_score', 0)}/10</p>
                    </div>
                    <div class="criteria-score">
                        <h4>Accuracy</h4>
                        <p>{result.get('accuracy_score', 0)}/10</p>
                    </div>
                    <div class="criteria-score">
                        <h4>Purpose</h4>
                        <p>{result.get('purpose_score', 0)}/10</p>
                    </div>
                </div>
                
                <div class="source-details">
                    <h4>Source Details</h4>
                    <div class="detail-row">
                        <span class="detail-label">Categories:</span>
                        <span class="detail-value">{result.get('categories', 'None')}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Languages:</span>
                        <span class="detail-value">{result.get('languages', 'None')}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Countries:</span>
                        <span class="detail-value">{result.get('countries', 'None')}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">HTTPS Enabled:</span>
                        <span class="detail-value">{result.get('https_enabled', False)}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Has About Page:</span>
                        <span class="detail-value">{result.get('has_about_page', False)}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Has Contact Info:</span>
                        <span class="detail-value">{result.get('has_contact_info', False)}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Social Media:</span>
                        <span class="detail-value">{', '.join(result.get('social_media_presence', ['None']))}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Ad Level:</span>
                        <span class="detail-value">{result.get('ads_level', 'Unknown')}</span>
                    </div>
                </div>
            </div>
            """
            source_cards += source_card
        
        # Generate table rows HTML
        table_rows = ""
        for i, result in enumerate(sorted_results, 1):
            table_row = f"""
            <tr>
                <td>{i}</td>
                <td>{result.get('name', 'Unknown')}</td>
                <td>{result.get('total_score', 0)}</td>
                <td>{result.get('rating', 'Not Rated')}</td>
                <td>{result.get('currency_score', 0)}</td>
                <td>{result.get('relevance_score', 0)}</td>
                <td>{result.get('authority_score', 0)}</td>
                <td>{result.get('accuracy_score', 0)}</td>
                <td>{result.get('purpose_score', 0)}</td>
            </tr>
            """
            table_rows += table_row
        
        # Fill in the template
        html = html.format(
            total_sources=total_sources,
            avg_score=avg_score,
            eval_date=eval_date,
            source_cards=source_cards,
            table_rows=table_rows
        )
        
        # Write to file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"HTML report generated: {filename}")

