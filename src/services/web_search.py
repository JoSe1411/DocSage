import os
import requests
from langchain.tools import Tool

def get_web_search_tool():
    """Returns a Serper web search tool as a LangChain Tool instance."""
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        raise ValueError("SERPER_API_KEY environment variable not set.")
    endpoint = "https://google.serper.dev/search"

    def serper_search(query: str):
        try:
            headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
            data = {"q": query}
            response = requests.post(endpoint, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            results = response.json()
            organic = results.get("organic", [])
            if organic:
                return '\n'.join(f"{r.get('title')}: {r.get('link')}\n{r.get('snippet', r.get('description', ''))}" for r in organic[:3])
            return "No results found."
        except Exception as e:
            return f"Serper Search error: {e}"

    return Tool(
        name="WebSearch",
        func=serper_search,
        description="Searches the web using the Serper API (Google results). Use this for up-to-date information."
    ) 