from typing import TypedDict, List, Dict, Any, Annotated
import operator

class AgentState(TypedDict):
    query: str
    context_budget: int
    tokens_used: int
    current_agent: str
    history: Annotated[List[str], operator.add] 
    sub_tasks: List[Dict[str, Any]]
    citations: List[str]
    claims_evaluation: List[Dict[str, Any]]
    final_answer: str
    current_phase: str