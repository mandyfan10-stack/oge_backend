## 2024-05-19 - Content-Security-Policy for FastAPI Docs
**Vulnerability:** Missing Content-Security-Policy header, leaving application more vulnerable to XSS and data injection attacks.
**Learning:** Adding a generic strict CSP breaks FastAPI's auto-generated Swagger UI/ReDoc documentation because they rely on external CDNs (cdn.jsdelivr.net, fastapi.tiangolo.com).
**Prevention:** When applying CSP to FastAPI apps, explicitly allow necessary sources for the documentation (`script-src 'unsafe-inline' cdn.jsdelivr.net`, `style-src 'unsafe-inline' cdn.jsdelivr.net`, `img-src data: fastapi.tiangolo.com`) so the docs continue to function.
## 2024-05-20 - Information Leakage in Error Responses
**Vulnerability:** The API endpoints were returning verbose error messages that exposed the internal name of an environment variable (`GROQ_API_KEY`) and the underlying hosting infrastructure (`Render`).
**Learning:** Returning detailed error messages directly to the client can be a security risk (Information Leakage). In a production environment, this exposes internal configuration or infrastructure details to an attacker, potentially assisting in further reconnaissance or targeted attacks.
**Prevention:** All unhandled exceptions or configuration errors must be caught and logged securely on the server using `logging.exception()`, but the HTTP response must contain only generic, non-descriptive messages like "Сервис временно недоступен" or "Пожалуйста, попробуй позже".
## 2024-05-21 - Denial of Service (DoS) via Unbounded List in Pydantic Model
**Vulnerability:** The `ChatRequest` Pydantic model accepted a `history` list without a maximum length constraint, allowing an attacker to send arbitrarily large payloads that could lead to memory exhaustion and a Denial of Service (DoS).
**Learning:** Pydantic validation for lists does not enforce length limits by default. If an endpoint accepts a list of objects and loads them into memory (especially large objects or long lists), it can be exploited.
**Prevention:** Always apply `max_length` constraints to list/array fields in request models (e.g., `history: Optional[list[ChatMessage]] = Field(default=None, max_length=50)`) to enforce upper bounds on input size.
