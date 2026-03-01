/**
 * Arguments Builder (AB) API client for Wisdom Agent
 * Handles investigations, definitions, claims, evidence, counterarguments
 *
 * Follows patterns from knowledge-api.ts
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// AB endpoints are under /api/ab
const AB_PREFIX = '/api/ab';

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

  // 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// ============================================
// Types (matching backend ab_schemas.py)
// ============================================

export interface InvestigationSummary {
  id: number;
  title: string;
  slug: string;
  status: string;
  created_at: string;
  updated_at: string;
  definition_count: number;
  claim_count: number;
}

export interface Investigation {
  id: number;
  title: string;
  slug: string;
  overview_html: string;
  status: string;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  version: number;
  definitions: Definition[];
  claims: ABClaim[];
}

export interface Definition {
  id: number;
  investigation_id: number;
  term: string;
  slug: string;
  definition_html: string;
  see_also: string[];
  created_at: string;
  updated_at: string;
}

export interface LinkedInvestigationRef {
  id: number;
  title: string;
  slug: string;
}

export interface ABClaim {
  id: number;
  investigation_id: number;
  title: string;
  slug: string;
  claim_text: string;
  exposition_html: string | null;
  status: string;
  temporal_note: string | null;
  position: number;
  created_at: string;
  updated_at: string;
  evidence: ABEvidence[];
  counterarguments: Counterargument[];
  linked_investigation_id: number | null;
  linked_investigation: LinkedInvestigationRef | null;
}

export interface SupportingQuote {
  quote_type: string;  // "quote" | "example" | "data" | "statistic" | "citation" | "testimony"
  content: string;
  outline_node_id?: string;  // e.g. "evidence-98"
}

export interface ABEvidence {
  id: number;
  claim_id: number;
  kb_resource_id: number | null;
  source_title: string | null;
  source_url: string | null;
  source_type: string | null;
  key_quote: string | null;
  key_point: string | null;
  position: number;
  created_at: string;
  source_anchor_type: string | null;
  source_anchor_data: Record<string, any> | null;
  supporting_quotes: SupportingQuote[] | null;
}

export interface Counterargument {
  id: number;
  claim_id: number;
  counter_text: string;
  rebuttal_text: string | null;
  position: number;
  created_at: string;
}

// ============================================
// Types for KB parsed content
// ============================================

/** A parse run stored for a KB resource */
export interface ResourceParse {
  id: number;
  parse_level: 'light' | 'standard' | 'full';
  parser_model: string;
  parsed_at: string;
  main_thesis: string | null;
  cost_dollars: number;
  claim_count: number;
}

export interface ResourceParsesResponse {
  resource_id: number;
  parses: ResourceParse[];
}

/** A claim extracted during parsing */
export interface ParsedClaim {
  id: number;
  parsed_resource_id: number;
  claim_text: string;
  claim_type: 'factual' | 'interpretive' | 'prescriptive';
  context: string | null;
  source_quote: string | null;
  argument_title: string | null;
  confidence: number;
  position_in_doc: number | null;
  parent_claim_id: number | null;
  verification_status: string | null;
  evidence: ParsedEvidence[];
  sub_claims: ParsedClaim[];
  created_at: string;
}

export interface ParsedEvidence {
  id: number;
  claim_id: number;
  evidence_type: string;
  content: string;
  source_url: string | null;
  source_title: string | null;
  position: number;
  created_at: string;
}

/** A node in the parsed resource outline tree */
export interface OutlineNode {
  id: string;
  node_type: 'argument' | 'evidence';
  title: string;
  content?: string;
  claim_type?: 'factual' | 'interpretive' | 'prescriptive' | null;
  verification_status?: string | null;
  source_url?: string | null;
  children?: OutlineNode[];
  metadata?: Record<string, unknown>;
}

export interface OutlineResponse {
  parsed_resource_id: number;
  resource_id: number;
  resource_name: string;
  main_thesis: string | null;
  summary: string | null;
  outline: OutlineNode[];
}

// The arguments/parsing endpoints use /api/arguments prefix (not /api/ab)
const ARGS_PREFIX = '/api/arguments';

