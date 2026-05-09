import os
import json
import time
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI

# Local imports
from app.state import AgentState
from app.context import enforce_context_budget
from app.tools import web_search_tool, code_execution_sandbox, sql_lookup_tool

# --- 1. LLM Configuration (2026 Workhorse) ---
# Gemini 3.1 Flash-Lite is optimized for rapid agentic reasoning
llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", temperature=0)

# --- 2. Structured Output Schemas ---

class SubTask(BaseModel):
    task_id: int = Field(description="Unique task ID")
    description: str = Field(description="Goal of the sub-task")
    depends_on: List[int] = Field(description="Prerequisite task IDs")

class DecomposerOutput(BaseModel):
    sub_tasks: List[SubTask]

class RAGOutput(BaseModel):
    citations: List[str] = Field(description="Source links or IDs")
    answer_snippet: str = Field(description="Reasoning based on data")

class ClaimEvaluation(BaseModel):
    claim: str
    confidence: float
    disagree: bool
    reason: str

class CritiqueOutput(BaseModel):
    evaluations: List[ClaimEvaluation]

class SynthesisOutput(BaseModel):
    final_answer: str

# --- 3. Robust API Helper ---

def call_llm_with_retry(agent_llm, prompt, max_retries=3):
    """
    Ensures stability on the 2026 Free Tier (15 RPM).
    Implements a 4-second forced gap and exponential backoff.
    """
    for attempt in range(max_retries):
        try:
            # Respect the rate window
            time.sleep(4) 
            return agent_llm.invoke(prompt)
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                # Exponential backoff on rate limit
                wait_time = (attempt + 1) * 10
                time.sleep(wait_time)
                continue
            raise e
    raise Exception("API Quota Error: Max retries exceeded.")

# --- 4. Agent Nodes ---

def orchestrator_node(state: AgentState):
    # Default to "start" only if phase is missing or empty
    phase = state.get("current_phase") or "start"
    
    if phase == "start":
        next_agent = "decomposer"
        reasoning = "Initiating decomposition into sub-tasks."
    elif phase == "decomposed":
        next_agent = "rag"
        reasoning = "Sub-tasks defined; moving to RAG retrieval."
    elif phase == "retrieved":
        next_agent = "critique"
        reasoning = "Draft generated; moving to factual critique."
    elif phase == "critiqued":
        next_agent = "synthesis"
        reasoning = "Critique complete; synthesizing final output."
    elif phase == "synthesized":
        # This is the crucial terminal state
        next_agent = "end"
        reasoning = "Process complete. Terminating graph."
    else:
        # Emergency stop to prevent any loops
        next_agent = "end"
        reasoning = "Graph in terminal state."

    return {
        "current_agent": next_agent,
        "history": [f"Orchestrator: {reasoning}"]
    }

def decomposer_node(state: AgentState):
    budget_update = enforce_context_budget(state)
    agent_llm = llm.with_structured_output(DecomposerOutput)
    
    prompt = f"Break this query into dependent sub-tasks: {state['query']}"
    result = call_llm_with_retry(agent_llm, prompt)
    
    tasks_dict = [t.model_dump() for t in result.sub_tasks]
    return {
        "sub_tasks": tasks_dict,
        "current_phase": "decomposed",
        "history": [f"Decomposer: Created {len(tasks_dict)} tasks."],
        "tokens_used": budget_update.get("tokens_used", state["tokens_used"])
    }

def rag_node(state: AgentState):
    budget_update = enforce_context_budget(state)
    agent_llm = llm.with_structured_output(RAGOutput)
    
    # Real tool integration
    context = web_search_tool(state["query"])
    
    prompt = f"Using this context: {context}\n\nResolve the query: {state['query']}"
    result = call_llm_with_retry(agent_llm, prompt)
    
    return {
        "citations": result.citations,
        "current_phase": "retrieved",
        "history": [f"RAG: Reasoning complete with {len(result.citations)} sources."],
        "tokens_used": budget_update.get("tokens_used", state["tokens_used"])
    }

def critique_node(state: AgentState):
    budget_update = enforce_context_budget(state)
    agent_llm = llm.with_structured_output(CritiqueOutput)
    
    prompt = f"Audit the following history for contradictions: {state['history']}"
    result = call_llm_with_retry(agent_llm, prompt)
    
    evals = [e.model_dump() for e in result.evaluations]
    return {
        "claims_evaluation": evals,
        "current_phase": "critiqued",
        "history": [f"Critique: Verified {len(evals)} distinct claims."],
        "tokens_used": budget_update.get("tokens_used", state["tokens_used"])
    }

def synthesis_node(state: AgentState):
    budget_update = enforce_context_budget(state)
    agent_llm = llm.with_structured_output(SynthesisOutput)
    
    prompt = f"Generate the final authoritative answer: {state['query']}"
    result = call_llm_with_retry(agent_llm, prompt)
    
    return {
        "final_answer": result.final_answer,
        "current_phase": "synthesized",
        "history": ["Synthesis: Final authoritative response generated."],
        "tokens_used": budget_update.get("tokens_used", state["tokens_used"])
    }

# --- 5. Robust Routing Logic ---

def router(state: AgentState):
    target = state.get("current_agent")
    
    mapping = {
        "decomposer": "decomposer_node",
        "rag": "rag_node",
        "critique": "critique_node",
        "synthesis": "synthesis_node"
    }
    
    # If target is 'end' or not in our map, we MUST return END
    # This tells LangGraph to stop the astream generator entirely.
    if target == "end" or target not in mapping:
        return END
        
    return mapping.get(target)

# --- 6. Graph Construction ---

workflow = StateGraph(AgentState)

# Nodes
workflow.add_node("orchestrator", orchestrator_node)
workflow.add_node("decomposer_node", decomposer_node)
workflow.add_node("rag_node", rag_node)
workflow.add_node("critique_node", critique_node)
workflow.add_node("synthesis_node", synthesis_node)

# Edges
workflow.set_entry_point("orchestrator")
workflow.add_conditional_edges("orchestrator", router)

# Feedback loops to the Orchestrator for phase checking
workflow.add_edge("decomposer_node", "orchestrator")
workflow.add_edge("rag_node", "orchestrator")
workflow.add_edge("critique_node", "orchestrator")
workflow.add_edge("synthesis_node", "orchestrator")

app_graph = workflow.compile()