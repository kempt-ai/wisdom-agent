/**
 * Knowledge Base API client for Wisdom Agent
 * Handles collections, resources, and search functionality
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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

export interface CollectionSummary {
  id: number;
  name: string;
  description?: string;
  collection_type: CollectionType;
  resource_count: number;
  created_at: string;
  updated_at: string;
}

export interface Collection {
  id: number;
  name: string;
  description?: string;
  collection_type: CollectionType;
  created_at: string;
  updated_at: string;
  resources?: Resource[];
}

export interface Resource {
  id: number;
  collection_id: number;
  name: string;
  resource_type: ResourceType;
  source_type: 'url' | 'text' | 'file';
  source_url?: string;
  content_preview?: string;
  status: ResourceStatus;
  error_message?: string;
  token_count?: number;
  indexing_cost?: number;
  created_at: string;
  indexed_at?: string;
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
  model_override?: string;
  provider_override?: string;
}

export interface CostEstimate {
  content_tokens: number;
  estimated_cost: number;
  model_id: string;
  model_name: string;
  provider: string;
  estimates_by_model?: Array<{
    model_id: string;
    model_name: string;
    provider: string;
    estimated_cost: number;
    tier: string;
    description?: string;
  }>;
  recommended?: {
    model_id: string;
    provider: string;
  };
}

// ============================================
// API Functions Object
// ============================================

export const knowledgeApi = {
  // ----------------------------------------
  // Collections
  // ----------------------------------------
  
  /**
   * List all collections, optionally filtered by type
   */
  async listCollections(
    search?: string,
    collectionType?: CollectionType
  ): Promise<CollectionSummary[]> {
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (collectionType) params.append('collection_type', collectionType);
    
    const queryString = params.toString();
    const endpoint = `/api/knowledge/collections${queryString ? `?${queryString}` : ''}`;
    
    const response = await fetchAPI<{ collections: CollectionSummary[] } | CollectionSummary[]>(endpoint);
    
    // Handle both response formats
    return Array.isArray(response) ? response : response.collections;
  },

  /**
   * Get a single collection with its resources
   */
  async getCollection(id: number): Promise<Collection> {
    return fetchAPI(`/api/knowledge/collections/${id}`);
  },

  /**
   * Create a new collection
   */
  async createCollection(data: CreateCollectionRequest): Promise<Collection> {
    return fetchAPI('/api/knowledge/collections', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Update a collection
   */
  async updateCollection(id: number, data: Partial<CreateCollectionRequest>): Promise<Collection> {
    return fetchAPI(`/api/knowledge/collections/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  /**
   * Delete a collection and all its resources
   */
  async deleteCollection(id: number): Promise<void> {
    await fetchAPI(`/api/knowledge/collections/${id}`, {
      method: 'DELETE',
    });
  },

  // ----------------------------------------
  // Resources
  // ----------------------------------------

  /**
   * List resources in a collection
   */
  async listResources(collectionId: number): Promise<Resource[]> {
    const response = await fetchAPI<{ resources: Resource[] } | Resource[]>(
      `/api/knowledge/collections/${collectionId}/resources`
    );
    return Array.isArray(response) ? response : response.resources;
  },

  /**
   * Get a single resource
   */
  async getResource(resourceId: number): Promise<Resource> {
    return fetchAPI(`/api/knowledge/resources/${resourceId}`);
  },

  /**
   * Add a resource to a collection
   */
  async createResource(collectionId: number, data: CreateResourceRequest): Promise<Resource> {
    return fetchAPI(`/api/knowledge/collections/${collectionId}/resources`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Delete a resource
   */
  async deleteResource(resourceId: number): Promise<void> {
    await fetchAPI(`/api/knowledge/resources/${resourceId}`, {
      method: 'DELETE',
    });
  },

  /**
   * Retry indexing a failed resource
   */
  async reindexResource(resourceId: number): Promise<Resource> {
    return fetchAPI(`/api/knowledge/resources/${resourceId}/reindex`, {
      method: 'POST',
    });
  },

  // ----------------------------------------
  // Search
  // ----------------------------------------

  /**
   * Search across all collections or specific ones
   */
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
    
    return fetchAPI(`/api/knowledge/search?${params.toString()}`);
  },

  // ----------------------------------------
  // Stats & Cost Estimation
  // ----------------------------------------

  /**
   * Get knowledge base statistics
   */
  async getStats(): Promise<KnowledgeStats> {
    return fetchAPI('/api/knowledge/stats');
  },

  /**
   * Estimate indexing cost for content
   */
  async estimateIndexingCost(data: {
    source_type: 'url' | 'text';
    source_url?: string;
    source_content?: string;
  }): Promise<CostEstimate> {
    return fetchAPI('/api/knowledge/estimate', {
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
  deleteResource,
  reindexResource,
  search,
  getStats,
  estimateIndexingCost,
} = knowledgeApi;
