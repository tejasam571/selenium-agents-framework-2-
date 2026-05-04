from dotenv import load_dotenv
import os
load_dotenv()
key = os.getenv("GEMINI_API_KEY")
print(f"Key loaded: {key[:10]}..." if key else "NO KEY FOUND")