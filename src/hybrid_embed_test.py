from qdrant_client.models import Distance, Vector, VectorParams, models
from fastembed import SparseTextEmbedding, SparseEmbedding
import json
from tokenizers import Tokenizer
import ollama
import logging
import os
from typing import Any, Dict
from qdrant_client import QdrantClient as _QdrantClient, models
from qdrant_client.models import Document, PointStruct
import csv
import urllib.request
from qdrant_client.models import Document, PointStruct, SparseVector

from litellm import embedding, EmbeddingResponse
from pydantic import BaseModel, ConfigDict, StrictStr
from langchain_litellm import ChatLiteLLM, LiteLLMEmbeddings
from fastembed import LateInteractionTextEmbedding
from enum import Enum
# https://qdrant.tech/documentation/tutorials-search-engineering/reranking-hybrid-search/
#https://qdrant.tech/documentation/fastembed/fastembed-rerankers/
#https://qdrant.tech/documentation/manage-data/indexing/#idf-modifier

collection_name = "hybrid-search"
host = os.getenv("QDRANT_HOST", "localhost")
port = int(os.getenv("QDRANT_PORT", "6333"))
client = _QdrantClient(host=host, port=port)
import uuid


DENSE_EMBEDDING_MODEL = "openai/nomic-embed"#"sentence-transformers/all-MiniLM-L6-v2"
SPARSE_EMBEDDING_MODEL = "prithivida/Splade_PP_en_v1"
LATE_INTERACTION_EMBEDDING_MODEL = "answerdotai/answerai-colbert-small-v1"
LITE_LLM_URL = os.getenv("LITE_LLM_URL","http://litellm:4000")
LITE_LLM_API_KEY = os.getenv("LITE_LLM_API_KEY","sk-1234")
DIM_SIZE = 768

client.delete_collection(collection_name)
if not client.collection_exists(collection_name):
    client.create_collection(
        collection_name,
        vectors_config={
            "dense": models.VectorParams(
                size=DIM_SIZE,
                distance=models.Distance.COSINE,
            ),
            "multi": models.VectorParams(
                size=96,
                distance=models.Distance.COSINE,
                multivector_config=models.MultiVectorConfig(
                    comparator=models.MultiVectorComparator.MAX_SIM,
                ),
                hnsw_config=models.HnswConfigDiff(m=0)  #  Disable HNSW for reranking
            ),
        },
        sparse_vectors_config={
            "sparse": models.SparseVectorParams(modifier=models.Modifier.IDF)
        }
    )

class EmbedType(Enum):
    DENSE = "raw_text"
    SPARSE = "summary"
    LATE_INTERACTION = "rr"

