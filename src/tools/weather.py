# The project is built upon Bytedance MedDR
# SPDX-License-Identifier: MIT

import logging
from typing import Annotated

from langchain_core.tools import tool
from .decorators import log_io

from src.crawler import Crawler

logger = logging.getLogger(__name__)


@tool
@log_io
def weather_tool(
    city: Annotated[str, "The name of the city to get weather information for."]
) -> str:
    """Use this to crawl a url and get a readable content in markdown format."""
    return {"info" : f"The weather in the {city} is always sunny. 12345678"}
    
# if __name__ == "__main__":
#     print(crawl_tool.invoke("url"))
