### Example payload (inspired by prior mem0-based metadata patterns)


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
{
  "common_indexed_fields": {
    "category_type": "keyword", // The primary router
    "category": "keyword",      // The sub-router
    "tags": "keyword_list",     // The attribute filter
    "status": "keyword",        // Lifecycle filter (active/stale)
    "graph_node_id": "keyword", // The bridge to GraphRAG traversal
    "project_id": "keyword"     // Multi-tenancy isolation
  },

  "category_definitions": {
    // 1. LEARNING: Evolution of agent/user behavior (Section 3.3: Agent Memory)
    "learning": {
      "categories": ["technical", "behavior", "preference", "constraint"],
      "tags_options": ["direct_input", "inferred", "high_stability", "volatile"],
      "key_words_focus": ["workflow_style", "syntax_preference", "user_limit"],
      "description": "Used to refine the 'Persona' and 'Execution Style' of the agent."
    },

    // 2. CONCEPT: Static knowledge & ontology (Section 3.1: Knowledge Graphs)
    "concept": {
      "categories": ["definition", "domain_rule", "taxonomy", "entity_property"],
      "tags_options": ["foundational", "deprecated", "expert_level", "cross_domain"],
      "key_words_focus": ["subject_uri", "parent_concept", "logical_operator"],
      "description": "The 'World Model'. Standard RAG often fails here; GraphRAG excels by linking concepts."
    },

    // 3. PLANNING: Goal decomposition (Section 3.1.2: Task Decomposition)
    "planning": {
      "categories": ["goal", "sub_task", "milestone", "condition", "blocker"],
      "tags_options": ["p0", "p1", "sequential", "parallel", "high_uncertainty"],
      "key_words_focus": ["prerequisite_id", "outcome_target", "estimated_effort"],
      "description": "Maps the Task Dependency Graph (TDG). Critical for agents to know 'What is next?'"
    },

    // 4. EXPERIENCE: Episodic memory of actions (Section 3.3.1: Memory Organization)
    "experience": {
      "categories": ["action_result", "observation", "error_trace", "user_feedback"],
      "tags_options": ["success", "failure", "halting_error", "optimized_path"],
      "key_words_focus": ["tool_id", "latency_ms", "token_usage", "correction_id"],
      "description": "Historical logs. Allows the agent to 'remember' that an action failed before."
    },

    // 5. EXECUTION: Technical tool & environment specs (Section 3.2: Tool Usage)
    "execution": {
      "categories": ["api_spec", "parameter_map", "env_config", "access_protocol"],
      "tags_options": ["production", "sandbox", "read_only", "destructive"],
      "key_words_focus": ["endpoint_url", "auth_type", "rate_limit", "schema_version"],
      "description": "The 'How-To' layer. Defines how the agent interacts with external software/APIs."
    }
  },

  "implementation_example": {
    "chunk_id": "8f3e-...",
    "graph_node_id": "node_planning_login_flow",
    "category_type": "planning",
    "category": "sub_task", // Selected from 'planning' list
    "tags": ["p0", "sequential"], // Selected from 'planning' tags
    "key_words": ["auth_module", "prereq_db_connect"],
    "status": "active",
    "version": 1,
    // Non-indexed data-heavy fields for post-retrieval context
    "related_nodes": ["node_db_01", "node_user_schema"],
    "summary": "Implement the JWT handshake for the main login flow."
  }
}
