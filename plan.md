1. **Understand and analyze the codebase for security vulnerabilities**:
   - The `/api/chat` endpoint currently forwards requests directly to the Groq API without any incoming rate limiting, leaving it vulnerable to DoS attacks and API quota exhaustion.
2. **Implement IP-based rate limiting in `server.py`**:
   - Import `Request` from `fastapi` and `time`.
   - Add a bounded dictionary `_ip_tracking` with a maximum size `MAX_TRACKED_IPS = 1000` to prevent memory exhaustion from unique or spoofed IPs.
   - Implement `check_rate_limit(ip: str)` that limits requests to 10 per minute per IP.
   - Update `chat_endpoint` to accept `request: Request`, retrieve the IP using `request.client.host` (to prevent spoofing), and return `{"reply": RATE_LIMIT_REPLY}` if the rate limit is exceeded.
3. **Write tests to verify the rate limiting**:
   - Create `test_rate_limiting.py` or append to an existing test file to ensure the rate limit blocks IPs after the maximum allowed requests and does not exceed memory constraints.
4. **Complete pre-commit steps to ensure proper testing, verification, review, and reflection are done**:
   - Format and lint code.
   - Run tests.
5. **Submit a Pull Request**:
   - PR Title: `🛡️ Sentinel: [HIGH] Fix Missing rate limiting on sensitive endpoints`
   - Describe the issue, impact, and fix according to Sentinel guidelines.
