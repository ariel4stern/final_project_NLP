import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
import os
#from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

load_dotenv()

# Free local embedding model — no API key needed
#os.environ["HUGGINGFACEHUB_API_TOKEN"] = os.getenv("HF_TOKEN")
#ef = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

# OPEN API embedding model — API key needed
ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=os.getenv("OPENAI_API_KEY"),
    model_name="text-embedding-3-large"
)

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(
    name="movies",
    embedding_function=ef
)

# --- Add your documents here ---
collection.add(
    documents=[
    "The Shawshank Redemption — a prison drama about hope, patience, and lifelong friendship between two inmates who maintain their humanity under harsh conditions",
    "Inception — a sci-fi heist thriller about entering layered dream worlds to plant ideas in the subconscious mind while struggling to distinguish reality from illusion",
    "The Lion King — a coming-of-age animated story about a young lion who learns responsibility, loss, and leadership after being exiled from his kingdom",
    "Saving Private Ryan — a World War II drama following soldiers on a dangerous mission behind enemy lines to rescue a single paratrooper",
    "Braveheart — a historical epic about a Scottish warrior who leads a violent rebellion for freedom against English rule",
    "The Prestige — a psychological thriller about two rival magicians whose obsession with outperforming each other leads to deception and sacrifice",
    "Whiplash — a psychological drama about an ambitious young drummer pushed to emotional and physical extremes by an abusive but genius instructor",
    "Django Unchained — a western revenge story about a freed slave who teams up with a bounty hunter to rescue his wife from a brutal plantation owner",
    "The Wolf of Wall Street — a biographical crime drama about excessive greed, corruption, and the rise and fall of a stockbroker in the financial world",
    "Mad Max: Fury Road — a post-apocalyptic action film about survival, escape, and rebellion in a desert wasteland ruled by tyranny",
    "La La Land — a romantic musical drama about two artists struggling between love, ambition, and career dreams in Los Angeles",
    "The Social Network — a biographical drama about the creation of Facebook and the personal and legal conflicts that emerge from its success",
    "Black Panther — a superhero film about a newly crowned king balancing tradition and technology while protecting his hidden advanced nation",
    "Parasite — a dark social satire about class inequality and manipulation between two families from vastly different economic backgrounds",
    "Joker — a psychological character study about a mentally unstable man descending into chaos and becoming an infamous criminal figure"
]      # ... add at least 15 total
    ,metadatas=[
        {"genre": "drama", "year": 1994},
        {"genre": "sci-fi", "year": 2010},
        {"genre": "animation", "year": 1994},
        {"genre": "war", "year": 1998},
        {"genre": "history", "year": 1995},
        {"genre": "drama", "year": 2006},
        {"genre": "drama", "year": 2014},
        {"genre": "western", "year": 2012},
        {"genre": "biography", "year": 2013},
        {"genre": "action", "year": 2015},
        {"genre": "romance", "year": 2016},
        {"genre": "drama", "year": 2010},
        {"genre": "superhero", "year": 2018},
        {"genre": "thriller", "year": 2019},
        {"genre": "crime", "year": 2019}
    ]       # ... one metadata dict per document
    ,ids=[
        "doc1", "doc2", "doc3", "doc4", "doc5",
        "doc6", "doc7", "doc8", "doc9", "doc10",
        "doc11", "doc12", "doc13", "doc14", "doc15"
    ]       # must be unique strings
)

print(f"Collection created with {collection.count()} documents")

