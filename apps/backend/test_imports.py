#!/usr/bin/env python
"""Quick test to verify refactored modules import correctly"""

try:
    from ai_engine.faithfulness_scorer import verify_faithfulness, evaluate_with_ragas, score_answer
    from ai_engine.vault_config import get_groq_api_key
    from ai_engine.vector_store import get_embedding_model, get_vector_store
    from ai_engine.rag_logic import query_academic_rag
    
    print("✅ ALL MODULES IMPORTED SUCCESSFULLY")
    print("  ✅ faithfulness_scorer.py - OK")
    print("  ✅ vault_config.py - OK") 
    print("  ✅ vector_store.py - OK")
    print("  ✅ rag_logic.py - OK (with imports)")
    print("\n✅ Refactoring is CLEAN - no import errors!")
    
except Exception as e:
    print(f"❌ IMPORT ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