class Embedder(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    dense_embedding_model : LiteLLMEmbeddings = LiteLLMEmbeddings(    
        api_base=LITE_LLM_URL,
        api_key="sk-1234",
        model=DENSE_EMBEDDING_MODEL,

    )
    sparse_embedding_model : SparseTextEmbedding = SparseTextEmbedding(
        model_name=SPARSE_EMBEDDING_MODEL,
        cuda=False,
        providers=["CUDAExecutionProvider"]
    )

    li_embedding_model : LateInteractionTextEmbedding= LateInteractionTextEmbedding(LATE_INTERACTION_EMBEDDING_MODEL)
    
    def embed(self, docs: str, type:EmbedType) -> Vector:
        ret : Vector = None
        if type == EmbedType.DENSE:
            resp : EmbeddingResponse = embedding(
            api_base=LITE_LLM_URL,
            api_key=LITE_LLM_API_KEY,
            input=docs,
            model=DENSE_EMBEDDING_MODEL,
            #dimensions=DIM_SIZE
            )
            ret= resp.data[0]['embedding']

        elif type == EmbedType.SPARSE:
            sparse_embeddings = list(self.sparse_embedding_model.embed([docs]))
            sparse = sparse_embeddings[0]
            
            # Convert FastEmbed object to Qdrant SparseVector
            ret = SparseVector(
                indices=sparse.indices.tolist(), 
                values=sparse.values.tolist()
            )
        

        elif type == EmbedType.LATE_INTERACTION:
            # Colbert returns a 2D numpy array
            li_embeddings = list(self.li_embedding_model.embed([docs]))
            # Convert numpy array to list[list[float]]
            ret= li_embeddings[0].tolist()
        return ret
        




embedder = Embedder()


#res = embed_response = litellm_embed.embed_documents(texts=documents)


def create_points():
    documents: list[str] = [
    "Chandrayaan-3 is India's third lunar mission",
    "It aimed to land a rover on the Moon's surface - joining the US, China and Russia",
    "The mission is a follow-up to Chandrayaan-2, which had partial success",
    "Chandrayaan-3 will be launched by the Indian Space Research Organisation (ISRO)",
    "The estimated cost of the mission is around $35 million",
    "It will carry instruments to study the lunar surface and atmosphere",
    "Chandrayaan-3 landed on the Moon's surface on 23rd August 2023",
    "It consists of a lander named Vikram and a rover named Pragyan similar to Chandrayaan-2. Its propulsion module would act like an orbiter.",
    "The propulsion module carries the lander and rover configuration until the spacecraft is in a 100-kilometre (62 mi) lunar orbit",
    "The mission used GSLV Mk III rocket for its launch",
    "Chandrayaan-3 was launched from the Satish Dhawan Space Centre in Sriharikota",
    "Chandrayaan-3 was launched earlier in the year 2023",
    ]
    points = (
        PointStruct(
            id=uuid.uuid4(),
            vector={
                "dense": embedder.embed(row,type=EmbedType.DENSE),
                "sparse": embedder.embed(row,type=EmbedType.SPARSE),
                "multi": embedder.embed(row,type=EmbedType.LATE_INTERACTION),
            },
            payload={
                "page_content": row, 
                "source": "chandrayaan_data.csv",
                "timestamp": "2023-08-23"
            }
        )
        for row in documents
    )
    client.upload_points(
        collection_name=collection_name,
        points=points,
        batch_size=25
    )

def hybrid_search(query:str):
    prefetch = [
    models.Prefetch(
        query=embedder.embed(query,type=EmbedType.DENSE),
        using="dense",
        limit=20,
    ),
    models.Prefetch(
        query=embedder.embed(query,type=EmbedType.SPARSE),
        using="sparse",
        limit=20,
    ),
    ]

    # results = client.query_points(
    #     collection_name,
    #     prefetch=prefetch,
    #     query=models.FusionQuery(fusion=models.Fusion.RRF),
    #     with_payload=True,
    #     limit=10,
    # )
    ## OR
    results = client.query_points(
        collection_name,
        prefetch=prefetch,
        query=embedder.embed(query,type=EmbedType.LATE_INTERACTION),
        using="multi",
        with_payload=True,
        limit=10,
    )

    print(results.points)
create_points()
hybrid_search("books with time travel")
# sparse_embeddings_list: list[SparseEmbedding] = list(
#     model.embed(documents, batch_size=6)
# ) 
# index = 0
# #print(sparse_embeddings_list[index])

# for i in range(5):
#     print(f"Token at index {sparse_embeddings_list[0].indices[i]} has weight {sparse_embeddings_list[0].values[i]}")

# tokenizer = Tokenizer.from_pretrained("Qdrant/Splade_PP_en_v1")

# def get_tokens_and_weights(sparse_embedding, tokenizer):
#     token_weight_dict = {}
#     for i in range(len(sparse_embedding.indices)):
#         token = tokenizer.decode([sparse_embedding.indices[i]])
#         weight = sparse_embedding.values[i]
#         token_weight_dict[token] = weight

#     # Sort the dictionary by weights
#     token_weight_dict = dict(sorted(token_weight_dict.items(), key=lambda item: item[1], reverse=True))
#     return token_weight_dict

# # # Test the function with the first SparseEmbedding
# print(json.dumps(get_tokens_and_weights(sparse_embeddings_list[index], tokenizer), indent=4))


#model_name = "prithivida/Splade_PP_en_v1"
# This triggers the model download
#model = SparseTextEmbedding(model_name=model_name)



# if client.collection_exists(collection_name=collection_name):
#     client.delete_collection(collection_name=collection_name)




# def parse_csv(url):
#     with urllib.request.urlopen(url) as response:
#         reader = csv.DictReader(line.decode('utf-8') for line in response)
#         yield from reader

# csv_url = 'https://raw.githubusercontent.com/qdrant/examples/refs/heads/master/sci-fi-books/top_100_scifi_books_full.csv'

# #https://qdrant.tech/documentation/manage-data/points/#named-vectors
# # client.create_payload_index(
# #     collection_name="my_collection",
# #     field_name="city",
# #     field_schema=models.PayloadSchemaType.KEYWORD, # Types: keyword, integer, float, bool, geo, text
# # )
# en = list(enumerate(parse_csv(csv_url)))
# desc_test = en[0][1]['Description']
# sparse_embeddings_list: list[SparseEmbedding] = list(model.embed(desc_test, batch_size=6)) 
# sparse_embeddings_list2 = Document(text=desc_test, model=sparse_embedding_model)

# points = (
#     PointStruct(
#         id=idx,
#         vector={
#             "dense": Document(text=row['Description'], model=dense_embedding_model),
#             "sparse": Document(text=row['Description'], model=sparse_embedding_model),
#             "multi": Document(text=row['Description'], model=late_interaction_embedding_model),
#         },
#         payload={"title": row['Title'], "author": row['Author'], "description": row['Description']}
#     )
#     for idx, row in en
# )
# c



