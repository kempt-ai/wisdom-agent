"""
LLM Router - Multi-Provider Support

Routes LLM requests to configured providers (Anthropic, OpenAI, Nebius, Local).
Allows users to configure and toggle between different LLM providers.

Migrated from old wisdom-agent to use new config system.
"""

import json
from enum import Enum
from typing import Dict, List, Optional, Any

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

from backend.config import config


class LLMProvider(Enum):
    """Supported LLM providers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    LOCAL = "local"      # For Ollama or similar
    NEBIUS = "nebius"    # Nebius AI platform


class LLMRouter:
    """Routes requests to configured LLM provider."""
    
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
                return json.load(f)
        
        # Default configuration
        return {
            'active_provider': 'anthropic',
            'providers': {
                'anthropic': {
                    'enabled': True,
                    'api_key_env': 'ANTHROPIC_API_KEY',
                    'default_model': 'claude-sonnet-4-20250514',
                    'max_tokens': config.DEFAULT_MAX_TOKENS
                },
                'openai': {
                    'enabled': False,
                    'api_key_env': 'OPENAI_API_KEY',
                    'default_model': 'gpt-4-turbo-preview',
                    'max_tokens': config.DEFAULT_MAX_TOKENS
                },
                'local': {
                    'enabled': False,
                    'base_url': 'http://localhost:11434',  # Ollama default
                    'default_model': 'mistral',
                    'max_tokens': config.DEFAULT_MAX_TOKENS
                },
                'nebius': {
                    'enabled': False,
                    'api_key_env': 'NEBIUS_API_KEY',
                    'base_url': config.NEBIUS_BASE_URL,
                    'default_model': 'meta-llama/Meta-Llama-3.1-70B-Instruct',
                    'max_tokens': config.DEFAULT_MAX_TOKENS,
                    'available_models': [
                        'meta-llama/Meta-Llama-3.1-70B-Instruct',
                        'meta-llama/Meta-Llama-3.1-8B-Instruct',
                        'mistralai/Mistral-7B-Instruct-v0.3',
                        'mistralai/Mixtral-8x7B-Instruct-v0.1'
                    ]
                }
            }
        }
    
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
            base_url = nebius_settings.get('base_url', config.NEBIUS_BASE_URL)
            self.clients['nebius'] = OpenAI(
                base_url=base_url,
                api_key=config.NEBIUS_API_KEY
            )
            print(f"✓ Nebius client initialized: {base_url}")
            
            # Try to fetch available models
            try:
                models = self.fetch_nebius_models_from_api()
                if models:
                    print(f"✓ Fetched {len(models)} Nebius models")
            except Exception as e:
                print(f"⚠ Could not fetch Nebius models: {e}")
    
    def get_available_providers(self) -> List[str]:
        """Get list of available (configured and enabled) providers."""
        return list(self.clients.keys())
    
    def set_active_provider(self, provider: str):
        """
        Set the active LLM provider.
        
        Args:
            provider: Provider name (anthropic, openai, local, nebius)
        """
        if provider not in self.clients:
            available = self.get_available_providers()
            raise ValueError(f"Provider '{provider}' not available. Available: {available}")
        
        self.active_provider = provider
        self.provider_config['active_provider'] = provider
        self._save_config()
    
    def _save_config(self):
        """Save configuration to file."""
        config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(self.provider_config, f, indent=2)
    
    def complete(
        self,
        messages: List[Dict],
        system_prompt: str = "",
        max_tokens: Optional[int] = None,
        temperature: float = 1.0,
        provider: Optional[str] = None
    ) -> str:
        """
        Generate completion using active or specified provider.
        
        Args:
            messages: List of message dictionaries [{"role": "user", "content": "..."}]
            system_prompt: System prompt (if applicable)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            provider: Override active provider for this request
            
        Returns:
            Generated text response
        """
        provider = provider or self.active_provider
        
        if provider not in self.clients:
            raise ValueError(f"Provider '{provider}' not available")
        
        provider_settings = self.provider_config['providers'][provider]
        max_tokens = max_tokens or provider_settings['max_tokens']
        model = provider_settings['default_model']
        
        # Route to appropriate provider
        if provider == 'anthropic':
            return self._complete_anthropic(messages, system_prompt, max_tokens, temperature, model)
        elif provider == 'openai':
            return self._complete_openai(messages, system_prompt, max_tokens, temperature, model)
        elif provider == 'local':
            return self._complete_local(messages, system_prompt, max_tokens, temperature, model)
        elif provider == 'nebius':
            return self._complete_nebius(messages, system_prompt, max_tokens, temperature, model)
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
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
        """Complete using Nebius AI platform (OpenAI-compatible API)."""
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
            raise Exception(f"Nebius API error: {e}")
    
    def get_provider_info(self, provider: Optional[str] = None) -> Dict:
        """
        Get information about active or specified provider.
        
        Args:
            provider: Provider to get info for (default: active)
            
        Returns:
            Dictionary with provider information
        """
        provider = provider or self.active_provider
        
        if provider not in self.provider_config['providers']:
            return {}
        
        settings = self.provider_config['providers'][provider]
        return {
            'name': provider,
            'model': settings['default_model'],
            'enabled': settings['enabled'],
            'available': provider in self.clients,
            'max_tokens': settings['max_tokens']
        }
    
    def configure_provider(
        self,
        provider: str,
        enabled: bool = True,
        model: Optional[str] = None,
        **kwargs
    ):
        """
        Configure or reconfigure a provider.
        
        Args:
            provider: Provider name
            enabled: Enable/disable provider
            model: Default model to use
            **kwargs: Additional provider-specific settings
        """
        if provider not in self.provider_config['providers']:
            self.provider_config['providers'][provider] = {}
        
        settings = self.provider_config['providers'][provider]
        settings['enabled'] = enabled
        
        if model:
            settings['default_model'] = model
        
        settings.update(kwargs)
        self._save_config()
        
        # Reinitialize if enabling
        if enabled:
            self._initialize_clients()
    
    # === Nebius-specific methods ===
    
    def fetch_nebius_models_from_api(self) -> List[str]:
        """Fetch available models from Nebius API."""
        if 'nebius' not in self.clients:
            return []
        
        try:
            client = self.clients['nebius']
            models_response = client.models.list()
            model_ids = [model.id for model in models_response.data]
            
            # Update config with fetched models
            if 'nebius' in self.provider_config['providers']:
                self.provider_config['providers']['nebius']['available_models'] = model_ids
                self._save_config()
            
            return model_ids
        except Exception as e:
            print(f"⚠ Could not fetch Nebius models: {e}")
            return self.provider_config['providers'].get('nebius', {}).get('available_models', [])
    
    def get_nebius_models(self, refresh: bool = False) -> List[str]:
        """Get list of available models on Nebius."""
        if 'nebius' not in self.provider_config['providers']:
            return []
        
        cached_models = self.provider_config['providers']['nebius'].get('available_models', [])
        if refresh or not cached_models:
            return self.fetch_nebius_models_from_api()
        
        return cached_models
    
    def set_nebius_model(self, model_name: str):
        """Set the active model for Nebius."""
        if 'nebius' not in self.provider_config['providers']:
            raise ValueError("Nebius provider not configured")
        
        available = self.get_nebius_models()
        if available and model_name not in available:
            print(f"⚠ {model_name} not in configured model list")
            print(f"Available: {', '.join(available)}")
        
        self.provider_config['providers']['nebius']['default_model'] = model_name
        self._save_config()
        print(f"✓ Nebius model set to: {model_name}")


def initialize_llm_router(config_file: Optional[str] = None) -> Optional[LLMRouter]:
    """
    Initialize and return an LLM Router instance.
    
    Returns None if initialization fails.
    """
    try:
        router = LLMRouter(config_file)
        return router
    except Exception as e:
        print(f"⚠ Could not initialize LLM Router: {e}")
        return None


# Singleton instance (created on first import)
_router_instance: Optional[LLMRouter] = None


def get_llm_router() -> LLMRouter:
    """Get or create the singleton LLM Router instance."""
    global _router_instance
    if _router_instance is None:
        _router_instance = LLMRouter()
    return _router_instance
