import json
import time

def web_search_tool(query: str) -> str:
    """
    A web search stub that returns structured results.
    Failure Contract: Returns 'TIMEOUT' or 'EMPTY' if conditions met.
    """
    try:
        # Simulate a search timeout for specific queries to test fallback
        if "timeout" in query.lower():
            time.sleep(2) # Simulate latency
            return "ERROR: Search service timed out."
        
        if not query:
            return "ERROR: Malformed input - query is empty."

        # Mock successful response
        results = [
            {"url": "https://finance.yahoo.com/apple", "relevance": 0.98, "snippet": "Apple stock analysis 2023."},
            {"url": "https://marketwatch.com/msft", "relevance": 0.95, "snippet": "Microsoft performance overview."}
        ]
        return json.dumps(results)
    except Exception as e:
        return f"ERROR: Unexpected search failure - {str(e)}"

def code_execution_sandbox(code: str) -> str:
    """
    Runs Python snippets and returns stdout, stderr, and exit code.
    Failure Contract: Captures exceptions and returns as stderr.
    """
    import sys
    from io import StringIO

    # Very basic 'sandbox' simulation
    if "import os" in code or "rm" in code:
        return json.dumps({"stdout": "", "stderr": "Security Violation: Restricted module.", "exit_code": 1})

    old_stdout = sys.stdout
    redirected_output = sys.stdout = StringIO()
    
    try:
        exec(code)
        stdout = redirected_output.getvalue()
        return json.dumps({"stdout": stdout, "stderr": "", "exit_code": 0})
    except Exception as e:
        return json.dumps({"stdout": "", "stderr": str(e), "exit_code": 1})
    finally:
        sys.stdout = old_stdout

def sql_lookup_tool(nl_query: str) -> str:
    """
    Simulates converting NL to SQL and querying a local DB.
    Failure Contract: Returns 'SQL_ERROR' for malformed logic.
    """
    if "delete" in nl_query.lower() or "drop" in nl_query.lower():
        return "ERROR: SQL_ERROR - Write operations are prohibited."
    
    # Mock data return
    return json.dumps([{"id": 101, "metric": "growth", "value": "48%"}])

def self_reflection_tool(state_history: str) -> str:
    """
    The agent re-reads previous outputs to identify contradictions.
    """
    if not state_history:
        return "ERROR: No history provided for reflection."
    
    return "Reflection: Historical data appears consistent with current reasoning."