## 2024-05-18 - [Security Headers vs FastAPI Docs]
**Vulnerability:** Weak CSP / missing security headers.
**Learning:** Applying a restrictive `Content-Security-Policy` like `default-src 'none'` completely breaks FastAPI's auto-generated documentation pages (Swagger UI and ReDoc). These pages require inline scripts/styles and external assets from CDNs.
**Prevention:** When adding CSP to FastAPI apps, explicitly allow necessary sources for docs: `script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https://fastapi.tiangolo.com;`
