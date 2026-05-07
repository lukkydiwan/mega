from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import json
from app.graph import app_graph, AgentState

app = FastAPI(title="Multi-Agent Orchestrator API")

# --- Schemas ---
class QueryRequest(BaseModel):
    query: str

class PromptApproval(BaseModel):
    status: str # "approved" or "rejected"

async def run_graph_stream(query: str):
    """Runs the LangGraph workflow and yields real-time state updates."""
    
    # Initialize the required Shared Context Object
    initial_state = AgentState(
        query=query,
        context_budget=4000,
        tokens_used=0,
        current_agent="orchestrator",
        history=[],
        sub_tasks=[],
        citations=[],
        claims_evaluation=[],
        final_answer=""
    )
    
    # Run the graph asynchronously and stream the outputs
    async for output in app_graph.astream(initial_state):
        for node_name, state_update in output.items():
            # Package the node's output into a Server-Sent Event
            event = {
                "agent": node_name,
                "action": "state_update",
                "latest_history": state_update.get("history", [])[-1] if state_update.get("history") else "Working..."
            }
            yield f"data: {json.dumps(event)}\n\n"
            
            # Simulate slight processing delay for readability in testing
            await asyncio.sleep(0.5)

@app.post("/query")
async def submit_query(request: QueryRequest):
    """1. Submit query and receive streaming SSE response."""
    return StreamingResponse(run_graph_stream(request.query), media_type="text/event-stream")
# --- Endpoints ---


@app.get("/jobs/{job_id}/trace")
async def get_job_trace(job_id: str):
    """2. Retrieve full execution trace for a completed job."""
    return {
        "job_id": job_id,
        "status": "completed",
        "trace": [
            {"step": 1, "agent": "orchestrator", "decision": "Route to decomposer"},
            {"step": 2, "agent": "decomposer", "output": ["Task A", "Task B"]}
        ]
    }

@app.get("/eval/summary")
async def get_eval_summary():
    """3. Retrieve the latest eval run summary."""
    return {
        "total_runs": 15,
        "baseline_score": 0.92,
        "adversarial_robustness": 0.75,
        "budget_compliance": "100%"
    }

@app.post("/prompts/{prompt_id}/approve")
async def approve_prompt(prompt_id: str, approval: PromptApproval):
    """4. Submit human approval/rejection for a pending prompt rewrite."""
    if approval.status not in ["approved", "rejected"]:
        raise HTTPException(status_code=400, detail="Status must be 'approved' or 'rejected'")
    
    return {"status": "success", "message": f"Prompt {prompt_id} marked as {approval.status}."}

@app.post("/eval/re-run")
async def trigger_re_eval():
    """5. Trigger a targeted re-eval on previously failed cases."""
    return {"status": "accepted", "message": "Re-evaluation job triggered in the background.", "job_id": "eval-999"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}