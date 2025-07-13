"""
File upload security and validation module
"""
import os
import time
import magic
import hashlib
import mimetypes
from typing import Dict, List, Tuple, Optional, Any
from werkzeug.utils import secure_filename
from flask import request
import structlog
from config.security_config import (
    ALLOWED_EXTENSIONS, MAX_FILE_SIZE, MAGIC_NUMBERS,
    get_user_friendly_error_message
)

logger = structlog.get_logger()

class FileSecurityValidator:
    """Comprehensive file upload security validator"""
    
    def __init__(self):
        self.mime = magic.Magic(mime=True)
        self.mime_magic = magic.Magic()
    
    def validate_file(self, file_obj, original_filename: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Comprehensive file validation
        
        Returns:
            Tuple[bool, str, Dict]: (is_valid, error_message, file_info)
        """
        try:
            # Read file content for validation
            file_content = file_obj.read()
            file_obj.seek(0)  # Reset file pointer
            
            # Basic validation
            if not file_content:
                return False, get_user_friendly_error_message('file_upload_error'), {}
            
            # Check file size
            if len(file_content) > MAX_FILE_SIZE:
                return False, f"File size exceeds maximum allowed size of {MAX_FILE_SIZE // (1024*1024)}MB", {}
            
            # Validate filename
            if not original_filename or '.' not in original_filename:
                return False, "Invalid filename", {}
            
            # Get file extension
            file_extension = original_filename.rsplit('.', 1)[1].lower()
            
            # Check allowed extensions
            if file_extension not in ALLOWED_EXTENSIONS:
                return False, f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}", {}
            
            # Validate file content using magic numbers
            content_valid, content_error = self._validate_file_content(file_content, file_extension)
            if not content_valid:
                return False, content_error, {}
            
            # Validate MIME type
            mime_valid, mime_error = self._validate_mime_type(file_content, file_extension)
            if not mime_valid:
                return False, mime_error, {}
            
            # Generate file info
            file_info = self._generate_file_info(file_content, original_filename, file_extension)
            
            logger.info("File validation successful", 
                       filename=original_filename, 
                       file_size=len(file_content),
                       file_type=file_extension)
            
            return True, "", file_info
            
        except Exception as e:
            logger.error("File validation error", 
                        filename=original_filename, 
                        error=str(e))
            return False, get_user_friendly_error_message('file_upload_error'), {}
    
    def _validate_file_content(self, file_content: bytes, file_extension: str) -> Tuple[bool, str]:
        """Validate file content using magic numbers"""
        try:
            # Get expected magic numbers for this file type
            expected_magic_numbers = MAGIC_NUMBERS.get(file_extension, [])
            
            if not expected_magic_numbers:
                logger.warning(f"No magic numbers defined for extension: {file_extension}")
                return True, ""  # Allow if no magic numbers defined
            
            # Check if file starts with any expected magic number
            for magic_number in expected_magic_numbers:
                if file_content.startswith(magic_number):
                    return True, ""
            
            # Additional validation for specific file types
            if file_extension == 'csv':
                return self._validate_csv_content(file_content)
            elif file_extension in ['xlsx', 'xls']:
                return self._validate_excel_content(file_content, file_extension)
            
            logger.warning(f"File content validation failed for {file_extension}")
            return False, f"Invalid file content for {file_extension} file"
            
        except Exception as e:
            logger.error("File content validation error", error=str(e))
            return False, "File content validation failed"
    
    def _validate_csv_content(self, file_content: bytes) -> Tuple[bool, str]:
        """Validate CSV file content"""
        try:
            # Decode content
            content_str = file_content.decode('utf-8', errors='ignore')
            
            # Check for basic CSV structure
            lines = content_str.split('\n')
            if len(lines) < 2:
                return False, "CSV file must contain at least 2 lines (header + data)"
            
            # Check if first line contains commas (indicating CSV structure)
            if ',' not in lines[0]:
                return False, "Invalid CSV format: missing comma separators"
            
            return True, ""
            
        except Exception as e:
            logger.error("CSV validation error", error=str(e))
            return False, "CSV file validation failed"
    
    def _validate_excel_content(self, file_content: bytes, file_extension: str) -> Tuple[bool, str]:
        """Validate Excel file content"""
        try:
            # For Excel files, we rely on magic numbers
            # Additional validation could include checking for ZIP structure (for .xlsx)
            if file_extension == 'xlsx':
                # .xlsx files are ZIP archives containing XML files
                if not file_content.startswith(b'PK'):
                    return False, "Invalid XLSX file: not a valid ZIP archive"
            
            return True, ""
            
        except Exception as e:
            logger.error("Excel validation error", error=str(e))
            return False, "Excel file validation failed"
    
    def _validate_mime_type(self, file_content: bytes, file_extension: str) -> Tuple[bool, str]:
        """Validate MIME type"""
        try:
            detected_mime = self.mime.from_buffer(file_content)
            
            # Expected MIME types for each extension
            expected_mimes = {
                'csv': ['text/csv', 'text/plain'],
                'xlsx': ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
                'xls': ['application/vnd.ms-excel']
            }
            
            expected_mime_list = expected_mimes.get(file_extension, [])
            
            if expected_mime_list and detected_mime not in expected_mime_list:
                logger.warning(f"MIME type mismatch for {file_extension}: expected {expected_mime_list}, got {detected_mime}")
                return False, f"Invalid MIME type: {detected_mime}"
            
            return True, ""
            
        except Exception as e:
            logger.error("MIME type validation error", error=str(e))
            return False, "MIME type validation failed"
    
    def _generate_file_info(self, file_content: bytes, original_filename: str, file_extension: str) -> Dict[str, Any]:
        """Generate file information"""
        return {
            'original_filename': original_filename,
            'secure_filename': secure_filename(original_filename),
            'file_extension': file_extension,
            'file_size': len(file_content),
            'file_hash': hashlib.sha256(file_content).hexdigest(),
            'mime_type': self.mime.from_buffer(file_content),
            'magic_info': self.mime_magic.from_buffer(file_content)
        }
    
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe storage"""
        return secure_filename(filename)
    
    def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """Get file metadata for logging and monitoring"""
        try:
            if not os.path.exists(file_path):
                return {'error': 'File not found'}
            
            file_size = os.path.getsize(file_path)
            file_extension = os.path.splitext(file_path)[1].lower().lstrip('.')
            
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            return {
                'file_path': file_path,
                'file_size': file_size,
                'file_extension': file_extension,
                'file_hash': hashlib.sha256(file_content).hexdigest(),
                'mime_type': self.mime.from_buffer(file_content),
                'magic_info': self.mime_magic.from_buffer(file_content)
            }
            
        except Exception as e:
            logger.error("Error getting file metadata", file_path=file_path, error=str(e))
            return {'error': str(e)}

class FileUploadTracker:
    """Track file uploads for monitoring and security"""
    
    def __init__(self):
        self.upload_history = []
        self.max_history_size = 1000
    
    def track_upload(self, file_info: Dict[str, Any], user_id: str, status: str):
        """Track file upload attempt"""
        upload_record = {
            'timestamp': time.time(),
            'user_id': user_id,
            'filename': file_info.get('original_filename'),
            'file_size': file_info.get('file_size'),
            'file_extension': file_info.get('file_extension'),
            'file_hash': file_info.get('file_hash'),
            'status': status,
            'ip_address': request.remote_addr if request else None
        }
        
        self.upload_history.append(upload_record)
        
        # Keep history size manageable
        if len(self.upload_history) > self.max_history_size:
            self.upload_history = self.upload_history[-self.max_history_size:]
        
        logger.info("File upload tracked", **upload_record)
    
    def get_upload_stats(self) -> Dict[str, Any]:
        """Get upload statistics"""
        if not self.upload_history:
            return {'total_uploads': 0}
        
        total_uploads = len(self.upload_history)
        successful_uploads = len([u for u in self.upload_history if u['status'] == 'success'])
        failed_uploads = total_uploads - successful_uploads
        
        # File type distribution
        file_types = {}
        for upload in self.upload_history:
            ext = upload.get('file_extension', 'unknown')
            file_types[ext] = file_types.get(ext, 0) + 1
        
        return {
            'total_uploads': total_uploads,
            'successful_uploads': successful_uploads,
            'failed_uploads': failed_uploads,
            'success_rate': (successful_uploads / total_uploads) * 100 if total_uploads > 0 else 0,
            'file_type_distribution': file_types,
            'recent_uploads': self.upload_history[-10:]  # Last 10 uploads
        }

# Global instances
file_validator = FileSecurityValidator()
upload_tracker = FileUploadTracker()

def validate_and_track_upload(file_obj, original_filename: str, user_id: str) -> Tuple[bool, str, Dict[str, Any]]:
    """Convenience function to validate and track file upload"""
    is_valid, error_message, file_info = file_validator.validate_file(file_obj, original_filename)
    
    # Track the upload attempt
    status = 'success' if is_valid else 'failed'
    upload_tracker.track_upload(file_info, user_id, status)
    
    return is_valid, error_message, file_info 