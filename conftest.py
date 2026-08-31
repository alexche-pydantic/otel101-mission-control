"""Make the two demo modules importable, and guarantee the tests never call OpenAI."""

import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

# Constructing an Agent resolves the provider, which wants a key. The tests never
# reach the network: pydantic-ai's ALLOW_MODEL_REQUESTS is off and models are mocked.
os.environ.setdefault("OPENAI_API_KEY", "test-key-never-used")
