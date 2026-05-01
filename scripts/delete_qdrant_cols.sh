#!/bin/bash
# 1. Fetch names of all collections
# 2. Iterate and delete each one
for collection in $(curl -s http://qdrant:6333/collections | jq -r '.result.collections[].name'); do
    echo "Deleting: $collection"
    curl -X DELETE "http://qdrant:6333/collections/$collection"
done
