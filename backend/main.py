from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import os
from dotenv import load_dotenv
from openai import OpenAI
import requests
from bs4 import BeautifulSoup
import json

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

def generate_research_plan(query: str) -> Dict[str, Any]:
    """Generate a research plan based on the query."""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a medical research assistant. Generate a detailed research plan for the given query."},
                {"role": "user", "content": f"Generate a research plan for: {query}"}
            ],
            temperature=0.7,
        )
        plan = response.choices[0].message.content
        return {
            "steps": plan.split("\n"),
            "summary": f"Research plan for: {query}"
        }
    except Exception as e:
        print(f"Error generating research plan: {e}")
        return {
            "steps": ["Analyze the query", "Search relevant medical literature", "Generate comprehensive response"],
            "summary": "Default research plan"
        }

def generate_response(query: str, plan: Dict[str, Any]) -> str:
    """Generate a comprehensive response based on the query and research plan."""
    try:
        # First, get a high-level understanding
        understanding = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a medical research assistant. Provide a comprehensive response based on the query and research plan."},
                {"role": "user", "content": f"Query: {query}\nResearch Plan: {json.dumps(plan)}\n\nProvide a detailed response:"}
            ],
            temperature=0.7,
        )
        
        response = understanding.choices[0].message.content
        
        # Format the response
        formatted_response = f"""Based on your query about "{query}", here's what I found:

{response}

This information is based on current medical research and literature. For specific medical advice, please consult with healthcare professionals."""
        
        return formatted_response
    except Exception as e:
        print(f"Error generating response: {e}")
        return f"I apologize, but I encountered an error while processing your query about {query}. Please try again or rephrase your question."

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Validate the query
        if not request.query or not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        # Generate research plan
        plan = generate_research_plan(request.query)
        
        # Generate response
        report = generate_response(request.query, plan)
        
        return ChatResponse(
            plan=plan,
            report=report
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"} 