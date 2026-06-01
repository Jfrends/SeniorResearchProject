import search
from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer('all-MiniLM-L6-v2')

def get_embedding(text):
    return model.encode(text)

def create_embeddings(num_queries):
    docs = {}
    queries = {}
    for i in range(1, num_queries+1):
        text = search.get_doc_text(f"search/queries/{i}.txt")
        queries[i] = get_embedding(text)
    for i in range(1, 1401):
        text = search.get_doc_text(f"search/documents/{i}.txt")
        docs[i] = get_embedding(text)

    return docs, queries

def get_results(query_num, queries, docs):
    query_embed = queries[query_num]
    cosine_distances = []
    for doc_num, doc_embed in docs.items():
        distance = np.dot(query_embed, doc_embed) / (np.linalg.norm(query_embed) * np.linalg.norm(doc_embed))
        cosine_distances.append((doc_num, distance))
    
    cosine_distances.sort(key=lambda x: x[1], reverse=True)

    return [dist[0] for dist in cosine_distances[:20]]

def main():
    docs, queries = create_embeddings(20)
    total_score = 0
    human_results = search.get_judgement_df("search/human_judgement.txt")
    for i in range(20):
        returned = get_results(i+1, queries, docs)
        print(returned)
        score = search.map_score(returned, human_results[i+1])
        total_score += score
        print(f"Query {i+1}: {score}")

    print(f"Average MAP Score: {total_score / 20}")

main()

