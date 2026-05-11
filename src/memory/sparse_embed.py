from fastembed import SparseTextEmbedding, SparseEmbedding
import json
from tokenizers import Tokenizer

model_name = "prithivida/Splade_PP_en_v1"
# This triggers the model download
#model = SparseTextEmbedding(model_name=model_name)

model = SparseTextEmbedding(
    model_name=model_name,
    cuda=False,
    providers=["CUDAExecutionProvider"]
)



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

sparse_embeddings_list: list[SparseEmbedding] = list(
    model.embed(documents, batch_size=6)
) 
index = 0
#print(sparse_embeddings_list[index])

for i in range(5):
    print(f"Token at index {sparse_embeddings_list[0].indices[i]} has weight {sparse_embeddings_list[0].values[i]}")

tokenizer = Tokenizer.from_pretrained("Qdrant/Splade_PP_en_v1")

def get_tokens_and_weights(sparse_embedding, tokenizer):
    token_weight_dict = {}
    for i in range(len(sparse_embedding.indices)):
        token = tokenizer.decode([sparse_embedding.indices[i]])
        weight = sparse_embedding.values[i]
        token_weight_dict[token] = weight

    # Sort the dictionary by weights
    token_weight_dict = dict(sorted(token_weight_dict.items(), key=lambda item: item[1], reverse=True))
    return token_weight_dict

# # Test the function with the first SparseEmbedding
print(json.dumps(get_tokens_and_weights(sparse_embeddings_list[index], tokenizer), indent=4))
