"""
Security tests for the Flask application
"""
import pytest
import tempfile
import os
from io import BytesIO
from unittest.mock import Mock, patch
from flask import Flask
from app.file_security import FileSecurityValidator, validate_and_track_upload
from config.security_config import (
    ALLOWED_EXTENSIONS, MAX_FILE_SIZE, MAGIC_NUMBERS,
    get_user_friendly_error_message
)

@pytest.fixture
def app():
    """Create a test Flask app"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    return app

@pytest.fixture
def client(app):
    """Create a test client"""
    return app.test_client()

@pytest.fixture
def file_validator():
    """Create a file validator instance"""
    return FileSecurityValidator()

class TestFileSecurity:
    """Test file upload security validation"""
    
    def test_valid_csv_file(self, file_validator):
        """Test validation of a valid CSV file"""
        csv_content = b"ticker,company\nAAPL,Apple Inc.\nMSFT,Microsoft Corp."
        file_obj = BytesIO(csv_content)
        
        is_valid, error_message, file_info = file_validator.validate_file(file_obj, "test.csv")
        
        assert is_valid
        assert error_message == ""
        assert file_info['file_extension'] == 'csv'
        assert file_info['file_size'] == len(csv_content)
        assert 'file_hash' in file_info
    
    def test_valid_xlsx_file(self, file_validator):
        """Test validation of a valid XLSX file"""
        # Create a minimal XLSX file (ZIP archive with XML content)
        xlsx_content = b'PK\x03\x04\x14\x00\x00\x00\x08\x00' + b'\x00' * 100
        file_obj = BytesIO(xlsx_content)
        
        is_valid, error_message, file_info = file_validator.validate_file(file_obj, "test.xlsx")
        
        assert is_valid
        assert error_message == ""
        assert file_info['file_extension'] == 'xlsx'
    
    def test_invalid_file_extension(self, file_validator):
        """Test rejection of invalid file extensions"""
        content = b"test content"
        file_obj = BytesIO(content)
        
        is_valid, error_message, file_info = file_validator.validate_file(file_obj, "test.exe")
        
        assert not is_valid
        assert "not allowed" in error_message
    
    def test_file_too_large(self, file_validator):
        """Test rejection of files that are too large"""
        large_content = b"x" * (MAX_FILE_SIZE + 1024)
        file_obj = BytesIO(large_content)
        
        is_valid, error_message, file_info = file_validator.validate_file(file_obj, "test.csv")
        
        assert not is_valid
        assert "exceeds maximum" in error_message
    
    def test_empty_file(self, file_validator):
        """Test rejection of empty files"""
        file_obj = BytesIO(b"")
        
        is_valid, error_message, file_info = file_validator.validate_file(file_obj, "test.csv")
        
        assert not is_valid
        assert error_message == get_user_friendly_error_message('file_upload_error')
    
    def test_invalid_csv_content(self, file_validator):
        """Test rejection of invalid CSV content"""
        invalid_csv = b"This is not a CSV file"
        file_obj = BytesIO(invalid_csv)
        
        is_valid, error_message, file_info = file_validator.validate_file(file_obj, "test.csv")
        
        assert not is_valid
        assert "CSV format" in error_message
    
    def test_invalid_xlsx_content(self, file_validator):
        """Test rejection of invalid XLSX content"""
        invalid_xlsx = b"This is not an XLSX file"
        file_obj = BytesIO(invalid_xlsx)
        
        is_valid, error_message, file_info = file_validator.validate_file(file_obj, "test.xlsx")
        
        assert not is_valid
        assert "ZIP archive" in error_message
    
    def test_filename_sanitization(self, file_validator):
        """Test filename sanitization"""
        dangerous_filename = "../../../etc/passwd.csv"
        sanitized = file_validator.sanitize_filename(dangerous_filename)
        
        assert ".." not in sanitized
        assert "etc" not in sanitized
        assert sanitized.endswith('.csv')
    
    def test_file_metadata_generation(self, file_validator):
        """Test file metadata generation"""
        content = b"test content"
        file_obj = BytesIO(content)
        
        is_valid, error_message, file_info = file_validator.validate_file(file_obj, "test.csv")
        
        assert 'file_hash' in file_info
        assert 'mime_type' in file_info
        assert 'magic_info' in file_info
        assert len(file_info['file_hash']) == 64  # SHA-256 hash length

class TestRateLimiting:
    """Test rate limiting functionality"""
    
    @patch('flask_limiter.util.get_remote_address')
    def test_rate_limiting_configuration(self, mock_get_remote_address, app):
        """Test that rate limiting is properly configured"""
        from flask_limiter import Limiter
        from flask_limiter.util import get_remote_address
        
        limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            default_limits=["200 per day", "50 per hour"]
        )
        
        @app.route('/test')
        @limiter.limit("5 per minute")
        def test_route():
            return "OK"
        
        # Test that rate limiting is applied
        for i in range(5):
            response = app.test_client().get('/test')
            assert response.status_code == 200
        
        # 6th request should be rate limited
        response = app.test_client().get('/test')
        assert response.status_code == 429

class TestCORSConfiguration:
    """Test CORS configuration"""
    
    def test_cors_development_config(self, app):
        """Test CORS configuration in development"""
        from flask_cors import CORS
        from config.security_config import get_cors_origins
        
        CORS(app, origins=get_cors_origins())
        
        @app.route('/test')
        def test_route():
            return "OK"
        
        response = app.test_client().get('/test')
        assert 'Access-Control-Allow-Origin' in response.headers
    
    def test_cors_production_config(self, app):
        """Test CORS configuration in production"""
        with patch.dict(os.environ, {'APP_ENV': 'production', 'ALLOWED_ORIGINS': 'https://example.com'}):
            from flask_cors import CORS
            from config.security_config import get_cors_origins
            
            CORS(app, origins=get_cors_origins())
            
            @app.route('/test')
            def test_route():
                return "OK"
            
            response = app.test_client().get('/test')
            assert 'Access-Control-Allow-Origin' in response.headers

class TestErrorHandling:
    """Test error handling and user-friendly messages"""
    
    def test_user_friendly_error_messages(self):
        """Test user-friendly error message generation"""
        messages = [
            'file_upload_error',
            'rate_limit_exceeded',
            'authentication_error',
            'permission_error',
            'validation_error',
            'server_error',
            'service_unavailable'
        ]
        
        for message_type in messages:
            message = get_user_friendly_error_message(message_type)
            assert message is not None
            assert len(message) > 0
            assert isinstance(message, str)
    
    def test_unknown_error_type(self):
        """Test handling of unknown error types"""
        message = get_user_friendly_error_message('unknown_error_type')
        assert message == 'An error occurred.'

class TestMonitoring:
    """Test monitoring and health check functionality"""
    
    def test_health_check_endpoints(self, app):
        """Test health check endpoints"""
        from app.monitoring import register_monitoring_routes, health_checker
        
        register_monitoring_routes(app, health_checker)
        
        # Test basic health check
        response = app.test_client().get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'
        
        # Test detailed health check
        response = app.test_client().get('/health/detailed')
        assert response.status_code == 200
        data = response.get_json()
        assert 'services' in data
        
        # Test metrics endpoint
        response = app.test_client().get('/metrics')
        assert response.status_code == 200
        assert 'text/plain' in response.headers['Content-Type']
    
    def test_quota_monitoring(self):
        """Test quota monitoring functionality"""
        from app.monitoring import QuotaMonitor
        
        monitor = QuotaMonitor()
        
        # Test Celery queue monitoring
        result = monitor.check_celery_queue_size()
        assert 'status' in result
        
        # Test Firestore quota monitoring
        result = monitor.check_firestore_quota()
        assert 'status' in result

if __name__ == '__main__':
    pytest.main([__file__]) 