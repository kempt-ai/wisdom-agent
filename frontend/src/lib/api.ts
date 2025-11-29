/**
 * API client for communicating with the Wisdom Agent backend
 * 
 * Week 3 Day 2 - Fixed endpoint paths with /api prefix
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Generic fetch wrapper with error handling
async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  
  try {
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

    // Handle empty responses (204 No Content)
    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  } catch (error) {
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error('Cannot connect to backend. Is the server running on port 8000?');
    }
    throw error;
  }
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
  learning_goal?: string;
  created_at?: string;
  updated_at?: string;
  session_count?: number;
}

export interface Session {
  id: string;
  project_id?: string;
  session_number: number;
  started_at: string;
  ended_at?: string;
  message_count: number;
  has_summary: boolean;
  has_reflection: boolean;
}

export interface SessionMessage {
  id: string;
  role: string;
  content: string;
  created_at: string;
  message_index: number;
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
  version?: string;
  timestamp?: string;
  services?: Record<string, any>;
}

export interface PhilosophyResponse {
  base_files: string[];
  domain_files: string[];
  org_files: string[];
  project_files: string[];
  current_domain: string | null;
  current_org: string | null;
  current_project: string | null;
}

export interface ReflectionScores {
  awareness: number;
  honesty: number;
  accuracy: number;
  competence: number;
  compassion: number;
  loving_kindness: number;
  joyful_sharing: number;
  overall: number;
}

export interface Reflection {
  session_id: string;
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

export interface MemorySearchResult {
  content: string;
  metadata: Record<string, any>;
  similarity: number;
}

export interface LearningPlan {
  subject: string;
  current_level: string;
  learning_goal: string;
  time_commitment: string;
  plan?: string;
}

// API functions

// Health & Status
export async function getHealth(): Promise<HealthResponse> {
  return fetchAPI('/health');
}

export async function getPhilosophy(): Promise<PhilosophyResponse> {
  return fetchAPI('/philosophy');
}

// Chat - FIXED: Added /api prefix
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

export async function askQuestion(question: string): Promise<ChatResponse> {
  return fetchAPI('/api/chat/ask', {
    method: 'POST',
    body: JSON.stringify({ question }),
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

// Projects - FIXED: Added /api prefix
export async function getProjects(): Promise<Project[]> {
  return fetchAPI('/api/projects/');
}

export async function getProject(name: string): Promise<Project> {
  return fetchAPI(`/api/projects/${encodeURIComponent(name)}`);
}

export async function createProject(project: Partial<Project>): Promise<Project> {
  return fetchAPI('/api/projects/', {
    method: 'POST',
    body: JSON.stringify(project),
  });
}

export async function updateProject(name: string, updates: Partial<Project>): Promise<Project> {
  return fetchAPI(`/api/projects/${encodeURIComponent(name)}`, {
    method: 'PUT',
    body: JSON.stringify(updates),
  });
}

export async function deleteProject(name: string): Promise<void> {
  await fetchAPI(`/api/projects/${encodeURIComponent(name)}`, {
    method: 'DELETE',
  });
}

export async function getProjectOutline(name: string): Promise<any> {
  return fetchAPI(`/api/projects/${encodeURIComponent(name)}/outline`);
}

export async function getProjectLearningPlan(name: string): Promise<any> {
  return fetchAPI(`/api/projects/${encodeURIComponent(name)}/learning-plan`);
}

export async function updateProjectLearningPlan(name: string, plan: any): Promise<any> {
  return fetchAPI(`/api/projects/${encodeURIComponent(name)}/learning-plan`, {
    method: 'PUT',
    body: JSON.stringify(plan),
  });
}

// Sessions - FIXED: Added /api prefix
export async function getSessions(projectId?: string): Promise<Session[]> {
  const endpoint = projectId 
    ? `/api/sessions/?project_id=${projectId}` 
    : '/api/sessions/';
  return fetchAPI(endpoint);
}

export async function getSession(sessionId: string): Promise<Session> {
  return fetchAPI(`/api/sessions/${sessionId}`);
}

export async function createSession(projectId?: string): Promise<Session> {
  return fetchAPI('/api/sessions/', {
    method: 'POST',
    body: JSON.stringify({ project_id: projectId }),
  });
}

export async function endSession(sessionId: string): Promise<Session> {
  return fetchAPI(`/api/sessions/${sessionId}/end`, {
    method: 'POST',
  });
}

export async function getSessionMessages(sessionId: string): Promise<SessionMessage[]> {
  return fetchAPI(`/api/sessions/${sessionId}/messages`);
}

export async function addMessageToSession(
  sessionId: string,
  role: string,
  content: string
): Promise<SessionMessage> {
  return fetchAPI(`/api/sessions/${sessionId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ role, content }),
  });
}

// Reflections - FIXED: Added /api prefix
export async function getSessionReflection(sessionId: string): Promise<Reflection> {
  return fetchAPI(`/api/sessions/${sessionId}/reflection`);
}

export async function generateReflection(sessionId: string): Promise<Reflection> {
  return fetchAPI(`/api/sessions/${sessionId}/reflection/generate`, {
    method: 'POST',
  });
}

// Reflection Service endpoints
export async function getReflectionStatus(): Promise<any> {
  return fetchAPI('/api/reflection/status');
}

export async function initializeReflection(): Promise<any> {
  return fetchAPI('/api/reflection/initialize', { method: 'POST' });
}

export async function getValuesInfo(): Promise<ValuesInfo> {
  return fetchAPI('/api/reflection/values');
}

export async function generateValuesReflection(
  sessionId: number,
  messages: Message[]
): Promise<any> {
  return fetchAPI('/api/reflection/values-reflection', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId, messages }),
  });
}

export async function getMetaSummary(): Promise<any> {
  return fetchAPI('/api/reflection/meta-summary');
}

export async function getRecentSummaries(limit: number = 10): Promise<any[]> {
  return fetchAPI(`/api/reflection/recent-summaries?limit=${limit}`);
}

export async function getValuesTrend(days: number = 30): Promise<any> {
  return fetchAPI(`/api/reflection/values-trend?days=${days}`);
}

// Memory - FIXED: Added /api prefix
export async function getMemoryStatus(): Promise<any> {
  return fetchAPI('/api/memory/status');
}

export async function initializeMemory(): Promise<any> {
  return fetchAPI('/api/memory/initialize', { method: 'POST' });
}

export async function searchMemory(
  query: string, 
  limit: number = 5
): Promise<{ results: MemorySearchResult[] }> {
  return fetchAPI('/api/memory/search', {
    method: 'POST',
    body: JSON.stringify({ query, n_results: limit }),
  });
}

export async function storeMemory(
  content: string, 
  metadata: Record<string, any> = {}
): Promise<any> {
  return fetchAPI('/api/memory/store', {
    method: 'POST',
    body: JSON.stringify({ content, metadata }),
  });
}

export async function getMemoryStats(): Promise<any> {
  return fetchAPI('/api/memory/stats');
}

// Pedagogy - FIXED: Added /api prefix
export async function getPedagogyStatus(): Promise<any> {
  return fetchAPI('/api/pedagogy/status');
}

export async function initializePedagogy(): Promise<any> {
  return fetchAPI('/api/pedagogy/initialize', { method: 'POST' });
}

export async function detectSessionType(
  messages: Message[]
): Promise<{ session_type: string; confidence: number }> {
  return fetchAPI('/api/pedagogy/detect-session-type', {
    method: 'POST',
    body: JSON.stringify({ messages }),
  });
}

export async function generateLearningPlan(
  subject: string,
  currentLevel: string,
  learningGoal: string,
  timeCommitment: string
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

export async function suggestNextTopics(
  subject: string,
  completedTopics: string[],
  currentLevel: string
): Promise<{ topics: string[] }> {
  return fetchAPI('/api/pedagogy/suggest-next-topics', {
    method: 'POST',
    body: JSON.stringify({
      subject,
      completed_topics: completedTopics,
      current_level: currentLevel,
    }),
  });
}

// Files - FIXED: Added /api prefix
export async function getFileStatus(): Promise<any> {
  return fetchAPI('/api/files/status');
}

export async function getFileStats(): Promise<any> {
  return fetchAPI('/api/files/stats');
}

export async function listUploads(): Promise<any[]> {
  return fetchAPI('/api/files/uploads');
}

export async function uploadFile(file: File): Promise<any> {
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

export async function downloadFile(filename: string): Promise<Blob> {
  const response = await fetch(
    `${API_BASE}/api/files/download?filename=${encodeURIComponent(filename)}`
  );
  
  if (!response.ok) {
    throw new Error('Download failed');
  }
  
  return response.blob();
}

// Utility function to check if backend is reachable
export async function checkBackendConnection(): Promise<boolean> {
  try {
    await getHealth();
    return true;
  } catch {
    return false;
  }
}
