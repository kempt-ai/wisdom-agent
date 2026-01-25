/**
 * Knowledge Base API client for Wisdom Agent
 * Handles collections, resources, search, indexing, and argument parsing
 * 
 * FIXED: January 19, 2026 - Matched to actual backend endpoints in knowledge.py
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Knowledge endpoints are under /api/knowledge
const KB_PREFIX = '/api/knowledge';

// Generic fetch wrapper with error handling
async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  return response.json();
}

// ============================================
// Types
// ============================================

export type CollectionType = 'research' | 'fiction' | 'learning' | 'general';

export type ResourceType = 'document' | 'fiction_book' | 'nonfiction_book' | 'article' | 'learning_module';

export type ResourceStatus = 'pending' | 'indexing' | 'indexed' | 'failed';
export type IndexStatus = 'pending' | 'indexing' | 'completed' | 'failed';

export type IndexLevel = 'none' | 'light' | 'standard' | 'full';

export interface CollectionSummary {
  id: number;
  name: string;
  description?: string;
  collection_type: CollectionType;
  resource_count: number;
  total_tokens: number;
  created_at: string;
  updated_at: string;
}

export interface Collection {
  id: number;
  name: string;
  description?: string;
  collection_type: CollectionType;
  resource_count: number;
  total_tokens: number;
  created_at: string;
  updated_at: string;
  resources?: Resource[];
}

export interface Resource {
  id: number;
  collection_id: number;
  name: string;
  resource_type: ResourceType;
  source_type: 'url' | 'text' | 'file' | 'upload';
  source_url?: string;
  content_preview?: string;
  content?: string;
  status: ResourceStatus;
  index_status: IndexStatus;
  index_level: IndexLevel;
  error_message?: string;
  token_count: number;
  indexing_cost?: number;
  created_at: string;
  updated_at: string;
  indexed_at?: string;
}

// Summary version for list views
export interface ResourceSummary {
  id: number;
  name: string;
  resource_type: ResourceType;
  token_count: number;
  index_level: IndexLevel;
  index_status: IndexStatus;
  updated_at: string;
}

export interface KnowledgeStats {
  collections: number;
  resources: number;
  total_tokens: number;
  total_indexing_cost: number;
}

export interface SearchResult {
  resource_id: number;
  resource_name: string;
  resource_type: ResourceType;
  collection_id: number;
  collection_name: string;
  matched_text: string;
  relevance_score: number;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total_results: number;
  search_time_ms: number;
}

export interface CreateCollectionRequest {
  name: string;
  description?: string;
  collection_type: CollectionType;
}

export interface CreateResourceRequest {
  name?: string;
  resource_type?: ResourceType;
  source_type: 'url' | 'text' | 'file';
  source_url?: string;
  source_content?: string;
  content?: string;
  model_override?: string;
  provider_override?: string;
}

export interface CostEstimate {
  content_tokens: number;
  estimated_cost: number;
  model_id: string;
  model_name: string;
  provider: string;
}

export interface IndexEstimate {
  resource_id: number;
  index_level: IndexLevel;
  token_count: number;
  estimated_cost: number;
  budget_remaining: number;
  can_afford: boolean;
  warning_message?: string;
  // Backend also returns these:
  estimated_tokens?: number;
  model_id?: string;
  alternatives?: Array<{
    model_id: string;
    estimated_cost: number;
  }>;
}

export interface UrlPreview {
  success: boolean;
  url: string;
  title?: string;
  author?: string;
  publish_date?: string;
  description?: string;
  content_preview?: string;
  word_count?: number;
  content_type?: string;
  token_estimate?: number;
  indexing_cost_estimates?: {
    light?: { estimated_tokens: number; estimated_cost: number };
    standard?: { estimated_tokens: number; estimated_cost: number };
    full?: { estimated_tokens: number; estimated_cost: number };
  };
  error_message?: string;
}

export interface AddResourceFromUrlRequest {
  url: string;
  name?: string;
  description?: string;
  resource_type?: ResourceType | string;
}

export interface AddResourceTextRequest {
  name: string;
  content: string;
  description?: string;
  resource_type?: ResourceType;
}

// ============================================
// API Functions Object
// ============================================

export const knowledgeApi = {
  // ----------------------------------------
  // Collections
  // ----------------------------------------
  
  async listCollections(
    search?: string,
    collectionType?: CollectionType
  ): Promise<CollectionSummary[]> {
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (collectionType) params.append('collection_type', collectionType);
    
    const queryString = params.toString();
    const endpoint = `${KB_PREFIX}/collections${queryString ? `?${queryString}` : ''}`;
    
    const response = await fetchAPI<CollectionSummary[] | { collections: CollectionSummary[] }>(endpoint);
    return Array.isArray(response) ? response : response.collections;
  },

  async getCollection(id: number): Promise<Collection> {
    return fetchAPI(`${KB_PREFIX}/collections/${id}`);
  },

  async createCollection(data: CreateCollectionRequest): Promise<Collection> {
    return fetchAPI(`${KB_PREFIX}/collections`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async updateCollection(id: number, data: Partial<CreateCollectionRequest>): Promise<Collection> {
    return fetchAPI(`${KB_PREFIX}/collections/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  async deleteCollection(id: number): Promise<void> {
    await fetchAPI(`${KB_PREFIX}/collections/${id}`, {
      method: 'DELETE',
    });
  },

  // ----------------------------------------
  // Resources
  // ----------------------------------------

  async listResources(collectionId: number): Promise<ResourceSummary[]> {
    const response = await fetchAPI<ResourceSummary[] | Resource[]>(
      `${KB_PREFIX}/collections/${collectionId}/resources`
    );
    
    // Map to ResourceSummary if needed
    return response.map((r: any) => ({
      id: r.id,
      name: r.name,
      resource_type: r.resource_type,
      token_count: r.token_count || 0,
      index_level: r.index_level || 'none',
      index_status: r.index_status || 'pending',
      updated_at: r.updated_at || r.created_at,
    }));
  },

  async getResource(resourceId: number): Promise<Resource> {
    return fetchAPI(`${KB_PREFIX}/resources/${resourceId}`);
  },

  async createResource(collectionId: number, data: CreateResourceRequest): Promise<Resource> {
    return fetchAPI(`${KB_PREFIX}/collections/${collectionId}/resources`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Preview a URL before adding it as a resource
   * Endpoint: POST /knowledge/preview-url
   */
  async previewUrl(url: string): Promise<UrlPreview> {
    return fetchAPI(`${KB_PREFIX}/preview-url`, {
      method: 'POST',
      body: JSON.stringify({ url }),
    });
  },

  /**
   * Add a resource from URL
   * Endpoint: POST /knowledge/collections/{id}/from-url
   */
  async addResourceFromUrl(
    collectionId: number, 
    data: AddResourceFromUrlRequest
  ): Promise<{ resource: Resource; extraction: any }> {
    return fetchAPI(`${KB_PREFIX}/collections/${collectionId}/from-url`, {
      method: 'POST',
      body: JSON.stringify({
        url: data.url,
        name: data.name,
        description: data.description,
        resource_type: data.resource_type || 'article',
      }),
    });
  },

  /**
   * Add a resource from pasted text
   * Endpoint: POST /knowledge/collections/{id}/resources
   */
  async addResourceText(
    collectionId: number, 
    data: AddResourceTextRequest
  ): Promise<Resource> {
    return fetchAPI(`${KB_PREFIX}/collections/${collectionId}/resources`, {
      method: 'POST',
      body: JSON.stringify({
        name: data.name,
        content: data.content,
        description: data.description,
        source_type: 'text',
        resource_type: data.resource_type || 'document',
      }),
    });
  },

  /**
   * Upload a file as a resource
   * Endpoint: POST /knowledge/collections/{id}/upload
   */
  async uploadResource(collectionId: number, file: File, name?: string): Promise<Resource> {
    const formData = new FormData();
    formData.append('file', file);
    if (name) formData.append('name', name);
    
    const url = `${API_BASE}${KB_PREFIX}/collections/${collectionId}/upload`;
    
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
      // Don't set Content-Type header - browser will set it with boundary
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(error.detail || `Upload error: ${response.status}`);
    }

    return response.json();
  },

  async deleteResource(resourceId: number): Promise<void> {
    await fetchAPI(`${KB_PREFIX}/resources/${resourceId}`, {
      method: 'DELETE',
    });
  },

  async reindexResource(resourceId: number): Promise<Resource> {
    return fetchAPI(`${KB_PREFIX}/resources/${resourceId}/refresh`, {
      method: 'POST',
    });
  },

  // ----------------------------------------
  // Indexing
  // ----------------------------------------

  /**
   * Get cost estimate for indexing a resource
   * Endpoint: GET /knowledge/resources/{id}/index-estimate?level=X
   */
  async getIndexEstimate(resourceId: number, level: IndexLevel): Promise<IndexEstimate> {
    return fetchAPI(`${KB_PREFIX}/resources/${resourceId}/index-estimate?level=${level}`);
  },

  /**
   * Index a resource at the specified level
   * Endpoint: POST /knowledge/resources/{id}/index
   */
  async indexResource(
    resourceId: number, 
    level: IndexLevel, 
    confirmed: boolean = false
  ): Promise<any> {
    return fetchAPI(`${KB_PREFIX}/resources/${resourceId}/index`, {
      method: 'POST',
      body: JSON.stringify({ 
        index_level: level, 
        confirmed,
      }),
    });
  },

  // ----------------------------------------
  // Search
  // ----------------------------------------

  async search(
    query: string,
    options?: {
      collection_ids?: number[];
      resource_types?: ResourceType[];
      limit?: number;
      offset?: number;
    }
  ): Promise<SearchResponse> {
    const params = new URLSearchParams();
    params.append('q', query);
    
    if (options?.collection_ids?.length) {
      options.collection_ids.forEach(id => params.append('collection_ids', String(id)));
    }
    if (options?.resource_types?.length) {
      options.resource_types.forEach(type => params.append('resource_types', type));
    }
    if (options?.limit) params.append('limit', String(options.limit));
    if (options?.offset) params.append('offset', String(options.offset));
    
    return fetchAPI(`${KB_PREFIX}/search?${params.toString()}`);
  },

  // ----------------------------------------
  // Stats
  // ----------------------------------------

  async getStats(): Promise<KnowledgeStats> {
    return fetchAPI(`${KB_PREFIX}/stats`);
  },

  async estimateIndexingCost(data: {
    source_type: 'url' | 'text';
    source_url?: string;
    source_content?: string;
  }): Promise<CostEstimate> {
    return fetchAPI(`${KB_PREFIX}/estimate`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
};

// Export individual functions for flexibility
export const {
  listCollections,
  getCollection,
  createCollection,
  updateCollection,
  deleteCollection,
  listResources,
  getResource,
  createResource,
  previewUrl,
  addResourceFromUrl,
  addResourceText,
  uploadResource,
  deleteResource,
  reindexResource,
  getIndexEstimate,
  indexResource,
  search,
  getStats,
  estimateIndexingCost,
} = knowledgeApi;
