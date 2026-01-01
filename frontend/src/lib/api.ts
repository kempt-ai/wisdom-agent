/**
 * API client for communicating with the Wisdom Agent backend
 * Updated: Added fact-check API calls and project archive functionality
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

// Types
export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface ChatResponse {
  response: string;
  provider: string;
  model: string;
}

export interface Project {
  id?: string;
  name: string;
  project_type: string;
  description?: string;
  goals?: string[];
  created_at?: string;
  updated_at?: string;
  session_count?: number;
  is_archived?: boolean;  // NEW
  archived_at?: string;   // NEW
}

export interface Session {
  session_id: number;
  session_number: number;
  project_id: number;
  user_id: number;
  title?: string;
  session_type: string;
  llm_provider?: string;
  llm_model?: string;
  started_at?: string;
  ended_at?: string;
  message_count: number;
  has_summary?: boolean;
  has_reflection?: boolean;
}

export interface SessionMessage {
  message_id: number;
  session_id: number;
  role: string;
  content: string;
  created_at: string;
  message_index: number;
}

export interface SessionEndResult {
  session_id: number;
  ended_at: string;
  message_count: number;
  summary?: {
    session_id: number;
    summary_text: string;
    key_topics?: string[];
    learning_outcomes?: string[];
    created_at: string;
    updated_at: string;
  };
  reflection?: {
    session_id: number;
    reflection_text: string;
    scores: ReflectionScores;
    insights?: string[];
    growth_areas?: string[];
    created_at: string;
    updated_at: string;
  };
}

export interface Provider {
  id: string;
  name: string;
  enabled: boolean;
  model: string;
  api_key_set: boolean;
}

export interface HealthResponse {
  status: string;
  services: {
    api: boolean;
    anthropic: boolean;
    openai: boolean;
    nebius: boolean;
    memory?: boolean;
    reflection?: boolean;
    conversation?: boolean;
  };
  paths: {
    data_exists: boolean;
    philosophy_exists: boolean;
  };
}

export interface PhilosophyResponse {
  base_files: string[];
  available_domains: string[];
  available_organizations: string[];
}

export interface ReflectionScores {
  Awareness: number;
  Honesty: number;
  Accuracy: number;
  Competence: number;
  Compassion: number;
  'Loving-kindness': number;
  'Joyful-sharing': number;
  overall: number;
}

export interface Reflection {
  session_id: number;
  reflection_text: string;
  scores: ReflectionScores;
  created_at: string;
}

export interface ValuesInfo {
  values: Array<{
    name: string;
    description: string;
  }>;
}

// NEW - Fact Check Types
export interface FactCheckTriggerResponse {
  review_id: number;
  session_id: number;
  status: string;
  poll_url: string;
  message: string;
}

export interface FactCheckResult {
  id: number;
  title?: string;
  source_type: string;
  source_url?: string;
  status: string;
  created_at: string;
  completed_at?: string;
  factual_verdict?: string;
  logic_verdict?: string;
  wisdom_verdict?: string;
  overall_verdict?: string;
  claims?: FactCheckClaim[];
  logic_analysis?: LogicAnalysis;
  wisdom_evaluation?: WisdomEvaluation;
}

export interface FactCheckClaim {
  id: number;
  claim_text: string;
  verdict: string;
  confidence: number;
  explanation: string;
  sources?: string[];
}

export interface LogicAnalysis {
  overall_soundness: string;
  fallacies_detected: string[];
  argument_structure: string;
  recommendations: string[];
}

export interface WisdomEvaluation {
  overall_alignment: string;
  values_assessment: Record<string, { score: number; explanation: string }>;
  something_deeperism_alignment: string;
  recommendations: string[];
}

export interface FactCheckListResponse {
  reviews: FactCheckSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface FactCheckSummary {
  id: number;
  title?: string;
  source_type: string;
  source_url?: string;
  status: string;
  created_at: string;
  factual_verdict?: string;
  wisdom_verdict?: string;
}

// API functions

// Health & Status
export async function getHealth(): Promise<HealthResponse> {
  return fetchAPI('/health');
}

export async function getPhilosophy(): Promise<PhilosophyResponse> {
  return fetchAPI('/philosophy');
}

// Chat - Fixed endpoint (was /chat/complete, should be /api/chat/complete)
export async function sendMessage(
  messages: Message[],
  systemPrompt?: string
): Promise<ChatResponse> {
  return fetchAPI('/api/chat/complete', {
    method: 'POST',
    body: JSON.stringify({
      messages,
      system_prompt: systemPrompt,
    }),
  });
}

// Alternative: Ask endpoint with philosophy grounding
export async function askQuestion(
  question: string,
  domain?: string,
  organization?: string,
  project?: string
): Promise<ChatResponse> {
  return fetchAPI('/api/chat/ask', {
    method: 'POST',
    body: JSON.stringify({
      question,
      domain,
      organization,
      project,
    }),
  });
}

export async function getProviders(): Promise<Provider[]> {
  return fetchAPI('/api/chat/providers');
}

export async function setActiveProvider(providerId: string): Promise<void> {
  await fetchAPI(`/api/chat/providers/${providerId}/activate`, {
    method: 'POST',
  });
}

// Projects - Fixed endpoints
export async function getProjects(includeArchived: boolean = false): Promise<Project[]> {
  const params = includeArchived ? '?include_archived=true' : '';
  return fetchAPI(`/api/projects/${params}`);
}

// NEW - Get only archived projects
export async function getArchivedProjects(): Promise<Project[]> {
  return fetchAPI('/api/projects/?archived_only=true');
}

export async function getProject(name: string): Promise<Project> {
  return fetchAPI(`/api/projects/${name}`);
}

export async function createProject(project: Partial<Project>): Promise<Project> {
  return fetchAPI('/api/projects/', {
    method: 'POST',
    body: JSON.stringify(project),
  });
}

export async function updateProject(name: string, updates: Partial<Project>): Promise<Project> {
  return fetchAPI(`/api/projects/${name}`, {
    method: 'PUT',
    body: JSON.stringify(updates),
  });
}

export async function deleteProject(name: string): Promise<void> {
  await fetchAPI(`/api/projects/${name}`, {
    method: 'DELETE',
  });
}

// NEW - Archive/Unarchive projects
export async function archiveProject(nameOrId: string): Promise<Project> {
  return fetchAPI(`/api/projects/${nameOrId}/archive`, {
    method: 'POST',
  });
}

export async function unarchiveProject(nameOrId: string): Promise<Project> {
  return fetchAPI(`/api/projects/${nameOrId}/unarchive`, {
    method: 'POST',
  });
}

// Sessions - Fixed and expanded for Day 3
export async function startSession(
  projectId: number = 1,
  userId: number = 1,
  title?: string,
  sessionType: string = 'general'
): Promise<Session> {
  return fetchAPI('/api/sessions/start', {
    method: 'POST',
    body: JSON.stringify({
      project_id: projectId,
      user_id: userId,
      title,
      session_type: sessionType,
    }),
  });
}

export async function getSessions(
  projectId?: number,
  userId?: number,
  limit: number = 50
): Promise<Session[]> {
  const params = new URLSearchParams();
  if (projectId) params.append('project_id', String(projectId));
  if (userId) params.append('user_id', String(userId));
  params.append('limit', String(limit));
  
  return fetchAPI(`/api/sessions/?${params.toString()}`);
}

export async function getSession(sessionId: number): Promise<Session> {
  return fetchAPI(`/api/sessions/${sessionId}`);
}

export async function endSession(
  sessionId: number,
  generateSummary: boolean = true,
  generateReflection: boolean = true
): Promise<SessionEndResult> {
  return fetchAPI(`/api/sessions/${sessionId}/end`, {
    method: 'POST',
    body: JSON.stringify({
      generate_summary: generateSummary,
      generate_reflection: generateReflection,
    }),
  });
}

export async function deleteSession(sessionId: number): Promise<void> {
  await fetchAPI(`/api/sessions/${sessionId}`, {
    method: 'DELETE',
  });
}

export async function getSessionMessages(sessionId: number): Promise<{ session_id: number; messages: Message[] }> {
  return fetchAPI(`/api/sessions/${sessionId}/messages`);
}

export async function addMessageToSession(
  sessionId: number,
  role: string,
  content: string,
  storeInMemory: boolean = true
): Promise<SessionMessage> {
  return fetchAPI(`/api/sessions/${sessionId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ 
      role, 
      content,
      store_in_memory: storeInMemory,
    }),
  });
}

// Session Summaries
export async function getSessionSummary(sessionId: number) {
  return fetchAPI(`/api/sessions/${sessionId}/summary`);
}

export async function generateSessionSummary(sessionId: number, forceRegenerate: boolean = false) {
  const params = forceRegenerate ? '?force_regenerate=true' : '';
  return fetchAPI(`/api/sessions/${sessionId}/summary${params}`, {
    method: 'POST',
  });
}

// Reflections - Fixed endpoints
export async function getSessionReflection(sessionId: number): Promise<Reflection> {
  return fetchAPI(`/api/sessions/${sessionId}/reflection`);
}

export async function generateSessionReflection(sessionId: number, forceRegenerate: boolean = false): Promise<Reflection> {
  const params = forceRegenerate ? '?force_regenerate=true' : '';
  return fetchAPI(`/api/sessions/${sessionId}/reflection${params}`, {
    method: 'POST',
  });
}

// Reflection Service endpoints
export async function getValuesInfo(): Promise<ValuesInfo> {
  return fetchAPI('/api/reflection/values');
}

export async function generateValuesReflection(
  sessionId: number,
  messages: Message[]
): Promise<{ reflection_text: string; scores: ReflectionScores }> {
  return fetchAPI('/api/reflection/values-reflection', {
    method: 'POST',
    body: JSON.stringify({
      session_id: sessionId,
      messages,
    }),
  });
}

export async function completeSession(
  sessionId: number,
  messages: Message[]
): Promise<SessionEndResult> {
  return fetchAPI(`/api/reflection/complete-session?session_id=${sessionId}`, {
    method: 'POST',
    body: JSON.stringify(messages),
  });
}

// ============================================
// NEW - Fact Check API Functions
// ============================================

/**
 * Trigger a fact check within a session
 */
