# Custom Format Examples

This document shows how to use the new custom format feature that allows users to specify their own requirements for report formatting.

## Command Line Usage

### Basic Custom Format
```bash
python main.py "What are the benefits of Python?" --output_format "Focus on technical details and include code examples"
```

### Academic Style Report
```bash
python main.py "Research quantum computing applications" --output_format "Write in academic style with detailed methodology section, include mathematical formulas where relevant, and provide comprehensive literature review"
```

### Executive Summary Style
```bash
python main.py "Market analysis of electric vehicles" --output_format "Create an executive summary with bullet points, include key metrics and charts, focus on business implications and market trends"
```

### Technical Documentation Style
```bash
python main.py "How to implement machine learning models" --output_format "Write as technical documentation with step-by-step instructions, include code snippets, error handling tips, and best practices"
```

## Python API Usage

```python
import asyncio
from src.workflow import run_agent_workflow_async

async def example_custom_report():
    result = await run_agent_workflow_async(
        user_input="What are the latest developments in AI?",
        output_format="Provide a comprehensive analysis with pros and cons, include recent developments from 2024, and focus on practical applications",
        max_plan_iterations=1,
        max_step_num=3
    )
    
    print(result.get("final_report", "No report generated"))

# Run the example
asyncio.run(example_custom_report())
```

## Example Custom Requirements

### For Technical Reports
- "Focus on technical implementation details"
- "Include code examples and architecture diagrams"
- "Provide step-by-step instructions"
- "Compare different approaches and technologies"

### For Business Reports
- "Create an executive summary format"
- "Include market analysis and competitive landscape"
- "Focus on ROI and business impact"
- "Provide actionable recommendations"

### For Academic Reports
- "Write in academic style with proper citations"
- "Include methodology and research design"
- "Provide comprehensive literature review"
- "Discuss limitations and future research directions"

### For Creative Reports
- "Use engaging storytelling approach"
- "Include visual descriptions and metaphors"
- "Focus on user experience and human impact"
- "Provide inspiring conclusions and next steps"

## How It Works

1. **Simple Detection**: If `output_format` is not "long-report" or "short-report", it's treated as custom requirements
2. **Template Rendering**: The system uses Jinja2 to render the `custom_reporter.md` template
3. **Dynamic Prompt Generation**: User requirements are injected into the template
4. **Flexible Structure**: The AI adapts the report structure based on the requirements
5. **Quality Maintenance**: Professional standards and proper citations are maintained

## Benefits

- **Simplicity**: No additional parameters needed
- **Flexibility**: Users can specify exactly what they need
- **Consistency**: Maintains professional quality standards
- **Adaptability**: Works for various use cases and industries
- **Efficiency**: No need to create new prompt templates for each use case 