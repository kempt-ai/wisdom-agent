"""
Wisdom Agent - Files Router

API endpoints for file upload, download, and management.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from pathlib import Path

from backend.services import get_file_service, initialize_file_service


router = APIRouter(prefix="/api/files", tags=["files"])


# ========== REQUEST/RESPONSE MODELS ==========

class TextFileCreate(BaseModel):
    """Request model for creating a text file."""
    content: str
    filename: str
    project_name: Optional[str] = None


class FileMetadata(BaseModel):
    """File metadata response."""
    filename: str
    path: str
    size: int
    modified: str
    category: Optional[str]


class FileStats(BaseModel):
    """File statistics response."""
    total_files: int
    total_size: int
    by_category: dict
    by_project: dict
    capabilities: dict


# ========== HELPER ==========

def get_service():
    """Get initialized file service or raise error."""
    service = get_file_service()
    if not service:
        service = initialize_file_service()
    if not service:
        raise HTTPException(status_code=503, detail="File service unavailable")
    return service


# ========== ENDPOINTS ==========

@router.get("/status")
async def file_service_status():
    """Check file service status and capabilities."""
    service = get_service()
    
    return {
        "status": "available",
        "upload_dir": str(service.upload_dir),
        "export_dir": str(service.export_dir),
        "supported_types": service.SUPPORTED_TYPES,
        "max_sizes_mb": {k: v / (1024*1024) for k, v in service.MAX_SIZES.items()}
    }


@router.get("/stats", response_model=FileStats)
async def get_file_stats():
    """Get file storage statistics."""
    service = get_service()
    return FileStats(**service.get_file_stats())


@router.get("/supported-types")
async def get_supported_types():
    """Get all supported file types."""
    service = get_service()
    
    return {
        "types": service.SUPPORTED_TYPES,
        "extensions": service.get_supported_extensions()
    }


# ========== UPLOAD ==========

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    project_name: Optional[str] = Form(None),
    description: Optional[str] = Form(None)
):
    """
    Upload a file.
    
    Optionally associate with a project.
    """
    service = get_service()
    
    # Read file content
    content = await file.read()
    
    result = service.upload_file(
        file_data=content,
        filename=file.filename,
        project_name=project_name,
        description=description
    )
    
    if not result['success']:
        raise HTTPException(status_code=400, detail=result.get('error', 'Upload failed'))
    
    return result


@router.post("/upload-multiple")
async def upload_multiple_files(
    files: List[UploadFile] = File(...),
    project_name: Optional[str] = Form(None)
):
    """Upload multiple files at once."""
    service = get_service()
    
    results = []
    for file in files:
        content = await file.read()
        result = service.upload_file(
            file_data=content,
            filename=file.filename,
            project_name=project_name
        )
        results.append({
            'filename': file.filename,
            'success': result['success'],
            'error': result.get('error'),
            'metadata': result.get('metadata')
        })
    
    successful = sum(1 for r in results if r['success'])
    
    return {
        "total": len(files),
        "successful": successful,
        "failed": len(files) - successful,
        "results": results
    }


# ========== LIST FILES ==========

@router.get("/uploads")
async def list_uploaded_files() -> List[FileMetadata]:
    """List all files in the upload directory."""
    service = get_service()
    files = service.get_uploaded_files()
    return [FileMetadata(**f) for f in files]


@router.get("/project/{project_name}")
async def list_project_files(project_name: str) -> List[FileMetadata]:
    """List all files for a project."""
    service = get_service()
    files = service.get_project_files(project_name)
    return [FileMetadata(**f) for f in files]


@router.get("/project/{project_name}/exports")
async def list_project_exports(project_name: str) -> List[FileMetadata]:
    """List exported files for a project."""
    service = get_service()
    files = service.get_project_exports(project_name)
    return [FileMetadata(**f) for f in files]


# ========== READ/EXTRACT ==========

@router.post("/read")
async def read_file(file_path: str):
    """
    Read file contents and extract text if possible.
    
    Args:
        file_path: Path to the file
    """
    service = get_service()
    result = service.read_file(file_path)
    
    if not result['success']:
        raise HTTPException(status_code=404, detail=result.get('error', 'File not found'))
    
    return result


@router.post("/extract-text")
async def extract_text(file_path: str):
    """
    Extract text content from a file.
    
    Supports: .txt, .md, .csv, .json, .pdf, .docx
    """
    service = get_service()
    
    text = service.extract_text_from_file(file_path)
    
    if text is None:
        raise HTTPException(
            status_code=400, 
            detail="Could not extract text from this file type"
        )
    
    return {
        "file_path": file_path,
        "text_length": len(text),
        "text_content": text
    }


# ========== CREATE/EXPORT ==========

@router.post("/create-text")
async def create_text_file(request: TextFileCreate):
    """
    Create a text file for download.
    
    Returns the path to the created file.
    """
    service = get_service()
    
    result = service.create_text_file(
        content=request.content,
        filename=request.filename,
        project_name=request.project_name
    )
    
    if not result['success']:
        raise HTTPException(status_code=500, detail=result.get('error', 'Failed to create file'))
    
    return result


@router.post("/create-json")
async def create_json_file(
    data: dict,
    filename: str,
    project_name: Optional[str] = None
):
    """Create a JSON file from data."""
    service = get_service()
    
    result = service.create_json_file(
        data=data,
        filename=filename,
        project_name=project_name
    )
    
    if not result['success']:
        raise HTTPException(status_code=500, detail=result.get('error', 'Failed to create file'))
    
    return result


# ========== DOWNLOAD ==========

@router.get("/download")
async def download_file(file_path: str):
    """
    Download a file.
    
    Args:
        file_path: Path to the file to download
    """
    service = get_service()
    
    path = Path(file_path)
    
    # Security check
    if not service._is_allowed_path(path):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        filename=path.name,
        media_type="application/octet-stream"
    )


# ========== DELETE ==========

@router.delete("/")
async def delete_file(file_path: str):
    """
    Delete a file.
    
    Args:
        file_path: Path to the file to delete
    """
    service = get_service()
    
    result = service.delete_file(file_path)
    
    if not result['success']:
        raise HTTPException(
            status_code=404 if result.get('error') == "File not found" else 400,
            detail=result.get('error', 'Delete failed')
        )
    
    return result


# ========== CATEGORIZE ==========

@router.get("/category/{filename}")
async def get_file_category(filename: str):
    """Get the category for a filename."""
    service = get_service()
    
    category = service.get_file_category(filename)
    
    return {
        "filename": filename,
        "category": category,
        "supported": category is not None
    }


@router.post("/validate")
async def validate_file_info(filename: str, file_size: int):
    """
    Validate if a file can be uploaded.
    
    Args:
        filename: Name of the file
        file_size: Size in bytes
    """
    service = get_service()
    
    is_valid, error = service.validate_file(filename, file_size)
    
    return {
        "filename": filename,
        "file_size": file_size,
        "file_size_mb": file_size / (1024 * 1024),
        "valid": is_valid,
        "error": error,
        "category": service.get_file_category(filename)
    }
