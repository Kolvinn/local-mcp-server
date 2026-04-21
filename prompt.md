I want to start building with Mem0 — a self-improving memory layer for LLM
applications that gives agents persistent context across sessions.

## Mem0 Resources

**Documentation:**
- Main docs: https://docs.mem0.ai
- Platform Quickstart: https://docs.mem0.ai/platform/quickstart
- OSS Python Quickstart: https://docs.mem0.ai/open-source/python-quickstart
- OSS Node.js Quickstart: https://docs.mem0.ai/open-source/node-quickstart
- API Reference: https://docs.mem0.ai/api-reference
- Full LLM-friendly docs: https://docs.mem0.ai/llms.txt

**Code & Examples:**
- Core repo: https://github.com/mem0ai/mem0
- Python SDK: pip install mem0ai
- TypeScript SDK: npm install mem0ai
- Cookbooks: https://docs.mem0.ai/cookbooks/overview

**What Mem0 Does:**
Mem0 is a memory layer for AI apps — managed (Mem0 Platform) or self-hosted
(Open Source). It stores, retrieves, and manages user memories so agents
remember preferences, learn from interactions, and personalize over time.
Sub-50ms retrieval. Dual storage: vector embeddings + graph databases.

**Architecture Overview:**
- Memory is scoped by user_id, agent_id, or run_id
- Core operations: add, search, update, delete
- Memory types: factual (preferences, facts), episodic (past interactions),
  semantic (concept relationships), working (session state)
- Integration pattern: retrieve relevant memories → generate response → store
  new memories

**Quick Usage (Python Platform):**
  from mem0 import MemoryClient
  client = MemoryClient(api_key="m0-xxx")
  client.add("I prefer dark mode and use VS Code.", user_id="user1")
  results = client.search("What editor do they use?", filters={"user_id": "user1"})

**Quick Usage (JavaScript Platform):**
  import MemoryClient from 'mem0ai';
  const client = new MemoryClient({ apiKey: 'm0-xxx' });
  await client.add([{ role: "user", content: "I prefer dark mode." }], { userId: "user1" });
  const results = await client.search("What editor?", { filters: { userId: "user1" } });

**Quick Usage (Python Open Source):**
  from mem0 import Memory
  m = Memory()
  m.add("I prefer dark mode and use VS Code.", user_id="user1")
  results = m.search("What editor do they use?", filters={"user_id": "user1"})

Help me integrate Mem0 into my project. Start by asking what I'm building,
what language/framework I'm using, and whether I want managed or self-hosted.