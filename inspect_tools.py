
import google.generativeai as genai
import inspect

print("Google Generative AI version:", genai.__version__)

try:
    print("\nFields in genai.protos.Tool:")
    # In recent versions protos are exposed differently, let's try to find where Tool is
    if hasattr(genai, 'protos'):
        tool_proto = genai.protos.Tool
        # Inspect dir() of an instance
    t = genai.protos.Tool()
    print("\nAttributes of genai.protos.Tool instance:")
    for attr in dir(t):
        if not attr.startswith('_'):
            print(f"- {attr}")

except Exception as e:
    print(f"Error inspecting protos: {e}")

print("\nTesting Tool instantiation:")
try:
    # Try the old way
    t1 = genai.protos.Tool(google_search=genai.protos.GoogleSearch())
    print("SUCCESS: genai.protos.Tool(google_search=...) worked")
except Exception as e:
    print(f"FAILED: genai.protos.Tool(google_search=...) - {e}")

try:
    # Try the new way
    t2 = genai.protos.Tool(google_search_retrieval=genai.protos.GoogleSearchRetrieval())
    print("SUCCESS: genai.protos.Tool(google_search_retrieval=...) worked")
except Exception as e:
    print(f"FAILED: genai.protos.Tool(google_search_retrieval=...) - {e}")
