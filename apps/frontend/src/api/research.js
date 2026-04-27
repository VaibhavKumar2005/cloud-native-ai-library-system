/**
 * Research API Client
 * Handles all API calls for the research interface
 */

const API_ROOT = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_BASE = `${API_ROOT}/api`;

/**
 * Search for academic papers from Semantic Scholar/arXiv
 */
export async function searchAcademicPapers(query, limit = 10) {
  try {
    const response = await fetch(
      `${API_BASE}/papers/search/`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: query,
          source: 'semantic_scholar',
          limit: limit
        })
      }
    );
    
    if (!response.ok) {
      throw new Error(`Search failed: ${response.status} ${response.statusText}`);
    }
    
    const data = await response.json();
    return data.papers || [];
  } catch (error) {
    console.error('Search error:', error);
    throw error;
  }
}

/**
 * Query RAG with optional session paper filtering
 */
export async function queryAcademicRAG(query, sessionPaperIds = []) {
  try {
    const response = await fetch(
      `${API_ROOT}/query`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query,
          session_paper_ids: sessionPaperIds
        })
      }
    );

    if (!response.ok) {
      throw new Error(`Query failed: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Query error:', error);
    throw error;
  }
}

/**
 * Ingest an academic paper into the RAG system
 */
export async function ingestAcademicPaper(paperData) {
  try {
    const response = await fetch(
      `${API_BASE}/papers/ingest/`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(paperData)
      }
    );

    if (!response.ok) {
      throw new Error(`Ingest failed: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Ingest error:', error);
    throw error;
  }
}

/**
 * Get user's document library
 */
export async function getMyLibrary() {
  try {
    const response = await fetch(
      `${API_BASE}/documents/my-documents/`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      }
    );

    if (!response.ok) {
      throw new Error(`Fetch failed: ${response.statusText}`);
    }

    const data = await response.json();
    return Array.isArray(data) ? data : data.documents || [];
  } catch (error) {
    console.error('Library fetch error:', error);
    throw error;
  }
}

/**
 * Search user's local documents
 */
export async function searchLocalDocuments(query) {
  try {
    const response = await fetch(
      `${API_BASE}/documents/search/?q=${encodeURIComponent(query)}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      }
    );

    if (!response.ok) {
      throw new Error(`Search failed: ${response.statusText}`);
    }

    const data = await response.json();
    return Array.isArray(data) ? data : data.documents || [];
  } catch (error) {
    console.error('Document search error:', error);
    throw error;
  }
}

/**
 * Upload a PDF document
 */
export async function uploadDocument(file) {
  try {
    const formData = new FormData();
    formData.append('title', file.name.replace('.pdf', ''));
    formData.append('file', file);

    const response = await fetch(
      `${API_BASE}/documents/`,
      {
        method: 'POST',
        body: formData
      }
    );

    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Upload error:', error);
    throw error;
  }
}