export async function triggerFactCheck(
  sessionId: number,
  content: string,
  sourceType: 'text' | 'url' = 'text',
  sourceUrl?: string,
  title?: string
): Promise<FactCheckTriggerResponse> {
  return fetchAPI(`/api/sessions/${sessionId}/factcheck`, {
    method: 'POST',
    body: JSON.stringify({
      content,
      source_type: sourceType,
      source_url: sourceUrl,
      title,
    }),
  });
}

/**
 * Quick fact-check a URL within a session
 */
export async function factCheckUrl(sessionId: number, url: string): Promise<FactCheckTriggerResponse> {
  return fetchAPI(`/api/sessions/${sessionId}/factcheck-url?url=${encodeURIComponent(url)}`, {
    method: 'POST',
  });
}

/**
 * Quick fact-check a claim within a session
 */
export async function factCheckClaim(sessionId: number, claim: string): Promise<FactCheckTriggerResponse> {
  return fetchAPI(`/api/sessions/${sessionId}/factcheck-claim?claim=${encodeURIComponent(claim)}`, {
    method: 'POST',
  });
}

/**
 * Get all fact checks for a session
 */
export async function getSessionFactChecks(
  sessionId: number,
  includeDetails: boolean = false
): Promise<{ session_id: number; factchecks: FactCheckSummary[]; total: number }> {
  const params = includeDetails ? '?include_details=true' : '';
  return fetchAPI(`/api/sessions/${sessionId}/factchecks${params}`);
}

