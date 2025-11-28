/**
 * API client for communicating with the Wisdom Agent backend
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
  version: string;
  timestamp: string;
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

// API functions

// Health & Status
export async function getHealth(): Promise<HealthResponse> {
  return fetchAPI('/health');
}

export async function getPhilosophy(): Promise<PhilosophyResponse> {
  return fetchAPI('/philosophy');
}

// Chat
export async function sendMessage(
  messages: Message[],
  systemPrompt?: string
): Promise<ChatResponse> {
  return fetchAPI('/chat/complete', {
    method: 'POST',
    body: JSON.stringify({
      messages,
      system_prompt: systemPrompt,
    }),
  });
}

export async function getProviders(): Promise<Provider[]> {
  return fetchAPI('/chat/providers');
}

export async function setActiveProvider(providerId: string): Promise<void> {
  await fetchAPI(`/chat/providers/${providerId}/activate`, {
    method: 'POST',
  });
}

// Projects
export async function getProjects(): Promise<Project[]> {
  return fetchAPI('/projects/');
}

export async function getProject(id: string): Promise<Project> {
  return fetchAPI(`/projects/${id}`);
}

export async function createProject(project: Partial<Project>): Promise<Project> {
  return fetchAPI('/projects/', {
    method: 'POST',
    body: JSON.stringify(project),
  });
}

export async function updateProject(id: string, updates: Partial<Project>): Promise<Project> {
  return fetchAPI(`/projects/${id}`, {
    method: 'PUT',
    body: JSON.stringify(updates),
  });
}

export async function deleteProject(id: string): Promise<void> {
  await fetchAPI(`/projects/${id}`, {
    method: 'DELETE',
  });
}

// Sessions
export async function getSessions(projectId?: string): Promise<Session[]> {
  const endpoint = projectId 
    ? `/sessions/?project_id=${projectId}` 
    : '/sessions/';
  return fetchAPI(endpoint);
}

export async function getSession(sessionId: string): Promise<Session> {
  return fetchAPI(`/sessions/${sessionId}`);
}

export async function createSession(projectId?: string): Promise<Session> {
  return fetchAPI('/sessions/', {
    method: 'POST',
    body: JSON.stringify({ project_id: projectId }),
  });
}

export async function endSession(sessionId: string): Promise<Session> {
  return fetchAPI(`/sessions/${sessionId}/end`, {
    method: 'POST',
  });
}

export async function getSessionMessages(sessionId: string): Promise<SessionMessage[]> {
  return fetchAPI(`/sessions/${sessionId}/messages`);
}

export async function addMessageToSession(
  sessionId: string,
  role: string,
  content: string
): Promise<SessionMessage> {
  return fetchAPI(`/sessions/${sessionId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ role, content }),
  });
}

// Reflections
export async function getSessionReflection(sessionId: string): Promise<Reflection> {
  return fetchAPI(`/sessions/${sessionId}/reflection`);
}

export async function generateReflection(sessionId: string): Promise<Reflection> {
  return fetchAPI(`/sessions/${sessionId}/reflection/generate`, {
    method: 'POST',
  });
}

// Memory
export async function searchMemory(query: string, limit: number = 5) {
  return fetchAPI(`/memory/search?query=${encodeURIComponent(query)}&n_results=${limit}`);
}

export async function storeMemory(content: string, metadata: Record<string, any> = {}) {
  return fetchAPI('/memory/store', {
    method: 'POST',
    body: JSON.stringify({ content, metadata }),
  });
}

// Pedagogy
export async function detectSessionType(messages: Message[]): Promise<{ session_type: string; confidence: number }> {
  return fetchAPI('/pedagogy/detect-session-type', {
    method: 'POST',
    body: JSON.stringify({ messages }),
  });
}

export async function generateLearningPlan(
  topic: string,
  currentLevel: string,
  goals: string[]
): Promise<{ plan: string }> {
  return fetchAPI('/pedagogy/learning-plan', {
    method: 'POST',
    body: JSON.stringify({
      topic,
      current_level: currentLevel,
      goals,
    }),
  });
}
