from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv
import asyncio
import sys
import json

# Add the root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.workflow import run_agent_workflow_async  # <-- must be updated to async generator

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
    query: str = Field(
        ..., min_length=1, max_length=1000, description="The user's question or query"
    )
    max_plan_iterations: int = Field(
        default=1, description="Maximum number of plan iterations"
    )
    max_step_num: int = Field(
        default=3, description="Maximum number of steps in a plan"
    )

@app.post("/api/chat")
async def chat(request: ChatRequest):
    async def event_stream():
        try:
            print(f"[BACKEND] Starting workflow for query: {request.query}")
            # Yield results progressively from run_agent_workflow_async
            async for result in run_agent_workflow_async(
                user_input=request.query,
                debug=False,
                max_plan_iterations=request.max_plan_iterations,
                max_step_num=request.max_step_num
            ):
                print(f"[BACKEND] Yielding result: {result}")
                yield f"data: {json.dumps(result)}\n\n"
            
            print(f"[BACKEND] Workflow completed")

        except Exception as e:
            print(f"[BACKEND] Error in workflow: {str(e)}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}
