"""
Middleware for request handling, rate limiting, and error management.
"""

import time
import logging
from typing import Dict, List
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import settings

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)

# Simple in-memory rate limiting (in production, use Redis)
rate_limit_store: Dict[str, List[float]] = {}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware."""

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute

    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Check rate limit
        current_time = time.time()
        if client_ip in rate_limit_store:
            # Remove old requests (older than 1 minute)
            rate_limit_store[client_ip] = [
                req_time for req_time in rate_limit_store[client_ip]
                if current_time - req_time < 60
            ]

            # Check if limit exceeded
            if len(rate_limit_store[client_ip]) >= self.requests_per_minute:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "message": f"Maximum {self.requests_per_minute} requests per minute allowed",
                        "retry_after": 60
                    }
                )

        # Add current request
        if client_ip not in rate_limit_store:
            rate_limit_store[client_ip] = []
        rate_limit_store[client_ip].append(current_time)

        # Continue with request
        response = await call_next(request)

        # Add rate limit headers
        if client_ip in rate_limit_store:
            remaining = self.requests_per_minute - len(rate_limit_store[client_ip])
            response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
            response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)

        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Request logging middleware."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )

        # Process request
        response = await call_next(request)

        # Calculate processing time
        process_time = time.time() - start_time

        # Log response
        logger.info(
            f"Response: {response.status_code} "
            f"took {process_time:.3f}s"
        )

        # Add processing time header
        response.headers["X-Process-Time"] = str(process_time)

        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware."""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response

        except HTTPException:
            # Re-raise HTTP exceptions (they're handled by FastAPI)
            raise

        except Exception as e:
            # Log the error
            logger.error(f"Unhandled error: {str(e)}", exc_info=True)

            # Return error response
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "message": "An unexpected error occurred",
                    "detail": str(e) if settings.debug else "Contact support for assistance"
                }
            )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Add CORS headers if not already present
        if "Access-Control-Allow-Origin" not in response.headers:
            response.headers["Access-Control-Allow-Origin"] = "*"

        return response