// ============================================
// API Functions
// ============================================

export const argumentsApi = {
  // ----------------------------------------
  // Investigations
  // ----------------------------------------

  async listInvestigations(): Promise<InvestigationSummary[]> {
    return fetchAPI<InvestigationSummary[]>(`${AB_PREFIX}/investigations`);
  },

  async getInvestigation(slug: string): Promise<Investigation> {
    return fetchAPI<Investigation>(`${AB_PREFIX}/investigations/${encodeURIComponent(slug)}`);
  },

  async createInvestigation(data: {
    title: string;
    overview_html?: string;
    status?: string;
  }): Promise<Investigation> {
    return fetchAPI<Investigation>(`${AB_PREFIX}/investigations`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async updateInvestigation(slug: string, data: {
    title?: string;
    overview_html?: string;
    status?: string;
  }): Promise<Investigation> {
    return fetchAPI<Investigation>(`${AB_PREFIX}/investigations/${encodeURIComponent(slug)}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  async deleteInvestigation(slug: string): Promise<void> {
    await fetchAPI(`${AB_PREFIX}/investigations/${encodeURIComponent(slug)}`, {
      method: 'DELETE',
    });
  },

  // ----------------------------------------
  // Definitions
  // ----------------------------------------

  async listDefinitions(slug: string): Promise<Definition[]> {
    return fetchAPI<Definition[]>(`${AB_PREFIX}/investigations/${encodeURIComponent(slug)}/definitions`);
  },

  async getDefinition(slug: string, defSlug: string): Promise<Definition> {
    return fetchAPI<Definition>(
      `${AB_PREFIX}/investigations/${encodeURIComponent(slug)}/definitions/${encodeURIComponent(defSlug)}`
    );
  },

  async createDefinition(slug: string, data: {
    term: string;
    definition_html?: string;
    see_also?: string[];
  }): Promise<Definition> {
    return fetchAPI<Definition>(
      `${AB_PREFIX}/investigations/${encodeURIComponent(slug)}/definitions`,
      { method: 'POST', body: JSON.stringify(data) }
    );
  },

  async updateDefinition(slug: string, defSlug: string, data: {
    term?: string;
    definition_html?: string;
    see_also?: string[];
  }): Promise<Definition> {
    return fetchAPI<Definition>(
      `${AB_PREFIX}/investigations/${encodeURIComponent(slug)}/definitions/${encodeURIComponent(defSlug)}`,
      { method: 'PUT', body: JSON.stringify(data) }
    );
  },

  // ----------------------------------------
  // Claims
  // ----------------------------------------

  async listClaims(slug: string): Promise<ABClaim[]> {
    return fetchAPI<ABClaim[]>(`${AB_PREFIX}/investigations/${encodeURIComponent(slug)}/claims`);
  },

  async getClaim(slug: string, claimSlug: string): Promise<ABClaim> {
    return fetchAPI<ABClaim>(
      `${AB_PREFIX}/investigations/${encodeURIComponent(slug)}/claims/${encodeURIComponent(claimSlug)}`
    );
  },

  async createClaim(slug: string, data: {
    title: string;
    claim_text: string;
    exposition_html?: string;
    status?: string;
    temporal_note?: string;
    position?: number;
    linked_investigation_id?: number | null;
  }): Promise<ABClaim> {
    return fetchAPI<ABClaim>(
      `${AB_PREFIX}/investigations/${encodeURIComponent(slug)}/claims`,
      { method: 'POST', body: JSON.stringify(data) }
    );
  },

  async updateClaim(slug: string, claimSlug: string, data: {
    title?: string;
    claim_text?: string;
    exposition_html?: string;
    status?: string;
    temporal_note?: string;
    position?: number;
    linked_investigation_id?: number | null;
  }): Promise<ABClaim> {
    return fetchAPI<ABClaim>(
      `${AB_PREFIX}/investigations/${encodeURIComponent(slug)}/claims/${encodeURIComponent(claimSlug)}`,
      { method: 'PUT', body: JSON.stringify(data) }
    );
  },

  // ----------------------------------------
  // Evidence
  // ----------------------------------------

  async createEvidence(claimId: number, data: {
    source_title?: string;
    source_url?: string;
    source_type?: string;
    key_quote?: string;
    key_point?: string;
    kb_resource_id?: number;
    position?: number;
    source_anchor_type?: string;
    source_anchor_data?: Record<string, any>;
    supporting_quotes?: SupportingQuote[];
  }): Promise<ABEvidence> {
    return fetchAPI<ABEvidence>(
      `${AB_PREFIX}/claims/${claimId}/evidence`,
      { method: 'POST', body: JSON.stringify(data) }
    );
  },

  async updateEvidence(evidenceId: number, data: {
    source_title?: string;
    source_url?: string;
    source_type?: string;
    key_quote?: string;
    key_point?: string;
    position?: number;
    source_anchor_type?: string;
    source_anchor_data?: Record<string, any>;
    supporting_quotes?: SupportingQuote[];
  }): Promise<ABEvidence> {
    return fetchAPI<ABEvidence>(
      `${AB_PREFIX}/evidence/${evidenceId}`,
      { method: 'PUT', body: JSON.stringify(data) }
    );
  },

  async reorderClaim(claimId: number, direction: 'up' | 'down'): Promise<void> {
    await fetchAPI(
      `${AB_PREFIX}/claims/${claimId}/reorder?direction=${direction}`,
      { method: 'POST' }
    );
  },

  async reorderEvidence(evidenceId: number, direction: 'up' | 'down'): Promise<void> {
    await fetchAPI(
      `${AB_PREFIX}/evidence/${evidenceId}/reorder?direction=${direction}`,
      { method: 'POST' }
    );
  },

  // ----------------------------------------
  // Counterarguments
  // ----------------------------------------

  async createCounterargument(claimId: number, data: {
    counter_text: string;
    rebuttal_text?: string;
  }): Promise<Counterargument> {
    return fetchAPI<Counterargument>(
      `${AB_PREFIX}/claims/${claimId}/counterarguments`,
      { method: 'POST', body: JSON.stringify(data) }
    );
  },

  async updateCounterargument(caId: number, data: {
    counter_text?: string;
    rebuttal_text?: string;
  }): Promise<Counterargument> {
    return fetchAPI<Counterargument>(
      `${AB_PREFIX}/counterarguments/${caId}`,
      { method: 'PUT', body: JSON.stringify(data) }
    );
  },

  async deleteCounterargument(caId: number): Promise<void> {
    await fetchAPI(
      `${AB_PREFIX}/counterarguments/${caId}`,
      { method: 'DELETE' }
    );
  },

  async reorderCounterargument(caId: number, direction: 'up' | 'down'): Promise<void> {
    await fetchAPI(
      `${AB_PREFIX}/counterarguments/${caId}/reorder?direction=${direction}`,
      { method: 'POST' }
    );
  },

  // ----------------------------------------
  // KB Parsed Content
  // ----------------------------------------

  async getResourceParses(resourceId: number): Promise<ResourceParsesResponse> {
    return fetchAPI<ResourceParsesResponse>(
      `${ARGS_PREFIX}/resource/${resourceId}/parses`
    );
  },

  async getParsedClaims(parsedResourceId: number): Promise<ParsedClaim[]> {
    return fetchAPI<ParsedClaim[]>(
      `${ARGS_PREFIX}/parsed/${parsedResourceId}/claims`
    );
  },

  async getOutline(parsedResourceId: number): Promise<OutlineResponse> {
    return fetchAPI<OutlineResponse>(
      `${ARGS_PREFIX}/parsed/${parsedResourceId}/outline`
    );
  },
};

// Export individual functions for flexibility
export const {
  listInvestigations,
  getInvestigation,
  createInvestigation,
  updateInvestigation,
  deleteInvestigation,
  listDefinitions,
  getDefinition,
  createDefinition,
  updateDefinition,
  listClaims,
  getClaim,
  createClaim,
  updateClaim,
  createEvidence,
  updateEvidence,
  getResourceParses,
  getParsedClaims,
  getOutline,
} = argumentsApi;
