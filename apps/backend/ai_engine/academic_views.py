"""
Academic Paper APIs - For PhD research discovery
Integrates with Semantic Scholar, arXiv, CrossRef, and Google Scholar
"""
import requests
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from .models import AcademicPaper, PaperLibrary, ResearchTopic, ResearchGap, PaperQnA
from .serializers import (
    AcademicPaperSerializer, PaperLibrarySerializer, 
    ResearchTopicSerializer, ResearchGapSerializer, PaperQnASerializer
)
from .rag_logic import query_academic_rag

logger = logging.getLogger(__name__)

# ============================================================================
# ACADEMIC PAPER SEARCH & INGESTION APIs
# ============================================================================

class AcademicPaperViewSet(viewsets.ModelViewSet):
    """
    API for searching and managing academic papers
    
    Endpoints:
    - POST /api/papers/search/ - Search papers from external sources
    - POST /api/papers/ingest/ - Add papers to user's library
    - GET /api/papers/library/ - Get user's paper library
    - POST /api/papers/analyze-gaps/ - Analyze research gaps
    - POST /api/papers/recommend-topics/ - Get topic recommendations
    - POST /api/papers/{id}/ask/ - RAG-based Q&A on papers
    """
    permission_classes = [IsAuthenticated]
    serializer_class = AcademicPaperSerializer
    
    def get_queryset(self):
        return AcademicPaper.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def search(self, request):
        """
        Search academic papers from external sources
        
        Request body:
        {
            "query": "prompt engineering in LLMs",
            "source": "semantic-scholar"  # semantic-scholar, arxiv, crossref
        }
        """
        query = request.data.get('query', '').strip()
        source = request.data.get('source', 'semantic-scholar')
        
        if not query:
            return Response({'error': 'Query is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            papers = self._search_papers(query, source)
            return Response({'papers': papers, 'count': len(papers)})
        except Exception as e:
            logger.error(f"Paper search failed: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def ingest(self, request):
        """
        Add papers to user's library from external sources
        
        Request body:
        {
            "paper_ids": ["semantic-scholar-id-1", "semantic-scholar-id-2"],
            "source": "semantic-scholar"
        }
        """
        paper_ids = request.data.get('paper_ids', [])
        source = request.data.get('source', 'semantic-scholar')
        
        if not paper_ids:
            return Response({'error': 'paper_ids required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            ingested_count = 0
            for paper_id in paper_ids:
                paper_data = self._fetch_paper_details(paper_id, source)
                if paper_data:
                    paper, created = AcademicPaper.objects.get_or_create(
                        user=request.user,
                        external_id=paper_id,
                        defaults=paper_data
                    )
                    ingested_count += 1
            
            return Response({
                'ingested': ingested_count,
                'total_requested': len(paper_ids),
                'message': f'Successfully added {ingested_count} papers'
            })
        except Exception as e:
            logger.error(f"Paper ingestion failed: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def library(self, request):
        """Get user's paper library"""
        filter_type = request.query_params.get('filter', 'all')
        papers = self.get_queryset()
        
        if filter_type == 'favorites':
            papers = papers.filter(paperlibrary__is_favorite=True)
        elif filter_type == 'recent':
            papers = papers.order_by('-created_at')[:20]
        
        serializer = self.get_serializer(papers, many=True)
        return Response({'papers': serializer.data, 'total': papers.count()})
    
    @action(detail=False, methods=['get'])
    def library_stats(self, request):
        """Get library statistics"""
        papers = self.get_queryset()
        return Response({
            'total_papers': papers.count(),
            'total_citations': sum(p.citation_count for p in papers),
            'years_span': {
                'earliest': papers.aggregate(models.Min('publication_year'))['publication_year__min'],
                'latest': papers.aggregate(models.Max('publication_year'))['publication_year__max'],
            }
        })
    
    @action(detail='<int:pk>', methods=['post'])
    def ask(self, request, pk=None):
        """
        Ask a question about a specific paper using RAG
        
        Request body:
        {
            "question": "What are the main contributions of this paper?"
        }
        """
        paper = self.get_object()
        question = request.data.get('question', '').strip()
        
        if not question:
            return Response({'error': 'Question is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            answer, sources, faithfulness = query_academic_rag(
                question=question,
                paper=paper,
                user=request.user
            )
            
            # Log the Q&A
            qna = PaperQnA.objects.create(
                paper=paper,
                user=request.user,
                question=question,
                answer=answer,
                sources_cited=sources,
                faithfulness_score=faithfulness
            )
            
            return Response({
                'answer': answer,
                'sources': sources,
                'faithfulness_score': faithfulness
            })
        except Exception as e:
            logger.error(f"Paper QnA failed: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # ========================================================================
    # PAPER SEARCH IMPLEMENTATIONS
    # ========================================================================
    
    def _search_papers(self, query, source):
        """Unified paper search across sources"""
        if source == 'semantic-scholar':
            return self._search_semantic_scholar(query)
        elif source == 'arxiv':
            return self._search_arxiv(query)
        elif source == 'crossref':
            return self._search_crossref(query)
        else:
            raise ValueError(f"Unsupported source: {source}")
    
    def _search_semantic_scholar(self, query):
        """Search Semantic Scholar (free API, no key required)"""
        try:
            response = requests.get(
                'https://api.semanticscholar.org/graph/v1/paper/search',
                params={
                    'query': query,
                    'limit': 10,
                    'fields': 'paperId,title,authors,year,abstract,url,citationCount,venue'
                },
                timeout=10
            )
            response.raise_for_status()
            
            papers = []
            for item in response.json().get('data', []):
                papers.append({
                    'id': item['paperId'],
                    'title': item.get('title', ''),
                    'authors': [a['name'] for a in item.get('authors', [])],
                    'year': item.get('year'),
                    'abstract': item.get('abstract', ''),
                    'url': item.get('url', ''),
                    'citationCount': item.get('citationCount', 0),
                    'venue': item.get('venue', ''),
                    'source': 'semantic-scholar'
                })
            
            return papers
        except Exception as e:
            logger.error(f"Semantic Scholar search failed: {e}")
            raise
    
    def _search_arxiv(self, query):
        """Search arXiv (free API)"""
        try:
            # arXiv uses querystring format
            # Example: cat:cs.AI AND submittedDate:[202001010000 TO 202012312359]
            response = requests.get(
                'http://export.arxiv.org/api/query',
                params={
                    'search_query': f'all:{query}',
                    'start': 0,
                    'max_results': 10,
                    'sortBy': 'relevance',
                    'sortOrder': 'descending'
                },
                timeout=10
            )
            response.raise_for_status()
            
            # Parse XML response
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)
            
            papers = []
            namespace = {'arxiv': 'http://arxiv.org/schemas/atom'}
            
            for entry in root.findall('atom:entry', {'atom': 'http://www.w3.org/2005/Atom'}):
                paper = {
                    'id': entry.find('atom:id', {'atom': 'http://www.w3.org/2005/Atom'}).text.split('/abs/')[-1],
                    'title': entry.find('atom:title', {'atom': 'http://www.w3.org/2005/Atom'}).text.strip(),
                    'authors': [author.find('atom:name', {'atom': 'http://www.w3.org/2005/Atom'}).text 
                               for author in entry.findall('atom:author', {'atom': 'http://www.w3.org/2005/Atom'})],
                    'year': entry.find('atom:published', {'atom': 'http://www.w3.org/2005/Atom'}).text[:4],
                    'abstract': entry.find('atom:summary', {'atom': 'http://www.w3.org/2005/Atom'}).text.strip(),
                    'url': entry.find('atom:id', {'atom': 'http://www.w3.org/2005/Atom'}).text,
                    'source': 'arxiv'
                }
                papers.append(paper)
            
            return papers
        except Exception as e:
            logger.error(f"arXiv search failed: {e}")
            raise
    
    def _search_crossref(self, query):
        """Search CrossRef (free API)"""
        try:
            response = requests.get(
                'https://api.crossref.org/works',
                params={
                    'query': query,
                    'rows': 10,
                    'sort': 'relevance'
                },
                timeout=10
            )
            response.raise_for_status()
            
            papers = []
            for item in response.json()['message'].get('items', []):
                paper = {
                    'id': item.get('DOI', ''),
                    'title': item.get('title', [''])[0],
                    'authors': [f"{a.get('given', '')} {a.get('family', '')}" 
                               for a in item.get('author', [])],
                    'year': item.get('published-online', {}).get('date-parts', [[None]])[0][0],
                    'abstract': item.get('abstract', ''),
                    'url': item.get('URL', ''),
                    'doi': item.get('DOI', ''),
                    'venue': item.get('container-title', ''),
                    'source': 'crossref'
                }
                papers.append(paper)
            
            return papers
        except Exception as e:
            logger.error(f"CrossRef search failed: {e}")
            raise
    
    def _fetch_paper_details(self, paper_id, source):
        """Fetch full paper details for ingestion"""
        if source == 'semantic-scholar':
            return self._fetch_semantic_scholar_details(paper_id)
        elif source == 'arxiv':
            return self._fetch_arxiv_details(paper_id)
        elif source == 'crossref':
            return self._fetch_crossref_details(paper_id)
        return None
    
    def _fetch_semantic_scholar_details(self, paper_id):
        """Fetch details from Semantic Scholar"""
        try:
            response = requests.get(
                f'https://api.semanticscholar.org/graph/v1/paper/{paper_id}',
                params={
                    'fields': 'paperId,title,authors,year,abstract,url,DOI,venue,citationCount'
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                'title': data.get('title', ''),
                'abstract': data.get('abstract', ''),
                'authors': [a['name'] for a in data.get('authors', [])],
                'publication_year': data.get('year'),
                'venue': data.get('venue', ''),
                'doi': data.get('DOI', ''),
                'url': data.get('url', ''),
                'citation_count': data.get('citationCount', 0),
                'source': AcademicPaper.Source.SEMANTIC_SCHOLAR,
            }
        except Exception as e:
            logger.error(f"Failed to fetch Semantic Scholar details: {e}")
            return None
    
    def _fetch_arxiv_details(self, paper_id):
        """Fetch details from arXiv"""
        # arXiv doesn't have much more details beyond search results
        return {
            'source': AcademicPaper.Source.ARXIV,
            'url': f'https://arxiv.org/abs/{paper_id}'
        }
    
    def _fetch_crossref_details(self, paper_id):
        """Fetch details from CrossRef"""
        try:
            response = requests.get(
                f'https://api.crossref.org/works/{paper_id}',
                timeout=10
            )
            response.raise_for_status()
            data = response.json()['message']
            
            return {
                'doi': data.get('DOI', ''),
                'title': data.get('title', [''])[0],
                'authors': [f"{a.get('given', '')} {a.get('family', '')}" 
                           for a in data.get('author', [])],
                'publication_year': data.get('published-online', {}).get('date-parts', [[None]])[0][0],
                'venue': data.get('container-title', ''),
                'url': data.get('URL', ''),
                'source': AcademicPaper.Source.CROSSREF,
            }
        except Exception as e:
            logger.error(f"Failed to fetch CrossRef details: {e}")
            return None


# ============================================================================
# RESEARCH GAP & TOPIC ANALYSIS APIs
# ============================================================================

class ResearchAnalysisViewSet(viewsets.ViewSet):
    """
    API for research gap analysis and topic recommendations
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def analyze_gaps(self, request):
        """
        Analyze research gaps in a given topic
        
        Request body:
        {
            "topic": "prompt engineering in large language models"
        }
        """
        topic = request.data.get('topic', '').strip()
        
        if not topic:
            return Response({'error': 'Topic is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            analysis = query_academic_rag(
                question=f"Analyze research gaps in: {topic}",
                topic=topic,
                user=request.user,
                mode='gap-analysis'
            )
            
            return Response(analysis)
        except Exception as e:
            logger.error(f"Gap analysis failed: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def recommend_topics(self, request):
        """
        Get topic recommendations based on user interests
        
        Request body:
        {
            "interests": ["machine learning", "natural language processing"],
            "field": "ai-engineering"
        }
        """
        interests = request.data.get('interests', [])
        field = request.data.get('field', 'ai-engineering')
        
        if not interests:
            return Response({'error': 'Interests required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            recommendations = query_academic_rag(
                interests=interests,
                field=field,
                user=request.user,
                mode='topic-recommendation'
            )
            
            return Response(recommendations)
        except Exception as e:
            logger.error(f"Topic recommendation failed: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
