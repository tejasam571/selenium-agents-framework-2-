# """
# agents/root_agent.py
# ─────────────────────────────────────────────────────────────────
# Root orchestrator agent – entry point for ADK Web.
# • Model  : Gemini 2.5 Flash
# • Routes incoming test-case requests through:
#     1. codegen_agent  → generates Java Selenium test
#     2. review_agent   → reviews & fixes the test
# • Also handles direct user queries via query_rag (Groq-backed RAG).
# • Crawl is triggered automatically if locators are stale / missing.
# """

# from google.adk.agents import LlmAgent
# from google.adk.models.google_llm import Gemini

# from tools.crawler import crawl_tool
# from tools.rag_csv import build_rag_index_tool, query_rag_tool
# from agents.codegen_agent import codegen_agent
# from agents.review_agent import review_agent

# ROOT_INSTRUCTION = """
# You are the orchestrator of a Java Selenium test-generation pipeline.

# ## Capabilities
# - **RAG Q&A**: Answer questions about test cases by calling `query_rag`.
#   The RAG pipeline uses HuggingFace embeddings + FAISS for retrieval and
#   Groq (llama-3.1-8b-instant) for generating the final answer.
# - **Auto-crawl**: Call `crawl_locators_sync` to discover and extract UI
#   locators from a web application.  The crawler follows internal links
#   automatically (up to 10 pages).
# - **Test generation**: Delegate to `codegen_agent` to produce Java Selenium
#   TestNG tests.
# - **Test review**: Delegate to `review_agent` to verify and fix the tests.

# ## Workflow for each test case
# 1. Ensure the RAG index is built: call `build_rag_index` if needed.
# 2. Ensure locators are available (from session state or via `crawl_locators_sync`).
# 3. Transfer to `codegen_agent` with the test-case details.
# 4. After codegen completes, transfer to `review_agent` for quality checks.
# 5. Report the final outcome to the user.

# ## Direct queries
# If the user asks a question about the test suite (e.g. "What does TC_003 test?"),
# call `query_rag` and return the answer directly — no need to run the full pipeline.

# ## Rules
# - Always be concise in status updates.
# - Surface errors clearly with suggested next steps.
# - Never expose raw stack traces to the user.
# """

# root_agent = LlmAgent(
#     name="root_agent",
#     model=Gemini(model="gemini-2.5-flash"),
#     instruction=ROOT_INSTRUCTION,
#     tools=[
#         build_rag_index_tool,
#         query_rag_tool,
#         crawl_tool,
#     ],
#     sub_agents=[codegen_agent, review_agent],
#     description="Root orchestrator: auto-crawls UI, RAGs CSV test cases, generates & reviews Java Selenium tests.",
# )

# #working code
# """
# agents/root_agent.py
# """

# from google.adk.agents import LlmAgent
# from google.adk.models.google_llm import Gemini

# from tools.crawler import crawl_tool
# from tools.rag_csv import build_rag_index_tool, query_rag_tool
# from agents.codegen_agent import codegen_agent
# from agents.review_agent import review_agent

# ROOT_INSTRUCTION = """
# You are the orchestrator of a Java Selenium test-generation pipeline.

# ## Session state keys available
# - `app_url`          : target application URL
# - `locators`         : crawled UI locators JSON
# - `review_iteration` : current iteration counter (starts at 1, pre-set)
# - `review_feedback`  : issues list for codegen to fix (pre-set to null)
# - `codegen_output`   : written by codegen_agent after generation
# - `review_output`    : written by review_agent after review (JSON string)

# ## MANDATORY workflow — follow every step, no skipping
# STEP 1. Call `build_rag_index` once at the start.
# STEP 2. Call `crawl_locators_sync` if locators are missing.
# STEP 3. Transfer to `codegen_agent`. Wait for it to finish and write `codegen_output`.
# STEP 4. ALWAYS transfer to `review_agent` after codegen. This step is NOT optional.
#         Wait for it to finish and write `review_output`.
# STEP 5. Parse the JSON in `review_output`.
#         - verdict == "PASS"
#             → Report "[Review <N>/5] PASS — test saved." Stop.
#         - verdict == "FAIL" AND (iteration >= 5 OR issues contains "MAX_ITERATIONS_REACHED")
#             → Report "FAILED after <N> iterations. Issues: <list>." Stop.
#         - verdict == "FAIL" AND iteration < 5
#             → a. Store issues as `review_feedback` in session state.
#             → b. Increment `review_iteration` by 1 in session state.
#             → c. Tell user "[Review <N>/5] FAIL — fixing. Issues: <issues>".
#             → d. Transfer to `codegen_agent` again (reads review_feedback, patches code).
#             → e. Transfer to `review_agent` again.
#             → f. Go back to STEP 5.

# ## CRITICAL
# - You MUST transfer to review_agent after EVERY codegen run, no exceptions.
# - Never report [Done] before review_agent has run.
# - Never skip review_agent even if codegen says the file was saved successfully.
# - Hard stop at iteration 5.

# ## Status message format
# [Review <iteration>/5] <PASS|FAIL> — <one line summary>

# ## Direct queries
# If the user asks a question (not a generation task), call `query_rag` directly.

# ## Rules
# - Never expose raw stack traces.
# - Always show iteration progress in status messages.
# """

# root_agent = LlmAgent(
#     name="root_agent",
#     model=Gemini(model="gemini-2.5-flash"),
#     instruction=ROOT_INSTRUCTION,
#     tools=[
#         build_rag_index_tool,
#         query_rag_tool,
#         crawl_tool,
#     ],
#     sub_agents=[codegen_agent, review_agent],
#     description="Orchestrator: generates Java Selenium tests and ALWAYS reviews them, iterating up to 5 times.",
# )
"""
agents/root_agent.py
"""
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini

root_agent = LlmAgent(
    name="root_agent",
    model=Gemini(model="gemini-2.5-flash"),
    instruction="You are a pipeline assistant. For test generation run: python main.py",
    tools=[],
    description="Chat assistant for the Java Selenium pipeline.",
)