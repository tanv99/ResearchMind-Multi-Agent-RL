
import requests
import arxiv
import time
import hashlib
import json
import os
from typing import List, Dict
from src.utils import rate_limit


class CachedAPI:
    """Base class with caching functionality"""
    
    def __init__(self):
        self.cache_dir = 'results/cache/api'
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def get_cache_key(self, query, source):
        """Generate cache key from query"""
        key_str = f"{source}_{query}".encode('utf-8')
        return hashlib.md5(key_str).hexdigest()
    
    def get_cached(self, cache_key):
        """Retrieve from cache"""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except:
                return None
        return None
    
    def save_cache(self, cache_key, data):
        """Save to cache"""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        try:
            with open(cache_file, 'w') as f:
                json.dump(data, f)
        except:
            pass


class OpenAlexAPI(CachedAPI):
    """
    OpenAlex API client.
    Rate limit: 10 requests/second (polite use recommended).
    No API key required. Much better than OpenAlex.
    """
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://api.openalex.org/works"
        self.session = requests.Session()
        # Polite pool: identify yourself
        self.session.headers.update({'User-Agent': 'mailto:your.email@example.com'})
    
    @rate_limit(max_per_minute=100)  # 10/sec = 600/min, use 100 to be polite
    def search_papers(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search OpenAlex for papers.
        
        Args:
            query: Search query string
            limit: Max number of papers to return
            
        Returns:
            List of paper dictionaries
        """
        # Check cache
        cache_key = self.get_cache_key(query, 'openalex')
        cached = self.get_cached(cache_key)
        if cached:
            return cached
        
        params = {
            'search': query,
            'per_page': min(limit, 200),  # OpenAlex max is 200
            'sort': 'cited_by_count:desc'
        }
        
        # Retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.session.get(self.base_url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', [])
                    
                    # Convert to standard format
                    papers = []
                    for work in results:
                        # Extract abstract (can be in multiple places)
                        abstract = None
                        if work.get('abstract_inverted_index'):
                            # Reconstruct abstract from inverted index
                            inv_index = work['abstract_inverted_index']
                            words = [''] * (max(max(positions) for positions in inv_index.values()) + 1)
                            for word, positions in inv_index.items():
                                for pos in positions:
                                    words[pos] = word
                            abstract = ' '.join(words)
                        
                        papers.append({
                            'title': work.get('title', 'No title'),
                            'abstract': abstract or work.get('display_name', 'No abstract available'),
                            'year': work.get('publication_year', 0),
                            'citationCount': work.get('cited_by_count', 0),
                            'authors': [{'name': a.get('author', {}).get('display_name', 'Unknown')} 
                                       for a in work.get('authorships', [])],
                            'url': work.get('id', '')
                        })
                    
                    # Cache result
                    self.save_cache(cache_key, papers)
                    return papers
                
                elif response.status_code == 429:
                    # Rate limited (rare with OpenAlex)
                    time.sleep(5)
                    continue
                
                elif response.status_code >= 500:
                    if attempt < max_retries - 1:
                        time.sleep(2 * (attempt + 1))
                        continue
                    return []
                
                else:
                    print(f"OpenAlex error: {response.status_code}")
                    return []
                    
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1))
                    continue
                return []
            
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1))
                    continue
                print(f"OpenAlex error: {e}")
                return []
        
        return []


class ArxivAPI(CachedAPI):
    """arXiv API client with caching"""
    
    def __init__(self):
        super().__init__()
        self.client = arxiv.Client()
    
    @rate_limit(max_per_minute=20)
    def search_papers(self, query: str, limit: int = 10) -> List[Dict]:
        """Search arXiv with caching"""
        
        cache_key = self.get_cache_key(query, 'arxiv')
        cached = self.get_cached(cache_key)
        if cached:
            return cached
        
        search = arxiv.Search(
            query=query,
            max_results=limit,
            sort_by=arxiv.SortCriterion.Relevance
        )
        
        papers = []
        try:
            for result in self.client.results(search):
                papers.append({
                    'title': result.title,
                    'abstract': result.summary,
                    'year': result.published.year,
                    'authors': [{'name': a.name} for a in result.authors],
                    'url': result.entry_id,
                    'citationCount': 0
                })
            
            self.save_cache(cache_key, papers)
                
        except Exception as e:
            print(f"arXiv error: {e}")
        
        return papers


class ResearchToolkit:
    """
    Unified interface to research APIs.
    Uses OpenAlex (no rate limiting) + arXiv.
    """
    
    def __init__(self):
        self.openalex = OpenAlexAPI()
        self.arxiv = ArxivAPI()
        self.call_count = {'openalex': 0, 'arxiv': 0}
        self.failure_count = {'openalex': 0, 'arxiv': 0}
    
    def search(self, query: str, source: str, limit: int = 10) -> List[Dict]:
        """
        Search papers from specified source.
        
        Args:
            query: Search query string
            source: 'openalex' or 'arxiv'
            limit: Max papers to return
        
        Returns:
            List of paper dictionaries
        """
        self.call_count[source] = self.call_count.get(source, 0) + 1
        
        try:
            if source == 'openalex':
                papers = self.openalex.search_papers(query, limit)
            elif source == 'arxiv':
                papers = self.arxiv.search_papers(query, limit)
            else:
                print(f"Unknown source: {source}")
                papers = []
            
            if not papers:
                self.failure_count[source] = self.failure_count.get(source, 0) + 1
            
            return papers
        
        except Exception as e:
            print(f"Search error for {source}: {e}")
            self.failure_count[source] = self.failure_count.get(source, 0) + 1
            return []
    
    def get_stats(self) -> Dict:
        """Return API usage statistics"""
        return {
            'total_calls': sum(self.call_count.values()),
            'by_source': self.call_count.copy(),
            'failures': self.failure_count.copy(),
            'success_rate': {
                src: 1 - (self.failure_count.get(src, 0) / max(1, self.call_count.get(src, 1)))
                for src in self.call_count.keys()
            }
        }
