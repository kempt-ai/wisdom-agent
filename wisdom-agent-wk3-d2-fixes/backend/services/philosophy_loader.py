"""
Philosophy Loader - Layered Philosophy System

Loads and combines philosophy files in a layered system:
- BASE: Something Deeperism core (always loaded)
- DOMAIN: democracy/, corporate/, education/ (optional)
- ORGANIZATION: org-specific values (optional)  
- PROJECT: project-specific principles (optional)

Each layer stacks on top of the previous, creating a customized
philosophy context for different use cases.
"""

from pathlib import Path
from typing import Optional
from backend.config import config


class PhilosophyLoader:
    """
    Manages layered philosophy loading for the Wisdom Agent.
    
    Philosophy files are plain text and are concatenated in layer order
    to create the final system prompt context.
    """
    
    # Core philosophy files (always loaded from base)
    CORE_FILES = ["core.txt", "rubric.txt"]
    
    # Supplementary files (loaded on demand)
    SUPPLEMENTARY_FILES = {
        "limits": "Limits.txt",
        "pure_love": "PL&SD.txt",
        "shared": "SharedSD.txt",
        "wisdom_meme": "WM&AI.txt",
    }
    
    def __init__(self):
        """Initialize the philosophy loader."""
        self._cache: dict[str, str] = {}
        
    def _read_file(self, path: Path) -> str:
        """
        Read a philosophy file with caching.
        
        Args:
            path: Path to the philosophy file
            
        Returns:
            File contents as string, or empty string if not found
        """
        cache_key = str(path)
        
        if cache_key not in self._cache:
            try:
                self._cache[cache_key] = path.read_text(encoding="utf-8")
            except FileNotFoundError:
                self._cache[cache_key] = ""
                
        return self._cache[cache_key]
    
    def clear_cache(self):
        """Clear the file cache (useful after philosophy updates)."""
        self._cache.clear()
    
    def load_base(self, include_supplementary: bool = False) -> str:
        """
        Load the base Something Deeperism philosophy.
        
        Args:
            include_supplementary: If True, load all supplementary files too
            
        Returns:
            Combined philosophy text
        """
        parts = []
        
        # Always load core files
        for filename in self.CORE_FILES:
            filepath = config.PHILOSOPHY_BASE / filename
            content = self._read_file(filepath)
            if content:
                parts.append(f"=== {filename.upper()} ===\n{content}")
        
        # Optionally load supplementary files
        if include_supplementary:
            for key, filename in self.SUPPLEMENTARY_FILES.items():
                filepath = config.PHILOSOPHY_BASE / filename
                content = self._read_file(filepath)
                if content:
                    parts.append(f"=== {filename.upper()} ===\n{content}")
        
        return "\n\n".join(parts)
    
    def load_supplementary(self, key: str) -> str:
        """
        Load a specific supplementary philosophy file.
        
        Args:
            key: One of 'limits', 'pure_love', 'shared', 'wisdom_meme'
            
        Returns:
            File contents or empty string
        """
        if key not in self.SUPPLEMENTARY_FILES:
            return ""
            
        filepath = config.PHILOSOPHY_BASE / self.SUPPLEMENTARY_FILES[key]
        return self._read_file(filepath)
    
    def load_domain(self, domain: str) -> str:
        """
        Load domain-specific philosophy overlay.
        
        Args:
            domain: Domain name (e.g., 'democracy', 'corporate', 'education')
            
        Returns:
            Domain philosophy text or empty string
        """
        domain_path = config.PHILOSOPHY_DOMAINS / domain
        
        if not domain_path.exists() or not domain_path.is_dir():
            return ""
        
        parts = []
        for filepath in sorted(domain_path.glob("*.txt")):
            content = self._read_file(filepath)
            if content:
                parts.append(f"=== {filepath.name.upper()} ===\n{content}")
        
        return "\n\n".join(parts)
    
    def load_organization(self, org_name: str) -> str:
        """
        Load organization-specific philosophy overlay.
        
        Args:
            org_name: Organization name/ID
            
        Returns:
            Organization philosophy text or empty string
        """
        org_path = config.PHILOSOPHY_ORGS / org_name
        
        if not org_path.exists() or not org_path.is_dir():
            return ""
        
        parts = []
        for filepath in sorted(org_path.glob("*.txt")):
            content = self._read_file(filepath)
            if content:
                parts.append(f"=== {filepath.name.upper()} ===\n{content}")
        
        return "\n\n".join(parts)
    
    def load_project(self, project_path: Path) -> str:
        """
        Load project-specific philosophy principles.
        
        Args:
            project_path: Path to project directory
            
        Returns:
            Project philosophy text or empty string
        """
        philosophy_file = project_path / "philosophy.txt"
        
        if not philosophy_file.exists():
            return ""
            
        return self._read_file(philosophy_file)
    
    def build_context(
        self,
        include_supplementary: bool = False,
        domain: Optional[str] = None,
        organization: Optional[str] = None,
        project_path: Optional[Path] = None,
    ) -> str:
        """
        Build complete philosophy context by stacking layers.
        
        Layers are applied in order:
        1. BASE (Something Deeperism) - always
        2. DOMAIN (democracy, corporate, etc.) - if specified
        3. ORGANIZATION (org values) - if specified
        4. PROJECT (project principles) - if specified
        
        Args:
            include_supplementary: Include all supplementary base files
            domain: Domain overlay to apply
            organization: Organization overlay to apply
            project_path: Project directory for project-specific philosophy
            
        Returns:
            Complete philosophy context string
        """
        layers = []
        
        # Layer 1: Base (always)
        base = self.load_base(include_supplementary=include_supplementary)
        if base:
            layers.append("### BASE PHILOSOPHY (Something Deeperism) ###\n" + base)
        
        # Layer 2: Domain (optional)
        if domain:
            domain_content = self.load_domain(domain)
            if domain_content:
                layers.append(f"### DOMAIN: {domain.upper()} ###\n" + domain_content)
        
        # Layer 3: Organization (optional)
        if organization:
            org_content = self.load_organization(organization)
            if org_content:
                layers.append(f"### ORGANIZATION: {organization.upper()} ###\n" + org_content)
        
        # Layer 4: Project (optional)
        if project_path:
            project_content = self.load_project(project_path)
            if project_content:
                layers.append("### PROJECT PRINCIPLES ###\n" + project_content)
        
        return "\n\n" + "=" * 60 + "\n\n".join(layers) if layers else ""
    
    def get_available_domains(self) -> list[str]:
        """Get list of available domain overlays."""
        if not config.PHILOSOPHY_DOMAINS.exists():
            return []
        return [d.name for d in config.PHILOSOPHY_DOMAINS.iterdir() if d.is_dir()]
    
    def get_available_organizations(self) -> list[str]:
        """Get list of available organization overlays."""
        if not config.PHILOSOPHY_ORGS.exists():
            return []
        return [d.name for d in config.PHILOSOPHY_ORGS.iterdir() if d.is_dir()]


# Singleton instance
philosophy_loader = PhilosophyLoader()


# Convenience functions
def get_base_philosophy(include_supplementary: bool = False) -> str:
    """Get the base Something Deeperism philosophy."""
    return philosophy_loader.load_base(include_supplementary)


def get_philosophy_context(
    domain: Optional[str] = None,
    organization: Optional[str] = None,
    project_path: Optional[Path] = None,
) -> str:
    """Build complete philosophy context with optional overlays."""
    return philosophy_loader.build_context(
        domain=domain,
        organization=organization,
        project_path=project_path,
    )
