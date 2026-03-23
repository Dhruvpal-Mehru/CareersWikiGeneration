import os
from dotenv import load_dotenv
from google import genai
from openai import AzureOpenAI
from azure.storage.blob import BlobServiceClient

load_dotenv()

# ── Test Gemini ──
print("Testing Gemini...")
key = os.getenv("GEMINI_API_KEY")
print(f"Key loaded: {key[:10]}..." if key else "❌ No key found!")

gemini = genai.Client(api_key=key)
response = gemini.models.generate_content(
    model="gemini-2.5-flash",
    contents="Say hello in one sentence."
)
print(f"✅ Gemini works: {response.text}")

# ── Test Azure OpenAI ──
print("\nTesting Azure OpenAI...")
openai_client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version="2025-01-01-preview"
)
response = openai_client.chat.completions.create(
    model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    messages=[{"role": "user", "content": "Say hello in one sentence."}]
)
print(f"✅ OpenAI works: {response.choices[0].message.content}")

# ── Test Azure Blob Storage ──
print("\nTesting Azure Blob Storage...")
blob_service = BlobServiceClient.from_connection_string(
    os.getenv("AZURE_STORAGE_CONNECTION_STRING")
)
container = blob_service.get_container_client(
    os.getenv("AZURE_CONTAINER_NAME")
)
container.upload_blob(
    name="test/hello.txt",
    data="Hello from MascotGO pipeline!",
    overwrite=True
)
print("✅ Blob Storage works: test file uploaded!")

print("\n🚀 All connections working — ready to build!")