### Example payload (inspired by prior mem0-based metadata patterns)

```python
{
    "chunk_id":       str,       # UUID — immutable identity
    "graph_node_id":  str,       # e.g. "bug-42" — bidirectional link
    "session_id":     str,       # which session produced this
    "created_at":     str,       # ISO8601 timestamp of first ingestion
    "updated_at":     str,       # ISO8601 timestamp of last modification
    "validated_at":   str,       # ISO8601 timestamp of last validation pass
    "category_type":  str,       # singular category value - learning, concept, data
    "category"        str,       # reference to specfic local dataset that changes based on the parent category. I.e., if category was 'learning' - sub categories could be ['technical', 'behaviour'] - therefore the category would either be the string or the index 
    "tags":           list[str], # cross-cutting labels for filtering
    "key_words":       list[str], 
    "source_category": str,       # origin file/path
    "project_id":     str,       # project grouping key
    "source_type":    str,       # defines the the types of source
    "source":         str,       # directory context at creation
    "related_files":  list[dict],# [{path, entered}, ...]
    "summary":        str,       # optional LLM-generated summary
    "version":        int,       # monotonic, incremented on reingest
    "status":         str,       # active | superseded | stale | merged
    "related_nodes"   list[str]
}
```
