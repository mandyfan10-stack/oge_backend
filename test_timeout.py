import asyncio
import os
os.environ["GROQ_API_KEY"] = "fake_key"
from unittest.mock import patch
from fastapi.testclient import TestClient

import server
from importlib import reload
reload(server)

def test_groq_timeout_config():
    if server.client:
        assert server.client.timeout == 10.0

test_groq_timeout_config()
print("Success!")
