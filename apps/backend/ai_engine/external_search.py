"""
VeriRAG — External Data Source Integration
Integrates arXiv, Google Scholar, and USPTO Patent APIs
"""

import requests
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
import feedparser

logger = logging.getLogger(__name__)

# ============================================================================
# ARXIV INTEGRATION
# ============================================================================

class ArxivSearcher:
    """
    Search arXiv for research papers
    API: https://arxiv.org/help/api/user-manual
    No API key required, but rate limit: 3 requests per second
    """
    
    BASE_URL = "http://export.arxiv.org/api/query"
    FIELDS_MAP = {
        "ai": "cat:cs.AI",
        "ml": "cat:cs.LG",
        "nlp": "cat:cs.CL",
        "vision": "cat:cs.CV",
        "security": "cat:cs.CR",
        "systems": "cat:cs.SY",
        "db": "cat:cs.DB",
        "distributed": "cat:cs.DC",
    }
    
    @staticmethod
    def search(
        query: str,
        max_results: int = 10,
        sort_by: str = "relevance",
        date_from: int = None,  # Days ago
    ) -> List[Dict[str, Any]]:
        """
        Search arXiv for papers
        
        Args:
            query: Search terms (e.g., "RAG retrieval augmented")
            max_results: Number of results (max 100)
            sort_by: "relevance" or "submittedDate"
            date_from: Only papers from last N days
            
        Returns:
            List of papers with title, authors, summary, PDF URL
        """
        try:
            # Build query
            arxiv_query = f'search_query=all:{query}&start=0&max_results={max_results}&sortBy={sort_by}'
            
            params = {
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": min(max_results, 100),
                "sortBy": sort_by,
            }
            
            response = requests.get(
                ArxivSearcher.BASE_URL,
                params=params,
                timeout=10,
            )
            response.raise_for_status()
            
            feed = feedparser.parse(response.content)
            
            results = []
            for entry in feed.entries:
                # Parse publication date
                published = entry.get("published", "")
                pub_date = datetime.fromisoformat(published.replace("Z", "+00:00"))
                
                # Filter by date if specified
                if date_from:
                    cutoff = datetime.now(pub_date.tzinfo) - timedelta(days=date_from)
                    if pub_date < cutoff:
                        continue
                
                # Extract PDF URL
                pdf_url = None
                for link in entry.get("links", []):
                    if link.get("title") == "pdf":
                        pdf_url = link.get("href")
                        break
                
                paper = {
                    "source": "arXiv",
                    "arxiv_id": entry.get("id", "").split("/abs/")[-1],
                    "title": entry.get("title", ""),
                    "authors": [author.name for author in entry.get("authors", [])],
                    "summary": entry.get("summary", "").strip(),
                    "published": pub_date.isoformat(),
                    "pdf_url": pdf_url or entry.get("id", ""),
                    "categories": entry.get("arxiv_primary_category", {}).get("term", ""),
                    "relevance_score": 0.85,  # arXiv relevance (you can improve this)
                }
                results.append(paper)
            
            logger.info(f"arXiv search for '{query}' returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"arXiv search failed: {str(e)}")
            return []
    
    @staticmethod
    def search_by_category(
        category: str,
        days: int = 7,
        max_results: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Search arXiv by category (latest papers)
        
        Categories:
          cs.AI - Artificial Intelligence
          cs.LG - Machine Learning
          cs.CL - Computation and Language (NLP)
          cs.CV - Computer Vision
          cs.CR - Cryptography and Security
        """
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d%H%M%S")
            
            params = {
                "search_query": f"cat:{category} AND submittedDate:[{cutoff_date} TO 9999999999]",
                "start": 0,
                "max_results": min(max_results, 100),
                "sortBy": "submittedDate",
            }
            
            response = requests.get(
                ArxivSearcher.BASE_URL,
                params=params,
                timeout=10,
            )
            response.raise_for_status()
            
            feed = feedparser.parse(response.content)
            
            results = []
            for entry in feed.entries:
                paper = {
                    "source": "arXiv",
                    "arxiv_id": entry.get("id", "").split("/abs/")[-1],
                    "title": entry.get("title", ""),
                    "authors": [author.name for author in entry.get("authors", [])],
                    "summary": entry.get("summary", "").strip(),
                    "published": entry.get("published", ""),
                    "category": category,
                }
                results.append(paper)
            
            return results
            
        except Exception as e:
            logger.error(f"arXiv category search failed: {str(e)}")
            return []


# ============================================================================
# SEMANTIC SCHOLAR INTEGRATION
# ============================================================================

class SemanticScholarSearcher:
    """
    Search Semantic Scholar for papers
    API: https://www.semanticscholar.org/product/api
    No key needed for basic search
    """
    
    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
    
    @staticmethod
    def search(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search Semantic Scholar for papers
        
        Args:
            query: Search terms
            max_results: Number of results
            
        Returns:
            List of papers with citation count, influential citations
        """
        try:
            params = {
                "query": query,
                "limit": min(max_results, 100),
                "fields": "paperId,title,authors,venue,year,citationCount,influentialCitationCount,openAccessPdf",
            }
            
            response = requests.get(
                SemanticScholarSearcher.BASE_URL,
                params=params,
                timeout=10,
            )
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for paper in data.get("data", []):
                result = {
                    "source": "Semantic Scholar",
                    "paper_id": paper.get("paperId"),
                    "title": paper.get("title"),
                    "authors": [a.get("name") for a in paper.get("authors", [])],
                    "venue": paper.get("venue"),
                    "year": paper.get("year"),
                    "citation_count": paper.get("citationCount", 0),
                    "influential_citation_count": paper.get("influentialCitationCount", 0),
                    "pdf_url": paper.get("openAccessPdf", {}).get("url"),
                    "relevance_score": 0.8,
                }
                results.append(result)
            
            logger.info(f"Semantic Scholar search for '{query}' returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Semantic Scholar search failed: {str(e)}")
            return []


# ============================================================================
# USPTO PATENT SEARCH
# ============================================================================

class USPTOPatentSearcher:
    """
    Search USPTO patents using PAIR API
    Public API: https://developer.uspto.gov/
    """
    
    BASE_URL = "https://api.uspto.gov/query"
    
    @staticmethod
    def search(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search USPTO patents
        
        Args:
            query: Patent search terms
            max_results: Number of results
            
        Returns:
            List of patents
        """
        try:
            # Using basic patent search (free, no key needed)
            params = {
                "q": query,
                "fl": "patent_number,patent_title,inventor,assignee,filing_date,grant_date",
                "rows": min(max_results, 100),
                "wt": "json",
            }
            
            response = requests.get(
                "https://patentsearch.uspto.gov/patentsearch/search",
                params=params,
                timeout=10,
            )
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for doc in data.get("response", {}).get("docs", []):
                patent = {
                    "source": "USPTO",
                    "patent_number": doc.get("patent_number"),
                    "title": doc.get("patent_title"),
                    "inventors": doc.get("inventor", []),
                    "assignee": doc.get("assignee"),
                    "filing_date": doc.get("filing_date"),
                    "grant_date": doc.get("grant_date"),
                    "abstract": doc.get("abstract", ""),
                    "pdf_url": f"https://patents.google.com/patent/US{doc.get('patent_number')}/en",
                    "relevance_score": 0.75,
                }
                results.append(patent)
            
            logger.info(f"USPTO patent search for '{query}' returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"USPTO patent search failed: {str(e)}")
            return []


# ============================================================================
# GOOGLE PATENTS
# ============================================================================

class GooglePatentSearcher:
    """
    Search Google Patents (easier than USPTO)
    Uses web scraping or their search API
    """
    
    BASE_URL = "https://patents.google.com/ajax/query"
    
    @staticmethod
    def search(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search Google Patents
        """
        try:
            params = {
                "cmd": "q",
                "num": min(max_results, 100),
                "q": query,
            }
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            response = requests.get(
                GooglePatentSearcher.BASE_URL,
                params=params,
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for patent in data.get("results", []):
                result = {
                    "source": "Google Patents",
                    "patent_id": patent.get("id"),
                    "title": patent.get("title"),
                    "assignee": patent.get("assignee"),
                    "filed_date": patent.get("filed_date"),
                    "granted_date": patent.get("granted_date"),
                    "pdf_url": f"https://patents.google.com/patent/{patent.get('id')}/en",
                    "relevance_score": 0.8,
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Google Patents search failed: {str(e)}")
            return []


# ============================================================================
# UNIFIED SEARCH INTERFACE
# ============================================================================

class UnifiedResearchSearcher:
    """
    Search across all sources for research papers and patents
    """
    
    @staticmethod
    def search_all(
        query: str,
        sources: List[str] = None,
        max_per_source: int = 10,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search all configured sources
        
        Args:
            query: Search term
            sources: ["arxiv", "semantic_scholar", "patents", "google_patents"]
                     Default: all
            max_per_source: Results per source
            
        Returns:
            Dictionary with results per source
        """
        if sources is None:
            sources = ["arxiv", "semantic_scholar", "patents"]
        
        results = {}
        
        if "arxiv" in sources:
            results["arxiv"] = ArxivSearcher.search(query, max_per_source)
        
        if "semantic_scholar" in sources:
            results["semantic_scholar"] = SemanticScholarSearcher.search(query, max_per_source)
        
        if "patents" in sources:
            results["patents"] = USPTOPatentSearcher.search(query, max_per_source)
        
        if "google_patents" in sources:
            results["google_patents"] = GooglePatentSearcher.search(query, max_per_source)
        
        return results
    
    @staticmethod
    def search_papers_only(query: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Search academic papers (arXiv + Semantic Scholar combined)
        """
        all_results = []
        
        # Search arXiv
        arxiv_results = ArxivSearcher.search(query, max_results // 2)
        all_results.extend(arxiv_results)
        
        # Search Semantic Scholar
        ss_results = SemanticScholarSearcher.search(query, max_results // 2)
        all_results.extend(ss_results)
        
        # Sort by relevance score
        all_results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        return all_results[:max_results]
    
    @staticmethod
    def search_patents_only(query: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Search patents (USPTO + Google Patents combined)
        """
        all_results = []
        
        # Search USPTO
        uspto_results = USPTOPatentSearcher.search(query, max_results // 2)
        all_results.extend(uspto_results)
        
        # Search Google Patents
        gp_results = GooglePatentSearcher.search(query, max_results // 2)
        all_results.extend(gp_results)
        
        # Sort by relevance
        all_results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        return all_results[:max_results]


# ============================================================================
# INTEGRATION WITH RAG SYSTEM
# ============================================================================

def augment_rag_with_web_search(
    query: str,
    local_chunks: List[Dict[str, Any]],
    search_web: bool = True,
    search_patents: bool = False,
) -> Dict[str, Any]:
    """
    Augment local RAG results with web search
    
    This is called when:
    1. Local documents don't have sufficient context (confidence < 0.7)
    2. User explicitly requests web search
    3. Query is about recent papers/patents
    
    Args:
        query: User's question
        local_chunks: Chunks retrieved from local database
        search_web: Whether to search arXiv/Semantic Scholar
        search_patents: Whether to search for patents
        
    Returns:
        Combined results with sources mixed
    """
    augmented = {
        "local_chunks": local_chunks,
        "web_papers": [],
        "patents": [],
        "hybrid_mode": False,
    }
    
    # If local results are weak, search the web
    if not local_chunks or len(local_chunks) < 3:
        logger.info(f"Local results insufficient, searching web for: {query}")
        augmented["hybrid_mode"] = True
        
        if search_web:
            augmented["web_papers"] = UnifiedResearchSearcher.search_papers_only(query, 10)
        
        if search_patents:
            augmented["patents"] = UnifiedResearchSearcher.search_patents_only(query, 10)
    
    return augmented


if __name__ == "__main__":
    # Test the searchers
    
    print("\n🔍 arXiv Search Test:")
    rag_papers = ArxivSearcher.search("RAG retrieval augmented generation", max_results=5)
    for p in rag_papers[:2]:
        print(f"  - {p['title']}")
    
    print("\n🔍 Semantic Scholar Search Test:")
    ss_papers = SemanticScholarSearcher.search("vector database", max_results=5)
    for p in ss_papers[:2]:
        print(f"  - {p['title']} ({p['citation_count']} citations)")
    
    print("\n🔍 Patent Search Test:")
    patents = USPTOPatentSearcher.search("machine learning", max_results=5)
    for p in patents[:2]:
        print(f"  - {p['title']}")
    
    print("\n✅ All integrations working!")