/**
 * Create a standalone fact check review (not tied to a session)
 */
export async function createFactCheckReview(
  sourceType: 'text' | 'url' | 'file',
  content: string,
  options?: {
    sourceUrl?: string;
    title?: string;
    sessionId?: number;
    projectId?: number;
  }
): Promise<FactCheckSummary> {
  return fetchAPI('/api/reviews', {
    method: 'POST',
    body: JSON.stringify({
      source_type: sourceType,
      source_content: sourceType === 'text' ? content : undefined,
      source_url: sourceType === 'url' ? content : options?.sourceUrl,
      title: options?.title,
      session_id: options?.sessionId,
      project_id: options?.projectId,
    }),
  });
}

/**
 * List all fact check reviews
 */
export async function listFactCheckReviews(options?: {
  projectId?: number;
  sessionId?: number;
  status?: string;
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<FactCheckListResponse> {
  const params = new URLSearchParams();
  if (options?.projectId) params.append('project_id', String(options.projectId));
  if (options?.sessionId) params.append('session_id', String(options.sessionId));
  if (options?.status) params.append('status', options.status);
  if (options?.search) params.append('search', options.search);
  if (options?.limit) params.append('limit', String(options.limit));
  if (options?.offset) params.append('offset', String(options.offset));
  
  return fetchAPI(`/api/reviews?${params.toString()}`);
}

/**
 * Get a single fact check review with full details
 */
export async function getFactCheckReview(reviewId: number): Promise<FactCheckResult> {
  return fetchAPI(`/api/reviews/${reviewId}`);
}

/**
 * Get the status of a fact check review (for polling)
 */
export async function getFactCheckStatus(reviewId: number): Promise<{ status: string; progress?: number }> {
  return fetchAPI(`/api/reviews/${reviewId}/status`);
}

/**
 * Delete a fact check review
 */
export async function deleteFactCheckReview(reviewId: number): Promise<void> {
  await fetchAPI(`/api/reviews/${reviewId}`, {
    method: 'DELETE',
  });
}

/**
 * Browse all completed fact checks (repository view)
 */
export async function browseFactChecks(options?: {
  search?: string;
  factualVerdict?: string;
  wisdomVerdict?: string;
  limit?: number;
  offset?: number;
}): Promise<FactCheckListResponse> {
  const params = new URLSearchParams();
  if (options?.search) params.append('search', options.search);
  if (options?.factualVerdict) params.append('factual_verdict', options.factualVerdict);
  if (options?.wisdomVerdict) params.append('wisdom_verdict', options.wisdomVerdict);
  if (options?.limit) params.append('limit', String(options.limit));
  if (options?.offset) params.append('offset', String(options.offset));
  
  return fetchAPI(`/api/reviews/repository/all?${params.toString()}`);
}

// Memory - Fixed endpoints
export async function getMemoryStatus() {
  return fetchAPI('/api/memory/status');
}

export async function initializeMemory() {
  return fetchAPI('/api/memory/initialize', {
    method: 'POST',
  });
}

export async function searchMemory(query: string, nResults: number = 5) {
  return fetchAPI('/api/memory/search', {
    method: 'POST',
    body: JSON.stringify({
      query,
      n_results: nResults,
    }),
  });
}

export async function storeMemory(content: string, metadata: Record<string, unknown> = {}) {
  return fetchAPI('/api/memory/store', {
    method: 'POST',
    body: JSON.stringify({ content, metadata }),
  });
}

export async function getMemoryStats() {
  return fetchAPI('/api/memory/stats');
}

// Pedagogy - Fixed endpoints
export async function getPedagogyStatus() {
  return fetchAPI('/api/pedagogy/status');
}

export async function initializePedagogy() {
  return fetchAPI('/api/pedagogy/initialize', {
    method: 'POST',
  });
}

export async function detectSessionType(messages: Message[]): Promise<{ session_type: string; confidence: number }> {
  return fetchAPI('/api/pedagogy/detect-session-type', {
    method: 'POST',
    body: JSON.stringify({ messages }),
  });
}

export async function generateLearningPlan(
  subject: string,
  currentLevel: string,
  learningGoal: string,
  timeCommitment?: string
): Promise<{ plan: string }> {
  return fetchAPI('/api/pedagogy/learning-plan', {
    method: 'POST',
    body: JSON.stringify({
      subject,
      current_level: currentLevel,
      learning_goal: learningGoal,
      time_commitment: timeCommitment,
    }),
  });
}

// Files
export async function uploadFile(file: File): Promise<{ filename: string; path: string }> {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch(`${API_BASE}/api/files/upload`, {
    method: 'POST',
    body: formData,
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(error.detail);
  }
  
  return response.json();
}

export async function getUploadedFiles(): Promise<Array<{ filename: string; size: number; uploaded_at: string }>> {
  return fetchAPI('/api/files/uploads');
}

export async function extractTextFromFile(filename: string): Promise<{ text: string; pages?: number }> {
  return fetchAPI('/api/files/extract-text', {
    method: 'POST',
    body: JSON.stringify({ filename }),
  });
}
