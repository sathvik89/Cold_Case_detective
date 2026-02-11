from sentence_transformers import SentenceTransformer

# model to turn text to vectors 
model = SentenceTransformer("all-MiniLM-L6-v2")

def embed_documents(documents):
    for doc in documents:
        doc["embedding"] = model.encode(doc["content"])
    return documents

def embed_query(query):
    return model.encode(query)