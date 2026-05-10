# Memory Manager — Redis Taxonomy Query Guide

**Purpose:** How the memory manager reads, validates against, and extends the evolving taxonomy schema stored in Redis. All keys under `taxonomy:` namespace.

---

## 1. Startup Init

Load once at startup. Cache locally — no repeated Redis calls during ingestion.

```python
# Non-blocking enumeration (NEVER use KEYS)
cursor = 0
while True:
    cursor, keys = redis.scan(cursor, match="taxonomy:*", count=100)
    for key in keys:
        # load based on type (see §2)
    if cursor == 0:
        break
```

## 2. Read Patterns

### Category Types
```
smembers taxonomy:category_types
# → ["knowledge", "objective", "learning", "thought"]
```

### Valid Subcategories for a Type
```
hgetall taxonomy:cat:knowledge:subcats
# → {definition: active, domain_rule: active, api_spec: active, ...}
```

### Valid Tags for a Type
```
hgetall taxonomy:cat:learning:tags
# → {direct_input: active, inferred: active, failure: active, ...}
```

### Valid Keywords for a Type
```
hgetall taxonomy:cat:thought:keywords
# → {question_text: active, confidence_level: active, ...}
```

### Node Types (Graph Labels)
```
hgetall taxonomy:node_types
# → {Bug: active, Decision: active, Knowledge: active, Agent: staged, ...}
```
Filter by status: `active` = usable now, `staged` = defined but not yet wired.

### Edge Types (Flat List)
```
smembers taxonomy:edge_types
# → ["AFFECTS", "RESOLVES", "SATISFIES", "DEPENDS_ON", ...]
```

### Payload Indexes (Qdrant)
```
hgetall taxonomy:payload_indexes
# → {category_type: keyword, category: keyword, tags: keyword_list, ...}
```
Use this to create Qdrant payload indexes at collection init time.

### Collection Config
```
hgetall taxonomy:collection_config
# → {collection_name: memory_chunks, vector_size: 768, distance_metric: COSINE, ...}
```

### Metadata
```
hgetall taxonomy:meta
# → {version: 1, updated_at: ..., source: ...}
```

---

## 3. Validation Patterns

### During ingestion — check one value
```
sismember taxonomy:category_types "knowledge"              # True
hexists taxonomy:cat:knowledge:subcats "api_spec"          # True
hexists taxonomy:cat:learning:tags "halting_error"         # True
hexists taxonomy:cat:objective:tags "experimental"         # False (unknown)
```

### Batch validation (pipeline for multiple tags)
```python
pipe = redis.pipeline()
for tag in classifier_output.tags:
    pipe.hexists(f"taxonomy:cat:{category_type}:tags", tag)
results = pipe.execute()  # list of bools
```

---

## 4. Extend Patterns (Schema Learns)

When the classifier encounters something unknown, add it. Schema evolves without code changes.

### New tag discovered
```
hset taxonomy:cat:knowledge:tags "experimental" "active"
```

### New subcategory discovered
```
hset taxonomy:cat:objective:subcats "dependency" "active"
```

### New keyword discovered
```
hset taxonomy:cat:thought:keywords "related_goal" "active"
```

### New edge type discovered
```
sadd taxonomy:edge_types "VALIDATES"
```

### New category type (complete with subdata)
```
sadd taxonomy:category_types "audit"
hset taxonomy:cat:audit:subcats finding active recommendation active
hset taxonomy:cat:audit:tags critical active minor active
hset taxonomy:cat:audit:keywords audit_source active severity active
```

### Deprecate (soft — value = deprecated)
```
hset taxonomy:cat:learning:tags "old_pattern" "deprecated"
```
Memory manager reads value: `active` → use freely, `deprecated` → accept with warning or reject.

---

## 5. Query Patterns (for Memory Manager Runtime)

### "What category types exist?"
```python
category_types = redis.smembers("taxonomy:category_types")
```

### "For this category_type, what subcategories can the classifier return?"
```python
subcats = redis.hgetall(f"taxonomy:cat:{category_type}:subcats")
active_subcats = [k for k, v in subcats.items() if v == "active"]
```

### "Is this edge type valid for graph ingestion?"
```python
redis.sismember("taxonomy:edge_types", edge_name)
```

### "What Qdrant payload indexes do I need to create?"
```python
indexes = redis.hgetall("taxonomy:payload_indexes")
```

### "What collection name / vector size / distance metric?"
```python
config = redis.hgetall("taxonomy:collection_config")
```

---

## 6. Key Layout Reference

```
taxonomy:category_types            SET    {knowledge, objective, learning, thought}
taxonomy:cat:{type}:subcats        HASH   {name: active|deprecated, ...}
taxonomy:cat:{type}:tags           HASH   {name: active|deprecated, ...}
taxonomy:cat:{type}:keywords       HASH   {name: active|deprecated, ...}
taxonomy:node_types                HASH   {Bug: active, Decision: active, Agent: staged, ...}
taxonomy:edge_types                SET    {AFFECTS, RESOLVES, ...}
taxonomy:payload_indexes           HASH   {category_type: keyword, tags: keyword_list, ...}
taxonomy:collection_config         HASH   {collection_name: ..., vector_size: ..., ...}
taxonomy:meta                      HASH   {version: ..., updated_at: ..., source: ...}
```

## 7. JSON Backup

Full schema snapshot at `docs/rag-dev/taxonomy-schema.json`. Restore with:
```python
from pathlib import Path
import json
schema = json.loads(Path("docs/rag-dev/taxonomy-schema.json").read_text())
# pipeline all data into Redis (see implementer spec)
```
