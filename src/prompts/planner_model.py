from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class StepType(str, Enum):
    """Type of step in the plan."""

    RESEARCH = "research"
    PROCESSING = "processing"


class Step(BaseModel):
    """Step in the plan."""

    title: str = Field(description="Title of the step")
    description: str = Field(description="Description of the step")
    step_type: StepType = Field(description="Type of the step")
    execution_res: Optional[str] = Field(
        default=None, description="Execution result of the step"
    )


class Plan(BaseModel):
    """Plan for the research task."""

    has_enough_context: bool = Field(
        description="Whether the plan has enough context to proceed"
    )
    thought: str = Field(description="Thought process behind the plan")
    title: str = Field(description="Title of the plan")
    steps: List[Step] = Field(description="Steps in the plan")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "has_enough_context": False,
                    "thought": (
                        "To understand the current market trends in AI, we need to gather comprehensive information."
                    ),
                    "title": "AI Market Research Plan",
                    "steps": [
                        {
                            "title": "Current AI Market Analysis",
                            "description": (
                                "Collect data on market size, growth rates, major players, and investment trends in AI sector."
                            ),
                            "step_type": "research",
                        }
                    ],
                }
            ]
        }
