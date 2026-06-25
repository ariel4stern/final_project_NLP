import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
import os

load_dotenv()

ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=os.getenv("OPENAI_API_KEY"),
    model_name= "text-embedding-3-large"

)
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_collection(
    name="movies",
    embedding_function=ef
)

# Example: query uses different words than the stored documents
queries =[ "a movie about escaping a difficult situation"
    , "film involving the subconscious mind"
    , "story about growing up and taking responsibility"
    , "a tale of revenge and justice",
    "a journey of self-discovery and transformation"
    # ... add 5 queries total
]

for query in queries:
    results = collection.query(
        query_texts=[query],
        n_results=3,
        include=["documents", "metadatas", "distances"]
    )
    print(f"\n🔍 Query: '{query}'")
    print("-" * 60)
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        print(f"  Distance: {dist:.4f}  |  {doc[:200]}...")
        print(f"  Metadata: {meta}")



