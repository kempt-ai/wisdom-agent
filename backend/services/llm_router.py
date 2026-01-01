"""
LLM Router - Multi-Provider Support with Granular Model Selection

Routes LLM requests to configured providers (Anthropic, OpenAI, Nebius, Gemini, Local).
Allows users to configure and toggle between different LLM providers AND specific models.

Updated: December 26, 2025 - Added granular model selection with cost tracking
"""

import json
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple

from anthropic import Anthropic

# Conditional imports for optional providers
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    import ollama
except ImportError:
    ollama = None

# Google Gemini import
try:
    import google.generativeai as genai
except ImportError:
    genai = None

from backend.config import config


class LLMProvider(Enum):
    """Supported LLM providers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    LOCAL = "local"      # For Ollama or similar
    NEBIUS = "nebius"    # Nebius AI platform
    GEMINI = "gemini"    # Google Gemini


# ============================================================================
# MODEL DEFINITIONS WITH METADATA
# ============================================================================
# Defines all available models per provider with their capabilities and costs

PROVIDER_MODELS = {
    'anthropic': {
        'models': [
            {
                'id': 'claude-3-haiku-20240307',
                'name': 'Claude 3 Haiku',
                'tier': 'economy',
                'description': 'Fast and efficient for simple tasks',
                'input_cost_per_1m': 0.25,
                'output_cost_per_1m': 1.25,
                'context_window': 200000,
                'best_for': ['Quick responses', 'Simple summaries', 'Classification'],
            },
            {
                'id': 'claude-3-5-haiku-20241022',
                'name': 'Claude 3.5 Haiku',
                'tier': 'economy',
                'description': 'Improved Haiku with better reasoning',
                'input_cost_per_1m': 1.00,
                'output_cost_per_1m': 5.00,
                'context_window': 200000,
                'best_for': ['Routine tasks', 'Summaries', 'Basic analysis'],
            },
            {
                'id': 'claude-3-5-sonnet-20241022',
                'name': 'Claude 3.5 Sonnet',
                'tier': 'standard',
                'description': 'Best balance of capability and cost',
                'input_cost_per_1m': 3.00,
                'output_cost_per_1m': 15.00,
                'context_window': 200000,
                'best_for': ['Complex analysis', 'Writing', 'Code generation'],
            },
            {
                'id': 'claude-sonnet-4-20250514',
                'name': 'Claude Sonnet 4',
                'tier': 'standard',
                'description': 'Latest Sonnet with improved capabilities',
                'input_cost_per_1m': 3.00,
                'output_cost_per_1m': 15.00,
                'context_window': 200000,
                'best_for': ['General use', 'Analysis', 'Creative writing'],
            },
            {
                'id': 'claude-3-opus-20240229',
                'name': 'Claude 3 Opus',
                'tier': 'premium',
                'description': 'Most capable, best for complex reasoning',
                'input_cost_per_1m': 15.00,
                'output_cost_per_1m': 75.00,
                'context_window': 200000,
                'best_for': ['Deep analysis', 'Philosophy', 'Nuanced tasks'],
            },
        ],
        'default': 'claude-sonnet-4-20250514',
    },
    'openai': {
        'models': [
            {
                'id': 'gpt-4o-mini',
                'name': 'GPT-4o Mini',
                'tier': 'economy',
                'description': 'Affordable GPT-4 class model',
                'input_cost_per_1m': 0.15,
                'output_cost_per_1m': 0.60,
                'context_window': 128000,
                'best_for': ['Quick tasks', 'Simple queries'],
            },
            {
                'id': 'gpt-4o',
                'name': 'GPT-4o',
                'tier': 'standard',
                'description': 'Powerful multimodal model',
                'input_cost_per_1m': 2.50,
                'output_cost_per_1m': 10.00,
                'context_window': 128000,
                'best_for': ['Complex reasoning', 'Vision tasks', 'Code'],
            },
            {
                'id': 'gpt-4-turbo',
                'name': 'GPT-4 Turbo',
                'tier': 'standard',
                'description': 'Previous generation flagship',
                'input_cost_per_1m': 10.00,
                'output_cost_per_1m': 30.00,
                'context_window': 128000,
                'best_for': ['Complex tasks', 'Long context'],
            },
            {
                'id': 'o1-preview',
                'name': 'o1 Preview',
                'tier': 'premium',
                'description': 'Advanced reasoning model',
                'input_cost_per_1m': 15.00,
                'output_cost_per_1m': 60.00,
                'context_window': 128000,
                'best_for': ['Math', 'Science', 'Complex reasoning'],
            },
        ],
        'default': 'gpt-4o',
    },
    'gemini': {
        'models': [
            {
                'id': 'gemini-1.5-flash',
                'name': 'Gemini 1.5 Flash',
                'tier': 'economy',
                'description': 'Very fast and affordable',
                'input_cost_per_1m': 0.075,
                'output_cost_per_1m': 0.30,
                'context_window': 1000000,
                'best_for': ['Bulk processing', 'Speed-critical', 'Long documents'],
            },
            {
                'id': 'gemini-1.5-flash-8b',
                'name': 'Gemini 1.5 Flash 8B',
                'tier': 'economy',
                'description': 'Smallest and fastest Flash variant',
                'input_cost_per_1m': 0.0375,
                'output_cost_per_1m': 0.15,
                'context_window': 1000000,
                'best_for': ['High volume', 'Simple tasks'],
            },
            {
                'id': 'gemini-1.5-pro',
                'name': 'Gemini 1.5 Pro',
                'tier': 'standard',
                'description': 'Capable with massive context window',
                'input_cost_per_1m': 1.25,
                'output_cost_per_1m': 5.00,
                'context_window': 2000000,
                'best_for': ['Very long documents', 'Multi-turn analysis'],
            },
            {
                'id': 'gemini-2.0-flash-exp',
                'name': 'Gemini 2.0 Flash (Experimental)',
                'tier': 'standard',
                'description': 'Next-gen experimental model',
                'input_cost_per_1m': 0.10,
                'output_cost_per_1m': 0.40,
                'context_window': 1000000,
                'best_for': ['Testing new capabilities'],
            },
        ],
        'default': 'gemini-1.5-flash',
    },
    'nebius': {
        'models': [
            {
                'id': 'meta-llama/Llama-3.3-70B-Instruct',
                'name': 'Llama 3.3 70B',
                'tier': 'standard',
                'description': 'Latest Llama, very capable',
                'input_cost_per_1m': 0.20,
                'output_cost_per_1m': 0.20,
                'context_window': 128000,
                'best_for': ['General tasks', 'Open-source alternative'],
            },
            {
                'id': 'meta-llama/Llama-3.1-70B-Instruct',
                'name': 'Llama 3.1 70B',
                'tier': 'standard',
                'description': 'Reliable Llama model',
                'input_cost_per_1m': 0.20,
                'output_cost_per_1m': 0.20,
                'context_window': 128000,
                'best_for': ['General tasks'],
            },
            {
                'id': 'meta-llama/Llama-3.1-8B-Instruct',
                'name': 'Llama 3.1 8B',
                'tier': 'economy',
                'description': 'Smaller, faster Llama',
                'input_cost_per_1m': 0.05,
                'output_cost_per_1m': 0.05,
                'context_window': 128000,
                'best_for': ['Simple tasks', 'High volume'],
            },
            {
                'id': 'Qwen/Qwen2.5-72B-Instruct',
                'name': 'Qwen 2.5 72B',
                'tier': 'standard',
                'description': 'Strong multilingual model',
                'input_cost_per_1m': 0.20,
                'output_cost_per_1m': 0.20,
                'context_window': 128000,
                'best_for': ['Multilingual', 'Chinese language'],
            },
            {
                'id': 'deepseek-ai/DeepSeek-V3',
                'name': 'DeepSeek V3',
                'tier': 'standard',
                'description': 'Capable reasoning model',
                'input_cost_per_1m': 0.14,
                'output_cost_per_1m': 0.28,
                'context_window': 64000,
                'best_for': ['Reasoning', 'Code'],
            },
            {
                'id': 'deepseek-ai/DeepSeek-R1',
                'name': 'DeepSeek R1',
                'tier': 'standard',
                'description': 'Advanced reasoning model',
                'input_cost_per_1m': 0.55,
                'output_cost_per_1m': 2.19,
                'context_window': 64000,
                'best_for': ['Complex reasoning', 'Math'],
            },
            {
                'id': 'mistralai/Mixtral-8x7B-Instruct-v0.1',
                'name': 'Mixtral 8x7B',
                'tier': 'economy',
                'description': 'Efficient mixture-of-experts',
                'input_cost_per_1m': 0.10,
                'output_cost_per_1m': 0.10,
                'context_window': 32000,
                'best_for': ['Efficient inference', 'General tasks'],
            },
        ],
        'default': 'meta-llama/Llama-3.3-70B-Instruct',
    },
    'local': {
        'models': [
            {
                'id': 'mistral',
                'name': 'Mistral 7B (Local)',
                'tier': 'free',
                'description': 'Local model - no API cost',
                'input_cost_per_1m': 0.0,
                'output_cost_per_1m': 0.0,
                'context_window': 32000,
                'best_for': ['Privacy', 'Offline use', 'Unlimited testing'],
            },
            {
                'id': 'llama3.2',
                'name': 'Llama 3.2 (Local)',
                'tier': 'free',
                'description': 'Local Llama - no API cost',
                'input_cost_per_1m': 0.0,
                'output_cost_per_1m': 0.0,
                'context_window': 128000,
                'best_for': ['Privacy', 'Offline use'],
            },
            {
                'id': 'phi3',
                'name': 'Phi-3 (Local)',
                'tier': 'free',
                'description': 'Microsoft small model',
                'input_cost_per_1m': 0.0,
                'output_cost_per_1m': 0.0,
                'context_window': 4000,
                'best_for': ['Fast local inference'],
            },
        ],
        'default': 'mistral',
    },
}


class LLMRouter:
    """Routes requests to configured LLM provider with model selection."""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize LLM Router.
        
        Args:
            config_file: Path to LLM provider configuration (optional, uses default)
        """
        self.config_file = config_file or str(config.LLM_CONFIG_FILE)
        self.provider_config = self._load_config()
        self.active_provider = self.provider_config.get('active_provider', 'anthropic')
        self.clients: Dict[str, Any] = {}
        self._initialize_clients()
    
    def _load_config(self) -> Dict:
        """Load LLM provider configuration."""
        if config.LLM_CONFIG_FILE.exists():
            with open(config.LLM_CONFIG_FILE, 'r') as f:
                loaded = json.load(f)
                # Merge with PROVIDER_MODELS to ensure we have latest model lists
                self._merge_model_definitions(loaded)
                return loaded
        
        # Default configuration with model lists from PROVIDER_MODELS
        return self._create_default_config()
    
    def _create_default_config(self) -> Dict:
        """Create default configuration with all model definitions."""
        return {
            'active_provider': 'anthropic',
            'providers': {
                'anthropic': {
                    'enabled': True,
                    'api_key_env': 'ANTHROPIC_API_KEY',
                    'default_model': PROVIDER_MODELS['anthropic']['default'],
                    'available_models': [m['id'] for m in PROVIDER_MODELS['anthropic']['models']],
                    'max_tokens': config.DEFAULT_MAX_TOKENS
                },
                'openai': {
                    'enabled': False,
                    'api_key_env': 'OPENAI_API_KEY',
                    'default_model': PROVIDER_MODELS['openai']['default'],
                    'available_models': [m['id'] for m in PROVIDER_MODELS['openai']['models']],
                    'max_tokens': config.DEFAULT_MAX_TOKENS
                },
                'local': {
                    'enabled': False,
                    'base_url': 'http://localhost:11434',
                    'default_model': PROVIDER_MODELS['local']['default'],
                    'available_models': [m['id'] for m in PROVIDER_MODELS['local']['models']],
                    'max_tokens': config.DEFAULT_MAX_TOKENS
                },
                'nebius': {
                    'enabled': False,
                    'api_key_env': 'NEBIUS_API_KEY',
                    'base_url': config.NEBIUS_BASE_URL,
                    'default_model': PROVIDER_MODELS['nebius']['default'],
                    'available_models': [m['id'] for m in PROVIDER_MODELS['nebius']['models']],
                    'max_tokens': config.DEFAULT_MAX_TOKENS,
                },
                'gemini': {
                    'enabled': False,
                    'api_key_env': 'GOOGLE_API_KEY',
                    'default_model': PROVIDER_MODELS['gemini']['default'],
                    'available_models': [m['id'] for m in PROVIDER_MODELS['gemini']['models']],
                    'max_tokens': config.DEFAULT_MAX_TOKENS,
                }
            }
        }
    
    def _merge_model_definitions(self, loaded_config: Dict):
        """Ensure loaded config has all current model definitions."""
        for provider, provider_data in PROVIDER_MODELS.items():
            if provider in loaded_config.get('providers', {}):
                # Update available_models list
                loaded_config['providers'][provider]['available_models'] = [
                    m['id'] for m in provider_data['models']
                ]
    
    def _initialize_clients(self):
        """Initialize API clients for enabled providers."""
        providers = self.provider_config.get('providers', {})
        
        # Anthropic - auto-enable if key present
        anthropic_settings = providers.get('anthropic', {})
        if config.ANTHROPIC_API_KEY:
            if not anthropic_settings.get('enabled'):
                anthropic_settings['enabled'] = True
                self.provider_config['providers']['anthropic'] = anthropic_settings
            self.clients['anthropic'] = Anthropic(api_key=config.ANTHROPIC_API_KEY)
            print("✓ Anthropic client initialized")
        
        # OpenAI - auto-enable if key present
        openai_settings = providers.get('openai', {})
        if config.OPENAI_API_KEY and OpenAI is not None:
            if not openai_settings.get('enabled'):
                openai_settings['enabled'] = True
                self.provider_config['providers']['openai'] = openai_settings
            self.clients['openai'] = OpenAI(api_key=config.OPENAI_API_KEY)
            print("✓ OpenAI client initialized")
        
        # Local (Ollama) - only if explicitly enabled
        if providers.get('local', {}).get('enabled'):
            if ollama is not None:
                self.clients['local'] = ollama
                print("✓ Ollama client initialized")
            else:
                print("⚠ Ollama library not installed")
        
        # Nebius - auto-enable if key present
        nebius_settings = providers.get('nebius', {})
        if config.NEBIUS_API_KEY and OpenAI is not None:
            if not nebius_settings.get('enabled'):
                nebius_settings['enabled'] = True
                self.provider_config['providers']['nebius'] = nebius_settings
            
            base_url = config.NEBIUS_BASE_URL
            self.clients['nebius'] = OpenAI(
                base_url=base_url,
                api_key=config.NEBIUS_API_KEY
            )
            print(f"✓ Nebius client initialized: {base_url}")
        
        # Google Gemini - auto-enable if key present
        gemini_settings = providers.get('gemini', {})
        google_api_key = getattr(config, 'GOOGLE_API_KEY', None)
        if google_api_key and genai is not None:
            if not gemini_settings.get('enabled'):
                gemini_settings['enabled'] = True
                self.provider_config['providers']['gemini'] = gemini_settings
            
            genai.configure(api_key=google_api_key)
            self.clients['gemini'] = genai
            print("✓ Google Gemini client initialized")
        elif genai is None and google_api_key:
            print("⚠ Google Generative AI library not installed")
    
    # ========================================================================
    # PROVIDER & MODEL MANAGEMENT
    # ========================================================================
    
    def get_available_providers(self) -> List[str]:
        """Get list of available (configured and enabled) providers."""
        return list(self.clients.keys())
    
    def set_active_provider(self, provider: str):
        """Set the active LLM provider."""
        if provider not in self.clients:
            available = self.get_available_providers()
            raise ValueError(f"Provider '{provider}' not available. Available: {available}")
        
        self.active_provider = provider
        self.provider_config['active_provider'] = provider
        self._save_config()
    
    def get_models(self, provider: Optional[str] = None) -> List[Dict]:
        """
        Get available models for a provider with full metadata.
        
        Args:
            provider: Provider name (default: active provider)
            
        Returns:
            List of model dicts with id, name, tier, costs, etc.
        """
        provider = provider or self.active_provider
        
        if provider not in PROVIDER_MODELS:
            return []
        
        return PROVIDER_MODELS[provider]['models']
    
    def get_model_info(self, model_id: str, provider: Optional[str] = None) -> Optional[Dict]:
        """
        Get detailed information about a specific model.
        
        Args:
            model_id: The model identifier
            provider: Provider name (will search all if not specified)
            
        Returns:
            Model info dict or None if not found
        """
        providers_to_search = [provider] if provider else PROVIDER_MODELS.keys()
        
        for p in providers_to_search:
            if p not in PROVIDER_MODELS:
                continue
            for model in PROVIDER_MODELS[p]['models']:
                if model['id'] == model_id:
                    return {**model, 'provider': p}
        
        return None
    
    def get_current_model(self, provider: Optional[str] = None) -> Dict:
        """
        Get the currently selected model for a provider.
        
        Args:
            provider: Provider name (default: active provider)
            
        Returns:
            Dict with model id and full info
        """
        provider = provider or self.active_provider
        
        if provider not in self.provider_config['providers']:
            raise ValueError(f"Provider '{provider}' not configured")
        
        model_id = self.provider_config['providers'][provider]['default_model']
        model_info = self.get_model_info(model_id, provider)
        
        return {
            'provider': provider,
            'model_id': model_id,
            'info': model_info
        }
    
    def set_model(self, model_id: str, provider: Optional[str] = None):
        """
        Set the active model for a provider.
        
        Args:
            model_id: Model identifier to use
            provider: Provider name (default: active provider)
        """
        provider = provider or self.active_provider
        
        if provider not in self.provider_config['providers']:
            raise ValueError(f"Provider '{provider}' not configured")
        
        # Verify model exists
        available = self.provider_config['providers'][provider].get('available_models', [])
        if available and model_id not in available:
            print(f"⚠ Warning: {model_id} not in known model list for {provider}")
        
        self.provider_config['providers'][provider]['default_model'] = model_id
        self._save_config()
        print(f"✓ {provider} model set to: {model_id}")
    
    def get_all_providers_status(self) -> List[Dict]:
        """
        Get status of all providers with their current models.
        
        Returns:
            List of provider status dicts
        """
        result = []
        for provider, settings in self.provider_config['providers'].items():
            model_id = settings.get('default_model', 'unknown')
            model_info = self.get_model_info(model_id, provider)
            
            result.append({
                'provider': provider,
                'enabled': settings.get('enabled', False),
                'available': provider in self.clients,
                'is_active': provider == self.active_provider,
                'current_model': model_id,
                'model_info': model_info,
                'available_models': self.get_models(provider),
            })
        
        return result
    
    # ========================================================================
    # COMPLETION WITH MODEL OVERRIDE
    # ========================================================================
    
    def complete(
        self,
        messages: List[Dict],
        system_prompt: str = "",
        max_tokens: Optional[int] = None,
        temperature: float = 1.0,
        provider: Optional[str] = None,
        model: Optional[str] = None  # NEW: Allow model override
    ) -> str:
        """
        Generate completion using active or specified provider/model.
        
        Args:
            messages: List of message dictionaries
            system_prompt: System prompt (if applicable)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            provider: Override active provider for this request
            model: Override default model for this request (NEW)
            
        Returns:
            Generated text response
        """
        provider = provider or self.active_provider
        
        if provider not in self.clients:
            raise ValueError(f"Provider '{provider}' not available")
        
        provider_settings = self.provider_config['providers'][provider]
        max_tokens = max_tokens or provider_settings['max_tokens']
        
        # Use specified model or fall back to provider default
        model = model or provider_settings['default_model']
        
        # Route to appropriate provider
        if provider == 'anthropic':
            return self._complete_anthropic(messages, system_prompt, max_tokens, temperature, model)
        elif provider == 'openai':
            return self._complete_openai(messages, system_prompt, max_tokens, temperature, model)
        elif provider == 'local':
            return self._complete_local(messages, system_prompt, max_tokens, temperature, model)
        elif provider == 'nebius':
            return self._complete_nebius(messages, system_prompt, max_tokens, temperature, model)
        elif provider == 'gemini':
            return self._complete_gemini(messages, system_prompt, max_tokens, temperature, model)
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def complete_with_cost(
        self,
        messages: List[Dict],
        system_prompt: str = "",
        max_tokens: Optional[int] = None,
        temperature: float = 1.0,
        provider: Optional[str] = None,
        model: Optional[str] = None
    ) -> Tuple[str, Dict]:
        """
        Generate completion and return estimated cost info.
        
        Returns:
            Tuple of (response_text, cost_info_dict)
        """
        provider = provider or self.active_provider
        model = model or self.provider_config['providers'][provider]['default_model']
        
        # Get model info for cost calculation
        model_info = self.get_model_info(model, provider)
        
        # Estimate input tokens (rough: 4 chars per token)
        input_text = system_prompt + " ".join(m.get('content', '') for m in messages)
        estimated_input_tokens = len(input_text) // 4
        
        # Complete the request
        response = self.complete(
            messages=messages,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            provider=provider,
            model=model
        )
        
        # Estimate output tokens
        estimated_output_tokens = len(response) // 4
        
        # Calculate cost
        if model_info:
            input_cost = (estimated_input_tokens / 1_000_000) * model_info.get('input_cost_per_1m', 0)
            output_cost = (estimated_output_tokens / 1_000_000) * model_info.get('output_cost_per_1m', 0)
            total_cost = input_cost + output_cost
        else:
            input_cost = output_cost = total_cost = 0
        
        cost_info = {
            'provider': provider,
            'model': model,
            'model_name': model_info.get('name', model) if model_info else model,
            'tier': model_info.get('tier', 'unknown') if model_info else 'unknown',
            'estimated_input_tokens': estimated_input_tokens,
            'estimated_output_tokens': estimated_output_tokens,
            'estimated_total_tokens': estimated_input_tokens + estimated_output_tokens,
            'estimated_cost': round(total_cost, 6),
        }
        
        return response, cost_info
    
    # ========================================================================
    # PROVIDER-SPECIFIC COMPLETION METHODS
    # ========================================================================
    
    def _complete_anthropic(self, messages, system_prompt, max_tokens, temperature, model) -> str:
        """Complete using Anthropic API."""
        response = self.clients['anthropic'].messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=messages
        )
        return response.content[0].text
    
    def _complete_openai(self, messages, system_prompt, max_tokens, temperature, model) -> str:
        """Complete using OpenAI API."""
        openai_messages = []
        if system_prompt:
            openai_messages.append({"role": "system", "content": system_prompt})
        openai_messages.extend(messages)
        
        response = self.clients['openai'].chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=openai_messages
        )
        return response.choices[0].message.content
    
    def _complete_local(self, messages, system_prompt, max_tokens, temperature, model) -> str:
        """Complete using local model (Ollama)."""
        ollama_messages = []
        if system_prompt:
            ollama_messages.append({"role": "system", "content": system_prompt})
        ollama_messages.extend(messages)
        
        response = self.clients['local'].chat(
            model=model,
            messages=ollama_messages,
            options={
                'temperature': temperature,
                'num_predict': max_tokens
            }
        )
        return response['message']['content']
    
    def _complete_nebius(self, messages, system_prompt, max_tokens, temperature, model) -> str:
        """Complete using Nebius AI platform."""
        client = self.clients['nebius']
        
        nebius_messages = []
        if system_prompt:
            nebius_messages.append({"role": "system", "content": system_prompt})
        nebius_messages.extend(messages)
        
        try:
            response = client.chat.completions.create(
                model=model,
                messages=nebius_messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            error_msg = str(e)
            if "does not exist" in error_msg or "404" in error_msg:
                available = self.get_models('nebius')
                model_ids = [m['id'] for m in available[:5]]
                raise Exception(
                    f"Nebius model '{model}' not found. "
                    f"Try one of: {', '.join(model_ids)}..."
                )
            raise Exception(f"Nebius API error: {e}")
    
    def _complete_gemini(self, messages, system_prompt, max_tokens, temperature, model) -> str:
        """Complete using Google Gemini API."""
        genai_client = self.clients['gemini']
        
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        
        if system_prompt:
            gemini_model = genai_client.GenerativeModel(
                model_name=model,
                generation_config=generation_config,
                system_instruction=system_prompt
            )
        else:
            gemini_model = genai_client.GenerativeModel(
                model_name=model,
                generation_config=generation_config
            )
        
        # Convert messages to Gemini format
        gemini_history = []
        for msg in messages[:-1]:
            role = 'model' if msg['role'] == 'assistant' else 'user'
            gemini_history.append({
                'role': role,
                'parts': [msg['content']]
            })
        
        chat = gemini_model.start_chat(history=gemini_history)
        last_message = messages[-1]['content'] if messages else ""
        response = chat.send_message(last_message)
        
        return response.text
    
    # ========================================================================
    # CONFIGURATION & UTILITY
    # ========================================================================
    
    def _save_config(self):
        """Save configuration to file."""
        config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(self.provider_config, f, indent=2)
    
    def get_provider_info(self, provider: Optional[str] = None) -> Dict:
        """Get information about active or specified provider."""
        provider = provider or self.active_provider
        
        if provider not in self.provider_config['providers']:
            return {}
        
        settings = self.provider_config['providers'][provider]
        model_info = self.get_model_info(settings['default_model'], provider)
        
        return {
            'name': provider,
            'model': settings['default_model'],
            'model_info': model_info,
            'enabled': settings['enabled'],
            'available': provider in self.clients,
            'max_tokens': settings['max_tokens'],
            'available_models': self.get_models(provider),
        }
    
    def configure_provider(
        self,
        provider: str,
        enabled: bool = True,
        model: Optional[str] = None,
        **kwargs
    ):
        """Configure or reconfigure a provider."""
        if provider not in self.provider_config['providers']:
            self.provider_config['providers'][provider] = {}
        
        settings = self.provider_config['providers'][provider]
        settings['enabled'] = enabled
        
        if model:
            settings['default_model'] = model
        
        settings.update(kwargs)
        self._save_config()
        
        if enabled:
            self._initialize_clients()
    
    # Legacy methods for backward compatibility
    def get_nebius_models(self, refresh: bool = False) -> List[str]:
        """Get list of available models on Nebius."""
        models = self.get_models('nebius')
        return [m['id'] for m in models]
    
    def set_nebius_model(self, model_name: str):
        """Set the active model for Nebius."""
        self.set_model(model_name, 'nebius')
    
    def get_gemini_models(self) -> List[str]:
        """Get list of available Gemini models."""
        models = self.get_models('gemini')
        return [m['id'] for m in models]
    
    def set_gemini_model(self, model_name: str):
        """Set the active model for Gemini."""
        self.set_model(model_name, 'gemini')


# ============================================================================
# MODULE-LEVEL FUNCTIONS
# ============================================================================

def initialize_llm_router(config_file: Optional[str] = None) -> Optional[LLMRouter]:
    """Initialize and return an LLM Router instance."""
    try:
        router = LLMRouter(config_file)
        return router
    except Exception as e:
        print(f"⚠ Could not initialize LLM Router: {e}")
        return None


# Singleton instance
_router_instance: Optional[LLMRouter] = None


def get_llm_router() -> LLMRouter:
    """Get or create the singleton LLM Router instance."""
    global _router_instance
    if _router_instance is None:
        _router_instance = LLMRouter()
    return _router_instance
