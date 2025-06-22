from typing import List, Dict, Any, Optional, Union
from enum import Enum
from dataclasses import dataclass
import logging
from src.llms.llm import get_llm_by_type

logger = logging.getLogger(__name__)


class QueryStrategy(Enum):
    """
    Enumeration of available query processing strategies.

    Strategies:
        DIRECT: Use the query exactly as provided without modifications
        PARAPHRASE: Generate semantically equivalent variations of the query
        EXPAND: Add relevant context and keywords to the query
    """

    DIRECT = "direct"
    PARAPHRASE = "paraphrase"
    EXPAND = "expand"
    LITESENSE = "litesense"


@dataclass
class ToolDescription:
    """
    Configuration class for tool-specific query processing requirements.

    Attributes:
        name: Identifier for the tool
        query_strategy: Strategy to use for processing queries
        max_variations: Maximum number of query variations to generate

    Example:
        ```python
        desc = ToolDescription(
            name="search_tool",
            query_strategy=QueryStrategy.PARAPHRASE,
            max_variations=3
        )
        ```
    """

    name: str
    query_strategy: QueryStrategy
    max_variations: int = 3


class QueryProcessingError(Exception):
    """
    Exception raised for errors during query processing.

    This can occur due to:
    - Empty or invalid queries
    - LLM processing failures
    - Invalid query variations
    """

    pass


class QueryProcessor:
    """
    Processes search queries using various strategies to improve search results.

    This class handles:
    - Query validation and cleaning
    - Strategy-based query transformation
    - Error handling and recovery
    - Result validation

    Attributes:
        llm: Language model instance for query processing

    Example:
        ```python
        processor = QueryProcessor("basic")
        results = await processor.process_query(
            "search query",
            ToolDescription(name="tool", strategy=QueryStrategy.PARAPHRASE)
        )
        ```
    """

    def __init__(self, llm_type: str = "basic"):
        """
        Initialize QueryProcessor with specified LLM.

        Args:
            llm_type: Type of language model to use for processing
        """
        self.llm = get_llm_by_type(llm_type)

    async def process_query(
        self, query: str, tool_description: ToolDescription
    ) -> List[str]:
        """
        Process a search query based on the specified strategy.

        This method:
        1. Validates the input query
        2. Applies the specified processing strategy
        3. Validates and cleans the results
        4. Ensures the original query is included

        Args:
            query: The original search query
            tool_description: Tool requirements and processing strategy

        Returns:
            List of processed search queries

        Raises:
            QueryProcessingError: If query processing fails

        Example:
            ```python
            queries = await processor.process_query(
                "search query",
                ToolDescription(name="tool", strategy=QueryStrategy.PARAPHRASE)
            )
            ```
        """
        try:
            if not query.strip():
                raise QueryProcessingError("Empty query provided")

            if tool_description.query_strategy == QueryStrategy.DIRECT:
                return [query]

            prompt = self._get_strategy_prompt(query, tool_description)

            try:
                response = await self.llm.ainvoke(prompt)
                if not response or not response.content:
                    logger.warning(f"Empty response from LLM for query: {query}")
                    return [query]
            except Exception as e:
                logger.error(f"LLM processing failed: {str(e)}")
                return [query]

            # Parse and validate queries
            queries = self._parse_response(response.content)
            queries = self._validate_queries(queries, query)

            # Ensure original query is included first
            if query not in queries:
                queries.insert(0, query)

            # Now limit variations (after adding original query)
            if len(queries) > tool_description.max_variations:
                # Keep original query and the first N-1 variations
                queries = queries[: tool_description.max_variations]

            return queries

        except Exception as e:
            raise QueryProcessingError(f"Failed to process query: {str(e)}")

    def _validate_queries(self, queries: List[str], original_query: str) -> List[str]:
        """
        Validate and clean the generated queries.

        Validation rules:
        - Non-empty strings
        - Minimum length of 3 characters
        - Proper string formatting

        Args:
            queries: List of generated queries
            original_query: The original query for fallback

        Returns:
            List of validated queries
        """
        valid_queries = []
        for q in queries:
            q = q.strip()
            if q and len(q) >= 3:
                valid_queries.append(q)

        return valid_queries if valid_queries else [original_query]

    def _get_strategy_prompt(
        self, query: str, tool_description: ToolDescription
    ) -> str:
        """
        Get the appropriate prompt for the search query strategy.

        Each strategy has a specific prompt template that guides the LLM
        in generating appropriate query variations.

        Args:
            query: Original search query
            tool_description: Tool configuration

        Returns:
            Formatted prompt string for the LLM
        """
        base_prompt = f"Original search query: {query}\n\n"

        if tool_description.query_strategy == QueryStrategy.PARAPHRASE:
            return (
                base_prompt
                + f"""
                    Generate {tool_description.max_variations - 1} alternative ways to express this search query while preserving its exact meaning.
                    Each variation should:
                    1. Keep the similar intent and meaning
                    2. Use different wording or phrasing that people would use to refer to the same thing
                    3. Be clear and specific
                    4. Be suitable for a search engine

                    Format each variation on a new line starting with '- '.
                    Do not include any explanations or reasoning, just the variations.
                    """
            )

        elif tool_description.query_strategy == QueryStrategy.EXPAND:
            return (
                base_prompt
                + f"""
                    Generate {tool_description.max_variations - 1} expanded versions of this search query by:
                    1. Adding relevant technical terms or synonyms
                    2. Including related concepts
                    3. Being more specific or detailed
                    4. Using domain-specific terminology

                    Format each expanded query on a new line starting with '- '.
                    Do not include any explanations or reasoning, just the expanded queries.
                    """
            )

        elif tool_description.query_strategy == QueryStrategy.LITESENSE:
            return (
                base_prompt
                + f"""
                    Generate {tool_description.max_variations - 1} alternative ways to express the biomedical search query below while keeping its meaning unchanged.

                    Guidelines  
                    1. Preserve every biomedical fact, hypothesis, or observation.  
                    2. Rephrase using wording a biomedical scientist would write in an abstract or full text.  
                    3. Ensure each version is clear, specific, and context-rich for sentence- or paragraph-level search.  

                    Format each expanded query on a new line starting with '- '.
                    Do not include any explanations or reasoning, just the expanded queries.
                    """
            )

        return base_prompt

    def _parse_response(self, response: str) -> List[str]:
        """
        Parse the LLM response into a list of search queries.

        Expected format:
        - Query variation 1
        - Query variation 2
        ...

        Args:
            response: Raw response from the LLM

        Returns:
            List of parsed query strings
        """
        queries = []

        for line in response.split("\n"):
            line = line.strip()
            if line.startswith("- "):
                query = line[2:].strip()
                if query:
                    queries.append(query)

        return queries
