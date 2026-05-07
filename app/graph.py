from typing import TypedDict, List, Dict, Any, Annotated
import operator
from langgraph.graph import StateGraph, END

# --- 1. The Shared Context Object ---
class AgentState(TypedDict):
    query: str
    context_budget: int
    tokens_used: int
    
    # State tracking
    current_agent: str
    history: Annotated[List[str], operator.add] 
    
    # Required Agent Outputs
    sub_tasks: List[Dict[str, Any]]
    citations: List[str]
    claims_evaluation: List[Dict[str, Any]]
    final_answer: str

# --- 2. STUB AGENTS ---
def orchestrator_node(state: AgentState):
    # Temporary mock logic to test the loop without getting stuck
    # It routes to decomposer first, then to synthesis on the next pass
    history = state.get("history", [])
    if not history:
        return {"current_agent": "decomposer", "history": ["Orchestrator: Routing to Decomposer"]}
    else:
        return {"current_agent": "synthesis", "history": ["Orchestrator: Routing to Synthesis"]}

def decomposer_node(state: AgentState):
    tasks = [{"task_id": 1, "description": "Break down query", "depends_on": []}]
    return {"sub_tasks": tasks, "history": ["Decomposer: Split into 1 task"]}

def rag_node(state: AgentState):
    return {"citations": ["chunk_123"], "history": ["RAG: Found 1 relevant chunk"]}

def critique_node(state: AgentState):
    evaluation = [{"claim": "example claim", "confidence": 0.9, "disagree": False}]
    return {"claims_evaluation": evaluation, "history": ["Critique: Evaluated claims"]}

def synthesis_node(state: AgentState):
    return {"final_answer": "This is the merged final answer.", "history": ["Synthesis: Generated final answer"]}

# --- 3. DYNAMIC ROUTER ---
def router(state: AgentState):
    """The Orchestrator mediates all handoffs."""
    next_agent = state.get("current_agent")
    
    if next_agent == "decomposer":
        return "decomposer_node"
    elif next_agent == "rag":
        return "rag_node"
    elif next_agent == "critique":
        return "critique_node"
    elif next_agent == "synthesis":
        return "synthesis_node"
    else:
        return END

# --- 4. BUILD THE GRAPH ---
workflow = StateGraph(AgentState)

# Add all nodes
workflow.add_node("orchestrator", orchestrator_node)
workflow.add_node("decomposer_node", decomposer_node)
workflow.add_node("rag_node", rag_node)
workflow.add_node("critique_node", critique_node)
workflow.add_node("synthesis_node", synthesis_node)

# Entry point is always the orchestrator
workflow.set_entry_point("orchestrator")

# Orchestrator dynamically routes to the next sub-agent
workflow.add_conditional_edges("orchestrator", router)

# Sub-agents route back to the orchestrator after their task
workflow.add_edge("decomposer_node", "orchestrator")
workflow.add_edge("rag_node", "orchestrator")
workflow.add_edge("critique_node", "orchestrator")

# Synthesis is the final step
workflow.add_edge("synthesis_node", END) 

# Compile it into a runnable application
app_graph = workflow.compile()