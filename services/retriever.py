import faiss #vector database 
import numpy as np

#Took help of ai--
class Retriever:
    def __init__(self, documents):
        self.documents = documents
        self.index = self._build_index()

    def _build_index(self):
        # convertnig list of embeddings to a 2D numpy array
        embeddings = np.array([doc["embedding"] for doc in self.documents]).astype("float32")
        faiss.normalize_L2(embeddings)
        
        dimension = embeddings.shape[1]
        # IndexFlatIP = Inner Product (equivalent to Cosine Sim after normalization)
        index = faiss.IndexFlatIP(dimension)
        index.add(embeddings)
        return index

    def search(self, query_embedding, top_k=2):
        query_vec = np.array([query_embedding]).astype("float32")
        faiss.normalize_L2(query_vec)
        
        scores, indices = self.index.search(query_vec, top_k)
        
        results = []
        for rank, i in enumerate(indices[0]):
            results.append({
                "source": self.documents[i]["source"],
                "content": self.documents[i]["content"],
                "score": float(scores[0][rank])
            })
        return results