from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import asyncio
from src.workflow import run_agent_workflow_async
import logging
import json
from langchain_core.messages import HumanMessage, AIMessage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="The user's question or query")

class ChatResponse(BaseModel):
    plan: Optional[Dict[str, Any]] = None
    report: Optional[str] = None
    intermediate_steps: Optional[List[Dict[str, Any]]] = None

def serialize_message(message):
    """Helper function to serialize a message object to a dict."""
    if isinstance(message, (HumanMessage, AIMessage)):
        return {
            "role": message.type,
            "content": message.content,
            "name": getattr(message, "name", None)
        }
    elif isinstance(message, dict):
        return message
    else:
        return {"role": "system", "content": str(message)}

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        logger.info(f"Received query: {request.query}")
        
        # Run the agent workflow with minimal recursion
        result = await run_agent_workflow_async(
            user_input=request.query,
            debug=True,
            max_plan_iterations=1,  # Keep this at 1 to prevent recursion
            max_step_num=2  # Reduce steps to prevent recursion
        )
        
        # Process the result
        intermediate_steps = []
        final_response = "No response generated"
        
        if isinstance(result, dict):
            # Log the state for debugging
            logger.info(f"Processing result: {json.dumps(result, indent=2)}")
            
            # Extract messages
            if "messages" in result:
                messages = result["messages"]
                for message in messages:
                    serialized_message = serialize_message(message)
                    intermediate_steps.append({
                        "type": serialized_message["role"],
                        "content": serialized_message["content"],
                        "timestamp": result.get("timestamp", "")
                    })
                
                # Get the last message as the final response
                if messages:
                    last_message = messages[-1]
                    if isinstance(last_message, (HumanMessage, AIMessage)):
                        final_response = last_message.content
                    elif isinstance(last_message, dict):
                        final_response = last_message.get("content", "No content in message")
                    else:
                        final_response = str(last_message)
            
            # Extract plan if available
            if "current_plan" in result:
                plan = result["current_plan"]
                if isinstance(plan, dict):
                    intermediate_steps.append({
                        "type": "plan",
                        "content": plan,
                        "timestamp": result.get("timestamp", "")
                    })
                else:
                    try:
                        plan_dict = json.loads(plan)
                        intermediate_steps.append({
                            "type": "plan",
                            "content": plan_dict,
                            "timestamp": result.get("timestamp", "")
                        })
                    except json.JSONDecodeError:
                        logger.warning(f"Could not parse plan as JSON: {plan}")
        
        # Format the response
        return ChatResponse(
            plan={
                "steps": [
                    "Analyze the query",
                    "Research relevant information"
                ],
                "summary": f"Research plan for: {request.query}"
            },
            report=final_response,
            intermediate_steps=intermediate_steps
        )
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"} 