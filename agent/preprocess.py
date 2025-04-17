from langchain_community.tools.tavily_search import TavilySearchResults
import os

tavily = TavilySearchResults(api_key=os.getenv("TAVILY_API_KEY"))

def enrich_profile_json(llm, profile_json: dict) -> dict:
    # Create a prompt to clean and extract fields
    prompt = f"""
You are a data extractor. Given this JSON object:

{profile_json}

Perform the following tasks:

1. Extract the full, clean name from the `name` field (e.g., handle cases like "RohanM" → "Rohan M", or "Eric Doty (Superpath)" → "Eric Doty").
2. Extract all company names mentioned in the `intro` or anywhere in the input. Include all of them in a list.
3. Extract any **additional links** from the input (e.g company's link, etc), but exclude the ones in the `social_profile and image` list.

Return the following updated JSON format only no other captions at all, preserving all the original keys:

{{
  "name": "<Cleaned Full Name>",
  "company_names": [<list of companies or null>],
  "links": [<list of links or null>],
  "original_keys": {profile_json}
}}
If no companies or extra links are found, return None for those fields.
"""

    # Invoke the LLM
    response = llm.invoke(prompt)

    # Parse the content from the response (string -> dict)
    import json
    try:
        result_json = json.loads(response.content)
    except json.JSONDecodeError:
        print("⚠️ LLM returned non-JSON content. Raw output:")
        print(response.content)
        return None

    return result_json


def update_intro_with_search(profile_json: dict) -> dict:
    name = profile_json.get("name", "")
    company_names = profile_json.get("company_names") or []
    social_profiles = profile_json.get("social_profile") or []
    
    # Construct search queries
    search_queries = []

    if name and company_names:
        search_queries.append(f"{name} {', '.join(company_names)}")

    for link in social_profiles:
        search_queries.append(f"{name} from profile {link}")

    # Use Tavily search and collect top result content
    results_text = ""
    for query in search_queries:
        result = tavily.run(query, num_results=1)
        if result and isinstance(result, list) and result[0].get("content"):
            results_text += result[0]["content"] + " "
    
    current_intro = profile_json.get("intro", "")
    final_intro = f"{current_intro.strip()} {results_text.strip()}".strip()
    
    # Return updated profile JSON
    updated_json = profile_json.copy()
    updated_json["intro"] = final_intro

    return updated_json
