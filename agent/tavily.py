import os
from dotenv import load_dotenv
from langchain_community.tools.tavily_search import TavilySearchResults
# Load the .env file
load_dotenv()

tavily_api_key = os.getenv("TAVILY_API_KEY")


def search_tavily_query(query: str, max_results: int = 3):
    """
    Searches using TavilySearchResults tool with a given URL or query.

    Args:
        url (str): The query or URL to search.
        max_results (int): Number of search results to return.

    Returns:
        list: A list of search results.
    """
    search = TavilySearchResults(max_results=max_results)
    search_results = search.invoke(query)
    return search_results

print(search_tavily_query("Who is Xe according to https://christine.website?"))