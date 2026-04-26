"""
VeriRAG External Search API Endpoint
Provides REST API for arXiv, patents, and academic paper search
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import logging

from ai_engine.external_search import (
    ArxivSearcher,
    SemanticScholarSearcher,
    USPTOPatentSearcher,
    GooglePatentSearcher,
    UnifiedResearchSearcher,
)

logger = logging.getLogger(__name__)


class ExternalSearchViewSet(viewsets.ViewSet):
    """
    API endpoints for searching external academic and patent sources
    
    Endpoints:
    - POST /api/search/arxiv/ - Search arXiv
    - POST /api/search/papers/ - Search papers (arXiv + Semantic Scholar)
    - POST /api/search/patents/ - Search patents
    - POST /api/search/all/ - Search all sources
    - GET /api/search/arxiv-latest/ - Latest papers by category
    """
    
    permission_classes = [IsAuthenticated]  # Only authenticated users can search
    
    @action(detail=False, methods=['post'])
    def arxiv(self, request):
        """
        Search arXiv for papers
        
        Request:
        {
            "query": "RAG retrieval augmented generation",
            "max_results": 10,
            "sort_by": "relevance"  # or "submittedDate"
        }
        """
        query = request.data.get('query')
        if not query:
            return Response(
                {"error": "query parameter required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        max_results = request.data.get('max_results', 10)
        sort_by = request.data.get('sort_by', 'relevance')
        
        try:
            results = ArxivSearcher.search(
                query=query,
                max_results=min(max_results, 50),
                sort_by=sort_by,
            )
            
            return Response({
                "source": "arXiv",
                "query": query,
                "count": len(results),
                "results": results,
            })
        
        except Exception as e:
            logger.error(f"arXiv search error: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def arxiv_latest(self, request):
        """
        Get latest papers from arXiv category
        
        Query params:
        - category: cs.AI, cs.LG, cs.CL, cs.CV, cs.CR, etc.
        - days: 7 (default)
        - max_results: 20 (default)
        """
        category = request.query_params.get('category', 'cs.AI')
        days = int(request.query_params.get('days', 7))
        max_results = int(request.query_params.get('max_results', 20))
        
        try:
            results = ArxivSearcher.search_by_category(
                category=category,
                days=days,
                max_results=min(max_results, 50),
            )
            
            return Response({
                "source": "arXiv",
                "category": category,
                "days": days,
                "count": len(results),
                "results": results,
            })
        
        except Exception as e:
            logger.error(f"arXiv category search error: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def papers(self, request):
        """
        Search academic papers (arXiv + Semantic Scholar)
        
        Request:
        {
            "query": "machine learning",
            "max_results": 20
        }
        """
        query = request.data.get('query')
        if not query:
            return Response(
                {"error": "query parameter required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        max_results = request.data.get('max_results', 20)
        
        try:
            results = UnifiedResearchSearcher.search_papers_only(
                query=query,
                max_results=min(max_results, 100),
            )
            
            return Response({
                "sources": ["arXiv", "Semantic Scholar"],
                "query": query,
                "count": len(results),
                "results": results,
            })
        
        except Exception as e:
            logger.error(f"Papers search error: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def patents(self, request):
        """
        Search patents (USPTO + Google Patents)
        
        Request:
        {
            "query": "machine learning patent",
            "max_results": 20
        }
        """
        query = request.data.get('query')
        if not query:
            return Response(
                {"error": "query parameter required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        max_results = request.data.get('max_results', 20)
        
        try:
            results = UnifiedResearchSearcher.search_patents_only(
                query=query,
                max_results=min(max_results, 100),
            )
            
            return Response({
                "sources": ["USPTO", "Google Patents"],
                "query": query,
                "count": len(results),
                "results": results,
            })
        
        except Exception as e:
            logger.error(f"Patents search error: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def all(self, request):
        """
        Search all sources (academic papers + patents)
        
        Request:
        {
            "query": "turboquant",
            "sources": ["arxiv", "semantic_scholar", "patents"],
            "max_per_source": 10
        }
        """
        query = request.data.get('query')
        if not query:
            return Response(
                {"error": "query parameter required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        sources = request.data.get('sources', ['arxiv', 'semantic_scholar', 'patents'])
        max_per_source = request.data.get('max_per_source', 10)
        
        try:
            results = UnifiedResearchSearcher.search_all(
                query=query,
                sources=sources,
                max_per_source=min(max_per_source, 50),
            )
            
            # Count total results
            total = sum(len(v) for v in results.values())
            
            return Response({
                "query": query,
                "sources": sources,
                "total_results": total,
                "results": results,
            })
        
        except Exception as e:
            logger.error(f"Unified search error: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def augment_rag(self, request):
        """
        Search external sources to augment RAG results
        Used when local documents don't have sufficient context
        
        Request:
        {
            "query": "what is turboquant?",
            "local_confidence": 0.5,
            "search_papers": true,
            "search_patents": false
        }
        """
        query = request.data.get('query')
        confidence = request.data.get('local_confidence', 0.0)
        search_papers = request.data.get('search_papers', True)
        search_patents = request.data.get('search_patents', False)
        
        if not query:
            return Response(
                {"error": "query parameter required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # If local confidence is low, search web
            if confidence < 0.7:
                results = []
                
                if search_papers:
                    papers = UnifiedResearchSearcher.search_papers_only(query, 10)
                    results.extend(papers)
                
                if search_patents:
                    patents = UnifiedResearchSearcher.search_patents_only(query, 10)
                    results.extend(patents)
                
                return Response({
                    "query": query,
                    "local_confidence": confidence,
                    "augmented": True,
                    "count": len(results),
                    "results": results[:20],
                })
            else:
                return Response({
                    "query": query,
                    "local_confidence": confidence,
                    "augmented": False,
                    "message": "Local confidence sufficient, no augmentation needed",
                })
        
        except Exception as e:
            logger.error(f"RAG augmentation error: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
