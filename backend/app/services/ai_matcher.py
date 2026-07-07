from sentence_transformers import SentenceTransformer
from typing import List

# We load the model globally so it's loaded once per application lifecycle
MODEL_NAME = "all-MiniLM-L6-v2"
model = None

def get_model():
    global model
    if model is None:
        model = SentenceTransformer(MODEL_NAME)
    return model

def generate_embedding(text: str) -> List[float]:
    """
    Generate an embedding for a single string.
    """
    transformer_model = get_model()
    # model.encode returns a numpy array, we convert to list
    embedding = transformer_model.encode(text)
    return embedding.tolist()

def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a list of strings.
    """
    transformer_model = get_model()
    embeddings = transformer_model.encode(texts)
    return [emb.tolist() for emb in embeddings]
