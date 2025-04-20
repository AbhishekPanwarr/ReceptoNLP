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
2. Extract all company names mentioned in the name, intro fields, from a company link or anywhere present in the json. Include all of them in a list.
3. Extract any **additional links** from the input (e.g company's link, etc), but exclude the ones in the `social_profile and image` list.

Return ONLY a valid, minified JSON object. Do NOT include any explanations, markdown formatting, or comments. Just the JSON on a single line.
While preserving all the original keys:

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
    # Extract name, company_names, and social_profiles
    og_keys = profile_json.get("original_keys", {})
    name = profile_json.get("name", "")
    company_names = profile_json.get("company_names") or []
    social_profiles = og_keys.get("social_profile") or [] 
    
    # Construct search queries
    search_queries = []
    
    # Add search queries for each social profile link
    for link in social_profiles:
        search_queries.append(f"who is {name} according to {link}?")
        search_queries.append(f"What does {name} do according to {link}?")
    
    # Add search queries for each company name
    for company in company_names:
        if name:
            search_queries.append(f"{name} {company}")
    
    # Collect top 3 titles from results for each query
    results_titles = []
    for query in search_queries:
        results = tavily.run(query, num_results=3)
        if results and isinstance(results, list):
            for result in results[:3]:
                title = result.get("title")
                if title:
                    results_titles.append(f"- {title}")
    
    # Update profile intro
    current_intro = og_keys.get('intro', "") or ""
    titles_text = ". ".join(results_titles)
    final_intro = f"{current_intro.strip()}. {titles_text}".strip()

    # Return updated profile JSON
    updated_json = profile_json.copy()
    updated_json["intro"] = final_intro

    return updated_json


def find_linkedin_profiles_by_tavily(profile_json: dict) -> list:
    if profile_json is None:
        print("Error: profile_json is None!")
        return []

    # Extract name and company names from the input JSON
    name = profile_json.get("name", "")
    company_names = profile_json.get("company_names") or []
    social_profiles = profile_json.get("social_profile") or []

    linkedin_links = []

    # Search 1: Query with just the name
    if name:
        query_name = f"LinkedIn profile of {name}"
        results_name = tavily.run(query_name, num_results=3)
        if results_name and isinstance(results_name, list):
            for result in results_name:
                if 'linkedin.com' in result.get('url', '') and 'company' not in result.get('url', ''):
                    linkedin_links.append(result.get('url'))

    # Search 2: Query with name + each company name
    for company_name in company_names:
        if company_name:
            query_name_company = f"LinkedIn profile of {name} at {company_name}"
            results_name_company = tavily.run(query_name_company, num_results=3)
            if results_name_company and isinstance(results_name_company, list):
                for result in results_name_company:
                    if 'linkedin.com' in result.get('url', '') and 'company' not in result.get('url', ''):
                        linkedin_links.append(result.get('url'))

    # Search 3: Query with name + full social profile URL
    for profile in social_profiles:
        if 'linkedin.com' not in profile:
            query_social_url = f"LinkedIn profile of {name} based on social profile {profile}"
            results_social_url = tavily.run(query_social_url, num_results=3)
            if results_social_url and isinstance(results_social_url, list):
                for result in results_social_url:
                    if 'linkedin.com' in result.get('url', '') and 'company' not in result.get('url', ''):
                        linkedin_links.append(result.get('url'))

    return linkedin_links
