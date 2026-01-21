# Agentic Stock Analysis System: Development Roadmap

This document outlines the strategic roadmap for transforming the current `tickzen2` analysis system into a sophisticated **Agentic System** similar to the one we analyzed (Main Agent + Specialized Executioners).

## 1. System Architecture Design

The goal is to move from a **Linear Execution Model** (User -> Script -> Output) to an **Agentic Model** (User -> Planner -> Agents -> Tools -> Insight).

### Core Components to Build
1.  **The Orchestrator (Main Agent)**:
    *   **Role**: Acts as the "Project Manager". It doesn't do the math; it plans the work.
    *   **Function**: Receives user queries (e.g., "Impact of GST on Maruti"), breaks them into sub-tasks, and delegates to sub-agents.
2.  **Specialized Sub-Agents (The Executioners)**:
    *   **Fundamental Agent**: Wrapper around `fundamental_analysis.py`. Interprets CSVs and ratios.
    *   **Technical Agent**: Wrapper around `technical_analysis.py`. Looks for patterns (not just indicators).
    *   **News/Sentiment Agent**: Wrapper around `sentiment_analysis.py`. Correlates news to price.
3.  **The "Context Engine" (Memory)**:
    *   **Role**: Stores "Enriched Context" (parsed data, previous results).
    *   **Tech**: Vector Database (like ChromaDB or FAISS) to store news embeddings and financial documents.

---

## 2. Development Roadmap & Timeline

**Estimated Total Time: 8-12 Weeks (for a functional MVP)**

### Phase 1: Toolification of Existing Scripts (Weeks 1-2)
**Goal**: Make your existing Python scripts "readable" by an AI.
*   **Task**: Create a `tools/` directory.
*   **Action**: Wrap functions in `technical_analysis.py` and `fundamental_analysis.py` into defined "Tool" classes with standardized JSON inputs/outputs.
*   **Example**: Instead of calling `calculate_rsi(data)`, create a tool `GetTechnicalIndicator(symbol, indicator="RSI")` that returns a JSON summary.
*   **Deliverable**: A library of callable tools that an LLM can invoke.

### Phase 2: The "Brain" & State Management (Weeks 3-5)
**Goal**: Build the Orchestrator that can decide which tool to use.
*   **Task**: Implement the `MainAgent` logic using a framework like **LangGraph** or **CrewAI** (Python based).
*   **Action**:
    *   Design the "Query Plan" prompt: Teach the LLM to break down complex questions.
    *   Implement "State": The agent needs to remember what step 1 returned to do step 2.
    *   *Differentiation*: Unlike the logs (JS-based), we will use Python to leverage your existing backend.
*   **Deliverable**: A script where you type a question, and it autonomously calls the correct tools from Phase 1.

### Phase 3: The Specialized Agents (Weeks 6-8)
**Goal**: Build the "Executioners" that add intelligence like the `PriceMovementExecutioner`.
*   **Task 1 (Pattern Executioner)**: Connect the `ChartPatternAnalyzer` logic. Instead of just calculating "Ascending Triangle", feed the chart data to a Vision-capable model (like GPT-4o or Claude 3.5 Sonnet) to *see* the chart.
*   **Task 2 (Sentiment Executioner)**: Implement the "News-to-Price" correlation logic. Fetch 30 days of news, fetch 30 days of price, and ask the LLM to find correlations.
*   **Deliverable**: Two robust sub-agents that provide "Insight" not just "Data".

### Phase 4: Integration & Optimization (Weeks 9-12)
**Goal**: The "Enriched Context" Loop.
*   **Task**: Build the Feedback Loop.
    *   Agent generates a hypothesis -> Checks ground truth data -> Refines hypothesis.
*   **Action**: Create a centralized context object that passes between agents (similar to the `enrichedContext` seen in logs).
*   **UI Integration**: Build a simple Chat UI (Streamlit or React) to visualize the "Thinking Process" (e.g., "Agent is analyzing charts...", "Agent is reading news...").

---

## 3. Tech Stack Recommendations

Since your current workspace is Python-heavy (`tickzen2`), we should stick to a **Python-First** stack to reuse your logic:

*   **Orchestration Framework**: **LangGraph** (Best for controlled flows) or **CrewAI** (Easier for multi-agent teams).
*   **LLM Provider**: **OpenAI API** (GPT-4o) or **Anthropic** (Claude 3.5 Sonnet) for the reasoning capability.
*   **Local LLM Option**: **Ollama** (Llama 3) for privacy/cost, though less "smart" for complex reasoning.
*   **Database**: **SQLite** (for caching) + **ChromaDB** (for document search).
*   **Frontend**: **Streamlit** (for rapid internal tools) or **React** (for production-grade UI).

## 4. Resource Estimates

*   **Developer C**: 1 Senior Python Dev (System Architect).
*   **Compute Costs**:
    *   API Costs (OpenAI/Anthropic): ~$50 - $100 / month during dev.
    *   Hosting: Standard Cloud VM (runs comfortably on 8GB RAM).

## 5. Comparison: Current vs. New System

| Feature | Current `tickzen2` Scripts | Proposed Agentic System |
| :--- | :--- | :--- |
| **Logic** | Hard-coded rules (`if RSI > 70`) | Cognitive Reasoning (`RSI > 70 BUT strong news momentum`) |
| **Input** | Structured Data only | Natural Language ("How is GST affecting margins?") |
| **Workflow** | Linear (Script A -> Script B) | Dynamic (Plan -> Execute -> Retry if needed) |
| **Output** | Raw Data / CSVs | Narrative Reports / Strategic Insights |

**Conclusion**: You have 60% of the raw materials ("Tools") already built in `analysis_scripts`. The work is primarily building the "Brain" to wield these tools effectively.
