# The project is built upon Bytedance MedDR
# SPDX-License-Identifier: MIT

import os
import enum
from dotenv import load_dotenv

load_dotenv()


class SearchEngine(enum.Enum):
    ARXIV = "arxiv"
    TAVILY = "tavily"
    BRAVE_SEARCH = "brave_search"


# Tool configuration
SELECTED_SEARCH_ENGINE = os.getenv("SEARCH_API", SearchEngine.ARXIV.value)
