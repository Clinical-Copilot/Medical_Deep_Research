from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import os
from dotenv import load_dotenv
import asyncio
import sys
import json

# Add the root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.workflow import run_agent_workflow_async

# Load environment variables
load_dotenv()

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="The user's question or query")
    max_plan_iterations: int = Field(default=1, description="Maximum number of plan iterations")
    max_step_num: int = Field(default=3, description="Maximum number of steps in a plan")

class WorkflowStep(BaseModel):
    type: str
    content: str
    name: Optional[str] = None

class ChatResponse(BaseModel):
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Validate the query
        if not request.query or not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        # Run the agent workflow
        result = await run_agent_workflow_async(
            user_input=request.query,
            debug=False,
            max_plan_iterations=request.max_plan_iterations,
            max_step_num=request.max_step_num
        )
        
        # Process the workflow result
        workflow_steps = []
        final_report = None
        coordinator_response = None
        
        if isinstance(result, dict):
            # Extract messages and convert them to workflow steps
            if "messages" in result:
                for msg in result["messages"]:
                    if isinstance(msg, dict):
                        content = msg.get("content", "")
                        role = msg.get("role", "system")
                        name = msg.get("name", "")
                        
                        # Handle coordinator messages specially - don't convert to workflow steps
                        if name == "coordinator" and content:
                            coordinator_response = content
                            continue
                        
                        if role == "assistant" and content:
                            # This is likely the final report
                            final_report = content
                            workflow_steps.append(WorkflowStep(
                                type="report",
                                content=content,
                                name="reporter"
                            ))
                        elif role == "system" and content:
                            # Determine the type of system message based on content and name
                            if "plan" in content.lower() or name == "planner":
                                workflow_steps.append(WorkflowStep(
                                    type="plan",
                                    content=content,
                                    name="planner"
                                ))
                            elif "research" in content.lower() or name == "researcher":
                                workflow_steps.append(WorkflowStep(
                                    type="info",
                                    content=content,
                                    name="researcher"
                                ))
                            elif "code" in content.lower() or name == "coder":
                                workflow_steps.append(WorkflowStep(
                                    type="info",
                                    content=content,
                                    name="coder"
                                ))
                            else:
                                workflow_steps.append(WorkflowStep(
                                    type="info",
                                    content=content,
                                    name=name or "system"
                                ))
            
            # Extract plan if available
            plan = None
            if "current_plan" in result:
                plan = result["current_plan"]
                if isinstance(plan, dict):
                    # Format the plan nicely
                    formatted_plan = "Research Plan:\n\n"
                    if "title" in plan:
                        formatted_plan += f"Title: {plan['title']}\n\n"
                    if "thought" in plan:
                        formatted_plan += f"Approach: {plan['thought']}\n\n"
                    if "steps" in plan:
                        formatted_plan += "Steps:\n"
                        for i, step in enumerate(plan["steps"], 1):
                            formatted_plan += f"{i}. {step.get('title', '')}\n"
                            if step.get("description"):
                                formatted_plan += f"   {step['description']}\n"
                    
                    workflow_steps.append(WorkflowStep(
                        type="plan",
                        content=formatted_plan,
                        name="planner"
                    ))
        
        return ChatResponse(
            status="success",
            message="Research completed successfully",
            data={
                "workflow_steps": [step.dict() for step in workflow_steps],
                "plan": plan,
                "report": final_report,
                "coordinator_response": coordinator_response or result.get("coordinator_response", None)
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"} 