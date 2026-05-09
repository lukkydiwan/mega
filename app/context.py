import tiktoken
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from app.state import AgentState

def get_token_count(text: str) -> int:
    """Uses cl100k_base as a fast, offline proxy for token consumption."""
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

def enforce_context_budget(state: AgentState) -> dict:
    history_text = "\n".join(state.get("history", []))
    current_tokens = get_token_count(history_text)
    
    budget = state.get("context_budget", 4000)
    
    if current_tokens <= budget:
        return {"tokens_used": current_tokens} 
        
    # Over budget! Compress the conversational history using Gemini
    llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", temperature=0)
    compression_prompt = f"""
    Condense the following system history. 
    CRITICAL INSTRUCTION: Keep all structured data, tool results, and scores EXACTLY as they are. 
    Only compress conversational filler.
    
    History:
    {history_text}
    """
    
    compressed_text = llm.invoke(compression_prompt).content
    
    return {
        "history": [compressed_text], 
        "tokens_used": get_token_count(compressed_text)
    }