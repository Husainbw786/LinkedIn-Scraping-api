"""Custom exceptions for the LinkedIn job scraper"""

class LinkedInScraperException(Exception):
    """Base exception for LinkedIn scraper"""
    pass

class ResumeParsingError(LinkedInScraperException):
    """Raised when resume parsing fails"""
    pass

class ScrapingError(LinkedInScraperException):
    """Raised when web scraping fails"""
    pass

class RateLimitError(LinkedInScraperException):
    """Raised when rate limit is exceeded"""
    pass

class AuthenticationError(LinkedInScraperException):
    """Raised when LinkedIn authentication fails"""
    pass

class ValidationError(LinkedInScraperException):
    """Raised when input validation fails"""
    pass
