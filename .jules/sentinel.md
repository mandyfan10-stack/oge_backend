## 2026-04-18 - [Secure CORS Configuration]
**Vulnerability:** Overly permissive CORS with allow_origins=["*"] combined with allow_credentials=True. This allows any origin to make authenticated requests, which is a major security risk and violates CORS specs.
**Learning:** The FastAPI application used insecure defaults for CORS middleware which could allow CSRF-like attacks or unwanted cross-origin access to the LLM backend.
**Prevention:** Use an ALLOWED_ORIGINS environment variable to restrict cross-origin access to specific trusted domains, falling back to localhost for development.
