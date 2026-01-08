/**
 * Knowledge Base API Client
 * 
 * TypeScript client for interacting with the Knowledge Base backend API.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ============================================================================
// TYPES
// ============================================================================

export type CollectionType = 'research' | 'fiction' | 'learning' | 'general';
export type ResourceType = 'document' | 'fiction_book' | 'nonfiction_book' | 'article' | 'learning_module';
export type SourceType = 'upload' | 'url' | 'text' | 'api';
export type IndexLevel = 'none' | 'light' | 'standard' | 'full';
export type IndexStatus = 'pending' | 'indexing' | 'completed' | 'failed';

export interface Collection {
  id: number;
  user_id: number;
  project_id?: number;
  name: string;
  description?: string;
  collection_type: CollectionType;
  visibility: string;
  tags: string[];
  settings: Record<string, any>;
  resource_count: number;
  total_tokens: number;
  created_at: string;
  updated_at: string;
}

export interface CollectionSummary {
  id: number;
  name: string;
  collection_type: CollectionType;
  resource_count: number;
  updated_at: string;
}

export interface Resource {
  id: number;
  collection_id: number;
  user_id: number;
  name: string;
  description?: string;
  resource_type: ResourceType;
  source_type: SourceType;
  source_url?: string;
  token_count: number;
  index_level: IndexLevel;
  index_status: IndexStatus;
  index_cost_tokens: number;
  index_cost_dollars: number;
  visibility: string;
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface ResourceSummary {
  id: number;
  name: string;
  resource_type: ResourceType;
  token_count: number;
  index_level: IndexLevel;
  index_status: IndexStatus;
  updated_at: string;
}

export interface IndexEstimate {
  resource_id: number;
  resource_name: string;
  token_count: number;
  index_level: IndexLevel;
  model_id: string;
  model_name: string;
  estimated_input_tokens: number;
  estimated_output_tokens: number;
  estimated_cost: number;
  budget_remaining: number;
  can_afford: boolean;
  warning_message?: string;
  alternatives: Array<{
    model_id: string;
    model_name: string;
    provider: string;
    tier: string;
    estimated_cost: number;
  }>;
}

export interface UrlPreviewResult {
  success: boolean;
  url: string;
  title?: string;
  author?: string;
  publish_date?: string;
  description?: string;
  word_count: number;
  content_type: string;
  content_preview?: string;
  token_estimate?: number;
  indexing_cost_estimates?: {
    light: { estimated_tokens: number; estimated_cost: number };
    standard: { estimated_tokens: number; estimated_cost: number };
    full: { estimated_tokens: number; estimated_cost: number };
  };
  extractor_used?: string;
  error_message?: string;
}

export interface SearchResult {
  resource_id: number;
  resource_name: string;
  resource_type: ResourceType;
  collection_id: number;
  collection_name: string;
  match_type: string;
  relevance_score: number;
  matched_text?: string;
  context?: string;
  index_type?: string;
}

export interface SearchResponse {
  query: string;
  total_results: number;
  results: SearchResult[];
  search_time_ms: number;
}

export interface KnowledgeStats {
  collections: number;
  resources: number;
  total_tokens: number;
  total_indexing_cost: number;
  indexes: number;
  characters: number;
  author_voices: number;
}

// ============================================================================
// API CLIENT
// ============================================================================

class KnowledgeAPI {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return undefined as T;
    }

    return response.json();
  }

  // ==========================================================================
  // COLLECTIONS
  // ==========================================================================

  async listCollections(projectId?: number, type?: CollectionType): Promise<CollectionSummary[]> {
    let endpoint = '/knowledge/collections';
    const params = new URLSearchParams();
    if (projectId) params.append('project_id', projectId.toString());
    if (type) params.append('collection_type', type);
    if (params.toString()) endpoint += `?${params}`;
    
    return this.request<CollectionSummary[]>(endpoint);
  }

  async getCollection(id: number): Promise<Collection> {
    return this.request<Collection>(`/knowledge/collections/${id}`);
  }

  async createCollection(data: {
    name: string;
    description?: string;
    collection_type?: CollectionType;
    project_id?: number;
    tags?: string[];
  }): Promise<Collection> {
    return this.request<Collection>('/knowledge/collections', {
      method: 'POST',
      body: JSON.stringify({
        collection_type: 'general',
        visibility: 'private',
        tags: [],
        settings: {},
        ...data,
      }),
    });
  }

  async updateCollection(id: number, data: Partial<{
    name: string;
    description: string;
    collection_type: CollectionType;
    tags: string[];
  }>): Promise<Collection> {
    return this.request<Collection>(`/knowledge/collections/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteCollection(id: number): Promise<void> {
    return this.request<void>(`/knowledge/collections/${id}`, {
      method: 'DELETE',
    });
  }

  // ==========================================================================
  // RESOURCES
  // ==========================================================================

  async listResources(collectionId: number): Promise<ResourceSummary[]> {
    return this.request<ResourceSummary[]>(
      `/knowledge/collections/${collectionId}/resources`
    );
  }

  async getResource(id: number): Promise<Resource> {
    return this.request<Resource>(`/knowledge/resources/${id}`);
  }

  async addResourceText(
    collectionId: number,
    data: {
      name: string;
      content: string;
      description?: string;
      resource_type?: ResourceType;
    }
  ): Promise<Resource> {
    return this.request<Resource>(
      `/knowledge/collections/${collectionId}/resources`,
      {
        method: 'POST',
        body: JSON.stringify({
          source_type: 'text',
          resource_type: 'document',
          visibility: 'private',
          metadata: {},
          ...data,
        }),
      }
    );
  }

  async addResourceFromUrl(
    collectionId: number,
    data: {
      url: string;
      name?: string;
      description?: string;
      resource_type?: string;
    }
  ): Promise<{ resource: Resource; extraction: Record<string, any> }> {
    return this.request(
      `/knowledge/collections/${collectionId}/from-url`,
      {
        method: 'POST',
        body: JSON.stringify({
          resource_type: 'article',
          ...data,
        }),
      }
    );
  }

  async uploadResource(
    collectionId: number,
    file: File,
    name?: string,
    description?: string,
    resourceType: string = 'document'
  ): Promise<Resource> {
    const formData = new FormData();
    formData.append('file', file);
    if (name) formData.append('name', name);
    if (description) formData.append('description', description);
    formData.append('resource_type', resourceType);

    const response = await fetch(
      `${this.baseUrl}/knowledge/collections/${collectionId}/upload`,
      {
        method: 'POST',
        body: formData,
      }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(error.detail);
    }

    return response.json();
  }

  async refreshResource(id: number): Promise<{ resource: Resource; extraction: Record<string, any> }> {
    return this.request(`/knowledge/resources/${id}/refresh`, {
      method: 'POST',
    });
  }

  async deleteResource(id: number): Promise<void> {
    return this.request<void>(`/knowledge/resources/${id}`, {
      method: 'DELETE',
    });
  }

  // ==========================================================================
  // URL PREVIEW
  // ==========================================================================

  async previewUrl(url: string): Promise<UrlPreviewResult> {
    return this.request<UrlPreviewResult>('/knowledge/preview-url', {
      method: 'POST',
      body: JSON.stringify({ url }),
    });
  }

  // ==========================================================================
  // INDEXING
  // ==========================================================================

  async getIndexEstimate(
    resourceId: number,
    level: IndexLevel = 'standard',
    modelId?: string
  ): Promise<IndexEstimate> {
    let endpoint = `/knowledge/resources/${resourceId}/index-estimate?level=${level}`;
    if (modelId) endpoint += `&model_id=${modelId}`;
    return this.request<IndexEstimate>(endpoint);
  }

  async indexResource(
    resourceId: number,
    level: IndexLevel,
    confirmed: boolean = false,
    modelId?: string
  ): Promise<any> {
    return this.request(`/knowledge/resources/${resourceId}/index`, {
      method: 'POST',
      body: JSON.stringify({
        index_level: level,
        confirmed,
        model_id: modelId,
      }),
    });
  }

  // ==========================================================================
  // SEARCH
  // ==========================================================================

  async search(
    query: string,
    options?: {
      collection_ids?: number[];
      resource_types?: ResourceType[];
      limit?: number;
    }
  ): Promise<SearchResponse> {
    return this.request<SearchResponse>('/knowledge/search', {
      method: 'POST',
      body: JSON.stringify({
        query,
        limit: 10,
        semantic: true,
        include_content: false,
        ...options,
      }),
    });
  }

  async searchSimple(query: string, limit: number = 10): Promise<SearchResponse> {
    return this.request<SearchResponse>(
      `/knowledge/search?q=${encodeURIComponent(query)}&limit=${limit}`
    );
  }

  // ==========================================================================
  // STATS
  // ==========================================================================

  async getStats(): Promise<KnowledgeStats> {
    return this.request<KnowledgeStats>('/knowledge/stats');
  }

  async getHealth(): Promise<{ status: string; database: string }> {
    return this.request('/knowledge/health');
  }
}

// Export singleton instance
export const knowledgeApi = new KnowledgeAPI();

// Export class for custom instances
export { KnowledgeAPI };
