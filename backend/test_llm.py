"""Quick LLM test script — run inside the backend container."""
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rag_backend.settings')
django.setup()

from ai_engine.rag_logic import get_api_key_from_vault, call_gemini, call_groq_llama

key = get_api_key_from_vault('GOOGLE_API_KEY')
print('Got API key:', key[:10] if key else 'NONE')

prompt = 'Return a JSON object with keys: answer, faithfulness_score, explanation, source_citation. Set answer to hello world.'

print('\n--- Testing Gemini (gemini-2.0-flash) ---')
try:
    r = call_gemini(prompt, key)
    print('SUCCESS:', r[:300])
except Exception as e:
    print('FAIL:', type(e).__name__, str(e)[:400])

print('\n--- Testing Groq (llama-3.3-70b-versatile) ---')
try:
    r = call_groq_llama(prompt)
    print('SUCCESS:', r[:300])
except Exception as e:
    print('FAIL:', type(e).__name__, str(e)[:400])
