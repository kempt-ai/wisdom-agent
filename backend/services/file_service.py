"""
Wisdom Agent - File Service

Document upload, processing, text extraction, and export functionality.

MIGRATION NOTES:
- Ported from file_manager.py
- Uses Config paths for all directories
- Same interface preserved for compatibility
- Works with ProjectService for project-aware file storage
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, BinaryIO, Union
import mimetypes

from backend.config import config

# Optional imports for document processing
try:
    import PyPDF2
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

try:
    from docx import Document as DocxDocument
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


class FileService:
    """Manages file upload, download, and document processing."""
    
    # Supported file types by category
    SUPPORTED_TYPES = {
        'text': ['.txt', '.md', '.csv', '.json'],
        'document': ['.pdf', '.docx', '.doc'],
        'audio': ['.mp3', '.wav', '.m4a', '.ogg'],
        'image': ['.jpg', '.jpeg', '.png', '.gif', '.webp'],
        'data': ['.xlsx', '.xls', '.csv']
    }
    
    # Maximum file sizes (in bytes)
    MAX_SIZES = {
        'text': 10 * 1024 * 1024,      # 10 MB
        'document': 25 * 1024 * 1024,  # 25 MB
        'audio': 50 * 1024 * 1024,     # 50 MB
        'image': 10 * 1024 * 1024,     # 10 MB
        'data': 25 * 1024 * 1024       # 25 MB
    }
    
    def __init__(self, 
                 upload_dir: Optional[Path] = None,
                 export_dir: Optional[Path] = None,
                 projects_dir: Optional[Path] = None):
        """
        Initialize File Service.
        
        Args:
            upload_dir: Directory for uploads (uses config default)
            export_dir: Directory for exports (uses config default)
            projects_dir: Directory for projects (uses config default)
        """
        self.upload_dir = upload_dir or config.UPLOADS_DIR
        self.export_dir = export_dir or config.EXPORTS_DIR
        self.projects_dir = projects_dir or config.PROJECTS_DIR
        
        # Ensure directories exist
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.export_dir.mkdir(parents=True, exist_ok=True)
    
    # ========== FILE CATEGORIZATION ==========
    
    def get_file_category(self, filename: str) -> Optional[str]:
        """
        Determine file category from extension.
        
        Args:
            filename: Name of the file
            
        Returns:
            Category string or None if unsupported
        """
        ext = Path(filename).suffix.lower()
        
        for category, extensions in self.SUPPORTED_TYPES.items():
            if ext in extensions:
                return category
        
        return None
    
    def get_supported_extensions(self) -> List[str]:
        """Get all supported file extensions."""
        extensions = []
        for exts in self.SUPPORTED_TYPES.values():
            extensions.extend(exts)
        return extensions
    
    def validate_file(self, filename: str, file_size: int) -> Tuple[bool, Optional[str]]:
        """
        Validate file type and size.
        
        Args:
            filename: Name of the file
            file_size: Size in bytes
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file type
        category = self.get_file_category(filename)
        if not category:
            ext = Path(filename).suffix.lower()
            return False, f"Unsupported file type: {ext}"
        
        # Check file size
        max_size = self.MAX_SIZES.get(category, 10 * 1024 * 1024)
        if file_size > max_size:
            max_mb = max_size / (1024 * 1024)
            actual_mb = file_size / (1024 * 1024)
            return False, f"File too large: {actual_mb:.1f}MB (max: {max_mb:.1f}MB)"
        
        return True, None
    
    # ========== UPLOAD METHODS ==========
    
    def upload_file(self, 
                   file_data: Union[BinaryIO, bytes],
                   filename: str,
                   project_name: Optional[str] = None,
                   description: Optional[str] = None) -> Dict:
        """
        Upload a file to storage.
        
        Args:
            file_data: File data (BinaryIO or bytes)
            filename: Original filename
            project_name: Optional project to associate with
            description: Optional description
            
        Returns:
            Dictionary with upload result
        """
        # Get file bytes
        if hasattr(file_data, 'getvalue'):
            file_bytes = file_data.getvalue()
        elif hasattr(file_data, 'read'):
            file_bytes = file_data.read()
        else:
            file_bytes = file_data
        
        file_size = len(file_bytes)
        
        # Validate
        is_valid, error = self.validate_file(filename, file_size)
        if not is_valid:
            return {
                'success': False,
                'error': error
            }
        
        # Determine storage location
        if project_name:
            safe_project_name = self._sanitize_name(project_name)
            storage_dir = self.projects_dir / safe_project_name / "resources"
        else:
            storage_dir = self.upload_dir
        
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Create unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        unique_filename = f"{timestamp}_{stem}{suffix}"
        
        file_path = storage_dir / unique_filename
        
        # Save file
        try:
            with open(file_path, 'wb') as f:
                f.write(file_bytes)
            
            # Extract text content if applicable
            text_content = self._extract_text(file_path)
            
            # Create metadata
            metadata = {
                'original_filename': filename,
                'stored_filename': unique_filename,
                'file_path': str(file_path),
                'file_size': file_size,
                'category': self.get_file_category(filename),
                'uploaded_at': datetime.now().isoformat(),
                'description': description,
                'project': project_name,
                'has_text_content': text_content is not None,
                'text_length': len(text_content) if text_content else 0
            }
            
            return {
                'success': True,
                'metadata': metadata,
                'text_content': text_content
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to save file: {str(e)}"
            }
    
    def upload_from_path(self, 
                        source_path: str,
                        project_name: Optional[str] = None,
                        description: Optional[str] = None) -> Dict:
        """
        Upload a file from a local path.
        
        Args:
            source_path: Path to the source file
            project_name: Optional project to associate with
            description: Optional description
            
        Returns:
            Dictionary with upload result
        """
        source = Path(source_path)
        if not source.exists():
            return {
                'success': False,
                'error': f"File not found: {source_path}"
            }
        
        with open(source, 'rb') as f:
            return self.upload_file(f.read(), source.name, project_name, description)
    
    # ========== TEXT EXTRACTION ==========
    
    def _extract_text(self, file_path: Path) -> Optional[str]:
        """
        Extract text content from file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Extracted text or None
        """
        ext = file_path.suffix.lower()
        
        try:
            # Plain text files
            if ext in ['.txt', '.md', '.csv']:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            
            # PDF files
            elif ext == '.pdf' and HAS_PDF:
                return self._extract_pdf_text(file_path)
            
            # DOCX files
            elif ext == '.docx' and HAS_DOCX:
                return self._extract_docx_text(file_path)
            
            # JSON files
            elif ext == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return json.dumps(data, indent=2)
            
            return None
            
        except Exception as e:
            print(f"Warning: Could not extract text from {file_path}: {e}")
            return None
    
    def _extract_pdf_text(self, file_path: Path) -> str:
        """Extract text from PDF file."""
        text_parts = []
        
        with open(file_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
        
        return '\n\n'.join(text_parts)
    
    def _extract_docx_text(self, file_path: Path) -> str:
        """Extract text from DOCX file."""
        doc = DocxDocument(file_path)
        
        text_parts = []
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_parts.append(paragraph.text)
        
        return '\n\n'.join(text_parts)
    
    def extract_text_from_file(self, file_path: str) -> Optional[str]:
        """
        Public method to extract text from any supported file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Extracted text or None
        """
        return self._extract_text(Path(file_path))
    
    # ========== EXPORT METHODS ==========
    
    def create_text_file(self, 
                        content: str,
                        filename: str,
                        project_name: Optional[str] = None) -> Dict:
        """
        Create a text file for download.
        
        Args:
            content: Text content
            filename: Desired filename
            project_name: Optional project association
            
        Returns:
            Dictionary with file info
        """
        # Determine storage location
        if project_name:
            safe_project_name = self._sanitize_name(project_name)
            storage_dir = self.projects_dir / safe_project_name / "exports"
        else:
            storage_dir = self.export_dir
        
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Add timestamp to filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = Path(filename).stem
        suffix = Path(filename).suffix or '.txt'
        unique_filename = f"{timestamp}_{stem}{suffix}"
        
        file_path = storage_dir / unique_filename
        
        # Write file
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                'success': True,
                'file_path': str(file_path),
                'filename': unique_filename,
                'size': len(content)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to create file: {str(e)}"
            }
    
    def create_json_file(self,
                        data: Dict,
                        filename: str,
                        project_name: Optional[str] = None) -> Dict:
        """
        Create a JSON file for download.
        
        Args:
            data: Dictionary to save as JSON
            filename: Desired filename
            project_name: Optional project association
            
        Returns:
            Dictionary with file info
        """
        content = json.dumps(data, indent=2)
        if not filename.endswith('.json'):
            filename = f"{filename}.json"
        return self.create_text_file(content, filename, project_name)
    
    # ========== FILE LISTING ==========
    
    def get_uploaded_files(self) -> List[Dict]:
        """
        List all files in the upload directory.
        
        Returns:
            List of file metadata dictionaries
        """
        return self._list_files_in_dir(self.upload_dir)
    
    def get_project_files(self, project_name: str) -> List[Dict]:
        """
        List all files for a project.
        
        Args:
            project_name: Name of the project
            
        Returns:
            List of file metadata dictionaries
        """
        safe_project_name = self._sanitize_name(project_name)
        resources_dir = self.projects_dir / safe_project_name / "resources"
        
        if not resources_dir.exists():
            return []
        
        return self._list_files_in_dir(resources_dir)
    
    def get_project_exports(self, project_name: str) -> List[Dict]:
        """
        List all exported files for a project.
        
        Args:
            project_name: Name of the project
            
        Returns:
            List of file metadata dictionaries
        """
        safe_project_name = self._sanitize_name(project_name)
        exports_dir = self.projects_dir / safe_project_name / "exports"
        
        if not exports_dir.exists():
            return []
        
        return self._list_files_in_dir(exports_dir)
    
    def _list_files_in_dir(self, directory: Path) -> List[Dict]:
        """List all files in a directory with metadata."""
        files = []
        
        if not directory.exists():
            return files
        
        for file_path in directory.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    'filename': file_path.name,
                    'path': str(file_path),
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'category': self.get_file_category(file_path.name)
                })
        
        return sorted(files, key=lambda x: x['modified'], reverse=True)
    
    # ========== FILE OPERATIONS ==========
    
    def read_file(self, file_path: str) -> Dict:
        """
        Read file contents.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with file contents and metadata
        """
        path = Path(file_path)
        
        if not path.exists():
            return {
                'success': False,
                'error': 'File not found'
            }
        
        # Security check
        if not self._is_allowed_path(path):
            return {
                'success': False,
                'error': 'Access denied: file not in allowed directories'
            }
        
        try:
            text_content = self._extract_text(path)
            
            return {
                'success': True,
                'filename': path.name,
                'category': self.get_file_category(path.name),
                'size': path.stat().st_size,
                'text_content': text_content,
                'has_text': text_content is not None
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to read file: {str(e)}"
            }
    
    def delete_file(self, file_path: str) -> Dict:
        """
        Delete a file.
        
        Args:
            file_path: Path to file to delete
            
        Returns:
            Dictionary with result
        """
        path = Path(file_path)
        
        # Security check
        if not self._is_allowed_path(path):
            return {
                'success': False,
                'error': "File path not in allowed directories"
            }
        
        try:
            if path.exists():
                os.remove(path)
                return {
                    'success': True,
                    'message': f"Deleted {path.name}"
                }
            else:
                return {
                    'success': False,
                    'error': "File not found"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to delete file: {str(e)}"
            }
    
    def _is_allowed_path(self, path: Path) -> bool:
        """Check if path is within allowed directories."""
        allowed_parents = [
            self.upload_dir,
            self.export_dir,
            self.projects_dir
        ]
        
        try:
            resolved = path.resolve()
            for parent in allowed_parents:
                if resolved.is_relative_to(parent.resolve()):
                    return True
            return False
        except (ValueError, RuntimeError):
            return False
    
    # ========== STATISTICS ==========
    
    def get_file_stats(self) -> Dict:
        """
        Get statistics about stored files.
        
        Returns:
            Dictionary with file statistics
        """
        stats = {
            'total_files': 0,
            'total_size': 0,
            'by_category': {},
            'by_project': {},
            'capabilities': {
                'pdf_extraction': HAS_PDF,
                'docx_extraction': HAS_DOCX
            }
        }
        
        # Check uploads directory
        if self.upload_dir.exists():
            for file_path in self.upload_dir.iterdir():
                if file_path.is_file():
                    stats['total_files'] += 1
                    stats['total_size'] += file_path.stat().st_size
                    
                    category = self.get_file_category(file_path.name) or 'unknown'
                    stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
        
        # Check project directories
        if self.projects_dir.exists():
            for project_dir in self.projects_dir.iterdir():
                if project_dir.is_dir():
                    resources_dir = project_dir / "resources"
                    if resources_dir.exists():
                        project_files = 0
                        for file_path in resources_dir.iterdir():
                            if file_path.is_file():
                                stats['total_files'] += 1
                                stats['total_size'] += file_path.stat().st_size
                                project_files += 1
                                
                                category = self.get_file_category(file_path.name) or 'unknown'
                                stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
                        
                        if project_files > 0:
                            stats['by_project'][project_dir.name] = project_files
        
        return stats
    
    # ========== HELPERS ==========
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize name for filesystem."""
        safe = name.lower().replace(' ', '_')
        safe = ''.join(c for c in safe if c.isalnum() or c == '_')
        return safe


# ========== SINGLETON & FACTORY ==========

_file_service: Optional[FileService] = None


def get_file_service() -> Optional[FileService]:
    """Get the singleton FileService instance."""
    global _file_service
    return _file_service


def initialize_file_service() -> Optional[FileService]:
    """
    Initialize and return the singleton FileService.
    
    Returns:
        FileService instance or None if initialization fails
    """
    global _file_service
    
    if _file_service is not None:
        return _file_service
    
    try:
        _file_service = FileService()
        return _file_service
    except Exception as e:
        print(f"Warning: Could not initialize FileService: {e}")
        return None
