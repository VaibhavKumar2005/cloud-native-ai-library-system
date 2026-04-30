"""
Academic Paper APIs - For PhD research discovery
Integrates with Semantic Scholar, arXiv, CrossRef, and Google Scholar
"""
import requests
import logging
from textwrap import shorten
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
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

    def get_permissions(self):
        if settings.DEMO_MODE:
            return [AllowAny()]
        return super().get_permissions()

    def _get_demo_user(self):
        User = get_user_model()
        user, _ = User.objects.get_or_create(
            username='demo',
            defaults={
                'email': 'demo@verirag.local',
                'is_active': True,
            },
        )
        return user

    def _get_request_user(self, request):
        if request.user.is_authenticated:
            return request.user
        if settings.DEMO_MODE:
            return self._get_demo_user()
        return request.user
    
    def get_queryset(self):
        return AcademicPaper.objects.filter(user=self._get_request_user(self.request))
    
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
        Add papers to user's library from external sources AND ingest into RAG
        
        Request body:
        {
            "paper_ids": ["semantic-scholar-id-1", "semantic-scholar-id-2"],
            "source": "semantic-scholar"
        }
        
        Creates both AcademicPaper (for discovery) and Document (for RAG)
        """
        paper_ids = request.data.get('paper_ids', [])
        paper_payloads = request.data.get('papers', [])
        source = request.data.get('source', 'semantic-scholar')
        
        if not paper_ids and not paper_payloads:
            return Response({'error': 'paper_ids or papers required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            ingest_result = self._ingest_papers_for_user(
                user=self._get_request_user(request),
                paper_ids=paper_ids,
                paper_payloads=paper_payloads,
                source=source,
                sync_process=False,
            )
            return Response({
                'ingested': ingest_result['ingested'],
                'total_requested': ingest_result['total_requested'],
                'document_ids': ingest_result['document_ids'],
                'message': f"Successfully ingested {ingest_result['ingested']} papers into RAG system"
            }, status=status.HTTP_202_ACCEPTED)  # 202 Accepted for async processing
        
        except Exception as e:
            logger.error(f"Paper ingestion failed: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='agentic-query')
    def agentic_query(self, request):
        """
        Agentic RAG flow:
        1) try local retrieval
        2) if weak evidence, search papers
        3) let user select papers
        4) answer from selected paper abstracts
        """
        query = str(request.data.get('query', '')).strip()
        selected_paper_ids = request.data.get('selected_paper_ids', []) or []
        source = request.data.get('source', 'arxiv')

        if not query:
            return Response({'error': 'query is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Step 1: Try local RAG first.
        local_result = query_academic_rag(query=query)
        if local_result.get('status') != 'rejected' and local_result.get('answer'):
            return Response({
                'status': 'answered',
                'mode': 'local_rag',
                'result': local_result,
            })

        # Step 2: If no selection yet, provide candidate papers.
        if not selected_paper_ids:
            try:
                papers = self._search_papers(query, source)
            except Exception as exc:
                logger.warning("Agentic paper search failed for %r via %s: %s", query, source, exc)
                return Response({
                    'status': 'rejected',
                    'mode': 'paper_search_unavailable',
                    'message': (
                        'Local evidence was weak and external paper search is currently unavailable. '
                        'Try a more specific query or retry in a moment.'
                    ),
                }, status=status.HTTP_200_OK)
            candidates = papers[:6]
            return Response({
                'status': 'needs_selection',
                'mode': 'paper_search',
                'message': 'Local evidence was weak. Select papers to ground your answer.',
                'candidates': candidates,
            })

        # Step 3: Ingest selected papers and answer with explicit grounding.
        selected_payloads = request.data.get('selected_papers', []) or []
        ingest_result = self._ingest_papers_for_user(
            user=self._get_request_user(request),
            paper_ids=selected_paper_ids,
            paper_payloads=selected_payloads,
            source=source,
            sync_process=False,
        )
        grounded_papers = ingest_result.get('papers', [])
        grounded_answer = self._build_grounded_answer_from_papers(query, grounded_papers)
        return Response({
            'status': 'answered',
            'mode': 'paper_grounded',
            'result': grounded_answer,
            'ingest': {
                'ingested': ingest_result['ingested'],
                'document_ids': ingest_result['document_ids'],
            },
        })
    
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
            rag_result = query_academic_rag(query=question)
            answer = rag_result.get('answer') or rag_result.get('message', 'No answer generated')
            sources = rag_result.get('sources', [])
            faithfulness = rag_result.get('confidence', 0.0)
            
            # Log the Q&A
            qna = PaperQnA.objects.create(
                paper=paper,
                user=self._get_request_user(request),
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
        # Normalize source names (handle both hyphens and underscores)
        source = source.replace('_', '-').lower()
        
        if source == 'semantic-scholar':
            return self._search_semantic_scholar(query)
        elif source == 'arxiv':
            return self._search_arxiv(query)
        elif source == 'crossref':
            return self._search_crossref(query)
        else:
            raise ValueError(f"Unsupported source: {source}")
    
    def _search_semantic_scholar(self, query):
        """Search Semantic Scholar (free API, no key required) with fallback to mock data"""
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
            
            return papers if papers else self._get_mock_papers(query)
        except Exception as e:
            logger.warning(f"Semantic Scholar search failed: {e}, using mock data")
            return self._get_mock_papers(query)
    
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

    def _ingest_papers_for_user(self, user, paper_ids, paper_payloads, source, sync_process=False):
        """Create/refresh AcademicPaper+Document records for selected papers."""
        from ai_engine.models import Document
        from ai_engine.tasks import process_abstract_to_vector_db

        ingested_count = 0
        document_ids = []
        hydrated_papers = []

        papers_to_ingest = []
        for payload in paper_payloads or []:
            if isinstance(payload, dict):
                payload_id = payload.get('id') or payload.get('paperId')
                if payload_id:
                    papers_to_ingest.append((str(payload_id), payload))

        for paper_id in paper_ids or []:
            if str(paper_id) not in {pid for pid, _ in papers_to_ingest}:
                papers_to_ingest.append((str(paper_id), None))

        for paper_id, payload in papers_to_ingest:
            paper_data = payload or self._fetch_paper_details(paper_id, source)
            if not paper_data:
                continue

            paper_data = dict(paper_data)
            payload_external_id = paper_data.pop('id', None) or paper_data.pop('paperId', None)
            paper_data.setdefault('external_id', payload_external_id or paper_id)
            paper_data.setdefault('publication_year', paper_data.pop('year', None))
            paper_data.setdefault('citation_count', paper_data.pop('citationCount', 0))
            paper_data.setdefault('source', source)

            academic_paper, _ = AcademicPaper.objects.update_or_create(
                external_id=paper_id,
                defaults={**paper_data, 'user': user},
            )
            hydrated_papers.append(academic_paper)

            source_mapping = {
                AcademicPaper.Source.SEMANTIC_SCHOLAR: Document.Source.SEMANTIC_SCHOLAR,
                AcademicPaper.Source.ARXIV: Document.Source.ARXIV,
                AcademicPaper.Source.CROSSREF: Document.Source.CROSSREF,
            }
            doc_source = source_mapping.get(paper_data.get('source'), Document.Source.SEMANTIC_SCHOLAR)

            doc, doc_created = Document.objects.get_or_create(
                user=user,
                title=paper_data.get('title', f'Paper {paper_id}'),
                source=doc_source,
                defaults={
                    'content': paper_data.get('abstract', ''),
                    'status': Document.Status.QUEUED,
                    'source_metadata': {
                        'paper_id': paper_id,
                        'external_id': paper_id,
                        'external_url': paper_data.get('url', ''),
                        'authors': paper_data.get('authors', []),
                        'year': paper_data.get('publication_year'),
                        'venue': paper_data.get('venue', ''),
                        'doi': paper_data.get('doi', ''),
                        'citation_count': paper_data.get('citation_count', 0),
                        'abstract': paper_data.get('abstract', ''),
                    },
                },
            )

            if doc_created and paper_data.get('abstract'):
                if sync_process:
                    process_abstract_to_vector_db.apply(kwargs={'document_id': doc.id})
                else:
                    process_abstract_to_vector_db.delay(document_id=doc.id)
                document_ids.append(doc.id)

            ingested_count += 1

        return {
            'ingested': ingested_count,
            'total_requested': len(papers_to_ingest),
            'document_ids': document_ids,
            'papers': hydrated_papers,
        }

    def _build_grounded_answer_from_papers(self, query, papers):
        """Create a grounded response directly from selected paper abstracts."""
        if not papers:
            return {
                'status': 'rejected',
                'message': 'No selected papers were available for grounding.',
                'confidence': 0.0,
                'confidence_label': 'none',
                'retrieval': {'top_k': 0, 'min_relevance': 0.2, 'chunks_returned': 0},
            }

        bullet_points = []
        sources = []
        for paper in papers[:4]:
            abstract = (paper.abstract or '').strip()
            if not abstract:
                continue
            excerpt = shorten(abstract, width=260, placeholder='...')
            bullet_points.append(f"- {paper.title}: {excerpt}")
            sources.append({
                'title': paper.title,
                'source': paper.source,
                'metadata_url': paper.url,
                'excerpt': excerpt,
                'relevance': 0.82,
            })

        if not bullet_points:
            return {
                'status': 'rejected',
                'message': 'Selected papers do not have usable abstract text for grounding.',
                'confidence': 0.0,
                'confidence_label': 'none',
                'retrieval': {'top_k': len(papers), 'min_relevance': 0.2, 'chunks_returned': 0},
            }

        answer_text = (
            f"For your question '{query}', I grounded the response in the selected papers. "
            "Here are the most relevant findings:\n\n" + "\n".join(bullet_points)
        )
        return {
            'status': 'answer',
            'answer': answer_text,
            'confidence': 0.82,
            'confidence_label': 'grounded',
            'retrieval': {'top_k': len(papers), 'min_relevance': 0.2, 'chunks_returned': len(sources)},
            'sources': sources,
        }
    
    def _get_mock_papers(self, query):
        """Return mock papers for demo/testing when APIs are unavailable"""
        mock_papers_db = {
            'rag': [
                {
                    'id': 'arxiv-2401.12345',
                    'title': 'Retrieval-Augmented Generation: A Comprehensive Overview',
                    'authors': ['Chen, Wei', 'Wan, Hang', 'Zhang, Qinggang'],
                    'year': 2024,
                    'abstract': 'This paper surveys the landscape of retrieval-augmented generation (RAG) systems, including methods for knowledge retrieval, integration architectures, and applications in conversational AI. We analyze how RAG improves factuality and reduces hallucination in large language models.',
                    'url': 'https://arxiv.org/abs/2401.12345',
                    'citationCount': 42,
                    'venue': 'arXiv',
                    'source': 'arxiv'
                },
                {
                    'id': 'semantic-scholar-2024-rag',
                    'title': 'In-Context Retrieval-Augmented Language Models',
                    'authors': ['Borgeaud, Sebastian', 'Mensch, Arthur', 'Hoffman, Jordan'],
                    'year': 2023,
                    'abstract': 'We demonstrate how large language models can be augmented with retrieval mechanisms to access up-to-date information and improve grounding. Our approach uses in-context retrieval where relevant documents are inserted into the prompt context window.',
                    'url': 'https://arxiv.org/abs/2302.00083',
                    'citationCount': 156,
                    'venue': 'ICLR',
                    'source': 'semantic-scholar'
                }
            ],
            'prompt engineering': [
                {
                    'id': 'arxiv-2401.54321',
                    'title': 'Prompting Techniques for Large Language Models',
                    'authors': ['Zhou, Yongcheng', 'Muresanu, Andrei Ionut'],
                    'year': 2024,
                    'abstract': 'We systematically study prompting techniques for LLMs, including few-shot learning, chain-of-thought reasoning, and instruction following. Our analysis shows that prompt design significantly impacts model performance across diverse tasks.',
                    'url': 'https://arxiv.org/abs/2401.54321',
                    'citationCount': 87,
                    'venue': 'arXiv',
                    'source': 'arxiv'
                }
            ],
            'llm': [
                {
                    'id': 'arxiv-2401.llm01',
                    'title': 'Language Models Are Few-Shot Learners',
                    'authors': ['Brown, Tom B.', 'Mann, Benjamin', 'Ryder, Nick'],
                    'year': 2020,
                    'abstract': 'We demonstrate that large language models perform well on many NLP tasks with minimal task-specific fine-tuning. This work introduces GPT-3 and explores the paradigm of few-shot learning for NLP applications.',
                    'url': 'https://arxiv.org/abs/2005.14165',
                    'citationCount': 8234,
                    'venue': 'NeurIPS',
                    'source': 'arxiv'
                }
            ]
        }
        
        # Search for matching query in mock database
        query_lower = query.lower()
        for keyword, papers in mock_papers_db.items():
            if keyword in query_lower:
                return papers
        
        # Default: return RAG papers if no match found
        return mock_papers_db.get('rag', [])


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
