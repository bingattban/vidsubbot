"""
URL and input validation utilities.
"""
import re
from typing import Optional
from urllib.parse import urlparse


def validate_url(url: str) -> bool:
    """
    Validate if string is a valid URL.
    
    Args:
        url: URL string to validate
        
    Returns:
        True if valid URL, False otherwise
    """
    try:
        result = urlparse(url.strip())
        
        # Check scheme and netloc
        if not result.scheme or not result.netloc:
            return False
        
        # Check scheme
        if result.scheme not in ['http', 'https']:
            return False
        
        # Check for basic domain format
        domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$'
        if not re.match(domain_pattern, result.netloc.split(':')[0]):
            return False
        
        return True
        
    except Exception:
        return False


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    
    # Limit length
    if len(filename) > 200:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:200 - len(ext) - 1] + '.' + ext
    
    return filename


def detect_command_injection(text: str) -> bool:
    """
    Detect potential command injection attempts.
    
    Args:
        text: Text to check
        
    Returns:
        True if suspicious patterns found
    """
    suspicious_patterns = [
        r'\$\(',      # Command substitution
        r'`[^`]+`',   # Backtick execution
        r'&&',        # Command chaining
        r'\|\|',      # OR operator
        r';',         # Command separator
        r'\\x[0-9a-fA-F]{2}',  # Hex encoding
        r'%[0-9a-fA-F]{2}',     # URL encoding
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, text):
            return True
    
    return False