import os
from dotenv import load_dotenv

load_dotenv()
# -*- coding: utf-8 -*-
"""
Module for finding LinkedIn profiles using Google Custom Search API.
Contains the LinkedInProfileFinder class.
"""

import os
import requests
import time
import json # For potential error parsing
from urllib.parse import quote
from typing import List

# Attempt to import userdata, fail gracefully if not available
try:
    from google.colab import userdata
except ImportError:
    # print("Google Colab userdata module not available. Continuing without it.") # Keep original script's print behaviour if desired
    userdata = None # Define userdata as None if import fails

# --- LinkedIn Profile Finder Class (Google Search) ---
class LinkedInProfileFinder:
    """Finds LinkedIn profiles using Google Custom Search API."""
    def __init__(self, api_key=None, search_engine_id=None):
        # --- Securely Get API Key and Search Engine ID ---
        # Prioritize environment variables, then Colab userdata, then direct parameters
        self.api_key = os.environ.get('GOOGLE_SEARCH_API_KEY')
        self.search_engine_id = os.environ.get('GOOGLE_SEARCH_ENGINE_ID')

        if not self.api_key and userdata:
            try: self.api_key = userdata.get('GOOGLE_SEARCH_API_KEY')
            except NameError: pass # userdata not defined
            except Exception: pass # Other potential errors

        if not self.search_engine_id and userdata:
            try: self.search_engine_id = userdata.get('GOOGLE_SEARCH_ENGINE_ID')
            except NameError: pass
            except Exception: pass

        # Fallback to parameters if still not found
        if not self.api_key: self.api_key = api_key
        if not self.search_engine_id: self.search_engine_id = search_engine_id

        # --- Use provided fixed credentials as last resort (NOT RECOMMENDED FOR PRODUCTION) ---
        if not self.api_key:
            print("GOOGLE JSON API key intiallized.")
            self.api_key = os.getenv("GOGGLE_JSON_KEY") # Your provided key
        if not self.search_engine_id:
            print("Google Search Engine ID Initiallized")
            self.search_engine_id = os.getenv("SEARCH_ENGINE_ID") # Your provided ID

        # --- Final Check ---
        if not self.api_key or not self.search_engine_id:
            raise ValueError("Google Search API Key or Search Engine ID could not be found or provided.")
        else:
             # Ensure this print matches the original script's output if needed
             if 'print("Google Search credentials loaded.")' in open('paste.txt').read(): # Check if the original print exists
                  print("Google Search credentials loaded.")


        self.base_url = "https://www.googleapis.com/customsearch/v1"
        self.profiles_list = []  # Initialize profiles list

    def search_profiles(self, name, timezone=None, company=None, location=None, title=None, max_results=10):
        """Search for LinkedIn profiles based on various filters using Google Custom Search."""
        if not name:
             print("Error: Name is required for searching.")
             return []

        # Build search query
        query_parts = [name]
        if company: query_parts.append(f'"{company}"') # Exact phrase for company
        if title: query_parts.append(f'"{title}"')     # Exact phrase for title
        if location: query_parts.append(location)
        if timezone: query_parts.append(timezone) # Timezone might be less effective search term

        # Always restrict to LinkedIn profiles
        query_parts.append("site:linkedin.com/")

        query = " ".join(query_parts)
        # Ensure this print matches the original script's output if needed
        if 'print(f"Constructed Search Query: {query}")' in open('paste.txt').read():
             print(f"Constructed Search Query: {query}")

        # URL encode the query
        encoded_query = quote(query)

        results = []
        processed_urls = set() # To avoid duplicates across pages
        page = 1
        num_requested = min(max_results, 10) # API max 10 per page

        while len(results) < max_results:
            # Calculate start index for pagination (1-based)
            start_index = (page - 1) * 10 + 1
            num_to_fetch = min(num_requested, max_results - len(results)) # How many more we need/can get

            if num_to_fetch <= 0: break # Should not happen with outer loop condition, but safe check

            # Build request URL
            request_url = f"{self.base_url}?key={self.api_key}&cx={self.search_engine_id}&q={encoded_query}&start={start_index}&num={num_to_fetch}"
            # Ensure this print matches the original script's output if needed
            if 'print(f"Requesting URL: {request_url}")' in open('paste.txt').read():
                 print(f"Requesting URL: {request_url}")

            try:
                response = requests.get(request_url, timeout=20)
                # Ensure this print matches the original script's output if needed
                if 'print(f"Google API Response Status: {response.status_code}")' in open('paste.txt').read():
                     print(f"Google API Response Status: {response.status_code}")
                response.raise_for_status()  # Raise exception for HTTP errors (4xx, 5xx)
                data = response.json()

                # --- Debug: Print snippet of response ---
                # print("Google API Response Snippet:", json.dumps(data, indent=2)[:500]) # Keep commented as per original
                # ---------------------------------------


                # Check if 'items' exist in the response
                if "items" not in data or not data["items"]:
                    print("No more results found in Google API response.")
                    if "error" in data:
                        print(f"Google API Error: {data['error'].get('message', 'Unknown Error')}")
                    break # Exit loop if no items are returned

                # Extract and filter LinkedIn profile URLs
                found_new = False
                for item in data["items"]:
                    url = item.get("link")
                    # Basic validation: must contain /in/ and not be a directory/search URL
                    if url and "/in/" in url and not url.endswith("/in/") and "linkedin.com/pub/dir/" not in url:
                        # Normalize URL slightly (remove query params)
                        normalized_url = url.split('?')[0]
                        if normalized_url not in processed_urls:
                            results.append(normalized_url)
                            processed_urls.add(normalized_url)
                            found_new = True
                            # Ensure this print matches the original script's output if needed
                            if 'print(f"  Added: {normalized_url}")' in open('paste.txt').read():
                                 print(f"  Added: {normalized_url}")
                            if len(results) >= max_results:
                                break # Reached desired number

                # Check if we need to go to the next page
                # API might return fewer than requested even if more exist
                # Rely on checking if we reached max_results OR if 'nextPage' info is missing
                more_pages_exist = "queries" in data and "nextPage" in data["queries"] and data["queries"]["nextPage"]
                if len(results) >= max_results or not more_pages_exist:
                     # Ensure this print matches the original script's output if needed
                     if 'print("Reached max results or no more pages indicated by API.")' in open('paste.txt').read():
                          print("Reached max results or no more pages indicated by API.")
                     break

                page += 1
                # Add delay to respect API rate limits (adjust as needed)
                # Ensure this print matches the original script's output if needed
                if 'print("Waiting 1 second before next page request...")' in open('paste.txt').read():
                     print("Waiting 1 second before next page request...")
                time.sleep(1)

            except requests.exceptions.Timeout:
                print("Error: Google API request timed out.")
                break # Stop searching on timeout
            except requests.exceptions.HTTPError as e:
                print(f"Error: HTTP Error {e.response.status_code} from Google API.")
                try:
                     error_details = e.response.json()
                     print(f"API Error Details: {error_details.get('error', {}).get('message', 'No details')}")
                     # Specific handling for quota limits
                     if e.response.status_code == 429 or 'quota' in error_details.get('error', {}).get('message', '').lower():
                          print("Quota limit likely reached. Stopping search.")
                          break
                except json.JSONDecodeError:
                     print("Could not parse error response from API.")
                break # Stop on HTTP errors
            except requests.exceptions.RequestException as e:
                print(f"Error: Network-related error during Google API request: {e}")
                break # Stop on general network errors
            except KeyError as e:
                print(f"Error: Unexpected structure in Google API response (KeyError: {e}).")
                # Ensure this print matches the original script's output if needed
                if 'print(f"Response data snippet: {str(data)[:500]}")' in open('paste.txt').read():
                     print(f"Response data snippet: {str(data)[:500]}")
                break # Stop if response format is unexpected
            except Exception as e:
                 print(f"Error: An unexpected error occurred during Google Search: {type(e).__name__} - {e}")
                 import traceback
                 traceback.print_exc()
                 break
        # Ensure this print matches the original script's output if needed
        if 'print(f"Google Search finished. Found {len(results)} unique profile URLs.")' in open('paste.txt').read():
             print(f"Google Search finished. Found {len(results)} unique profile URLs.")
        return results

    def save_results_to_list(self, results: List[str]):
        """Save results to the instance list variable."""
        self.profiles_list = list(results) # Ensure it's a list copy
        # Ensure this print matches the original script's output if needed
        if 'print(f"Search results saved internally ({len(self.profiles_list)} profiles).")' in open('paste.txt').read():
             print(f"Search results saved internally ({len(self.profiles_list)} profiles).")
