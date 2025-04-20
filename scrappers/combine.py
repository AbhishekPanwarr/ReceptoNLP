# -*- coding: utf-8 -*-
"""
Main module for LinkedIn profile search and scraping.
Provides functions to search for profiles and extract detailed information.
"""

import json
import time
from typing import List, Dict, Any, Optional

# Import functions/classes from other modules
from scrappers.search import LinkedInProfileFinder
from scrappers.scrape import LinkedInProvider
from scrappers.transform import run_transformation


def search_profiles_from_json(profile_json: Dict[str, Any], max_results: int = 10) -> List[str]:
    """
    Search for LinkedIn profiles using criteria extracted from input JSON.
    
    Args:
        profile_json: Dictionary containing search criteria (name, intro, etc.)
        max_results: Maximum number of results to return
        
    Returns:
        List of LinkedIn profile URLs
    """
    if not profile_json:  # Add this check
        print("Error: profile_json is None")
        return []
    
    print("\n--- Searching for LinkedIn Profiles ---")

    # Extract search criteria from the input JSON
    name = profile_json.get('name') or None
    if not name:
        print("Error: Name is required for searching")
        return []
    og_keys = profile_json.get('original_keys') or None
    timezone = og_keys.get("timezone", '')

    company_names = profile_json.get('company_names', [])
    if company_names:
        company_names = company_names[0]
    else: company_names = None
    
    # Extract potential title/role from intro or other fields
    intro = profile_json.get('intro', '')
    title = None
    
    # If intro contains company info or parentheses, extract potential title
    if intro:
        # Basic extraction - could be enhanced with more sophisticated parsing
        parts = intro.split('.')
        if parts:
            title = parts[0].strip()
        
        # Remove any URLs that might be in the intro
        if title and 'http' in title:
            title = title.split('http')[0].strip()
    
    # Initialize the finder
    try:
        finder = LinkedInProfileFinder()
    except Exception as e:
        print(f"Error initializing profile finder: {e}")
        return []
    
    # Print search parameters
    print(f"Search parameters:")
    print(f"  Name: {name}")
    print(f"  Company: {company_names}")
    print(f"  Max Results: {max_results}")
    
    # Perform the search
    results = finder.search_profiles(
        name=name,
        # company=company_names,
        max_results=max_results,
    )
    
    if results:
        print(f"\nFound {len(results)} LinkedIn profile URLs from Google Json Search.")
    else:
        print("No LinkedIn profile URLs found matching the criteria from Google Json Search.")
    
    return results

def get_profiles_details(urls: List[str]) -> List[Dict[str, Any]]:
    """
    Scrape and transform LinkedIn profiles from a list of URLs.
    
    Args:
        urls: List of LinkedIn profile URLs
        
    Returns:
        List of dictionaries containing detailed profile information
    """
    if not urls:
        print("No URLs provided to scrape.")
        return []
    
    print(f"\n--- Scraping {len(urls)} LinkedIn Profiles ---")
    
    provider = LinkedInProvider()
    profile_details = []
    
    for i, url in enumerate(urls, 1):
        print(f"\nProcessing URL {i}/{len(urls)}: {url}")
        
        try:
            # Scrape the profile using the LinkedInProvider
            basic_data, complete_data = provider.person_profile(url)
            
            if not basic_data and not complete_data:
                print(f"Failed to extract any data from {url}. Skipping.")
                continue
            
            # Construct the profile JSON
            profile_json = {}
            
            # Add data from complete_data (from HTML scraping)
            if complete_data:
                profile_json.update({
                    'name': complete_data.get('name'),
                    'image': complete_data.get('profileImage'),
                    'intro': complete_data.get('headline'),
                    'summary': complete_data.get('about'),
                    'url': complete_data.get('profileUrl') or url,
                    'experience': complete_data.get('experience', []),
                    'education': complete_data.get('education', []),
                    'skills': complete_data.get('skills', []),
                    'languages': complete_data.get('languages', []),
                    'highlights': complete_data.get('highlights')
                })
            
            # Add/supplement with data from basic_data (Pydantic model)
            if basic_data:
                # If name wasn't found in complete_data, use from basic_data
                if not profile_json.get('name') and (basic_data.first_name or basic_data.last_name):
                    profile_json['name'] = f"{basic_data.first_name or ''} {basic_data.last_name or ''}".strip()
                
                # Add workspaces
                if basic_data.workspaces:
                    profile_json['workspaces'] = basic_data.workspaces
                
                # Ensure URL is set
                if not profile_json.get('url') and basic_data.linkedin:
                    profile_json['url'] = basic_data.linkedin
            
            # Clean up: Remove None values for cleaner JSON
            profile_json = {k: v for k, v in profile_json.items() if v is not None}
            
            if profile_json:
                profile_details.append(profile_json)
                print(f"Successfully extracted data for: {profile_json.get('name', 'Unknown')}")
            else:
                print(f"No usable data extracted from {url}")
            
            # Add a delay between requests to avoid rate limiting
            if i < len(urls):
                wait_time = 3  # seconds
                print(f"Waiting {wait_time} seconds before next request...")
                time.sleep(wait_time)
                
        except Exception as e:
            print(f"Error processing {url}: {type(e).__name__} - {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\nCompleted scraping. Successfully extracted data for {len(profile_details)} profiles")
    return profile_details

def save_profiles_to_file(profiles: List[Dict[str, Any]], output_file: str) -> None:
    """
    Save profile results to a JSON file.
    
    Args:
        profiles: List of profile dictionaries
        output_file: Path to output file
    """
    if not profiles:
        print("No profiles to save")
        return
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(profiles, f, indent=2, ensure_ascii=False)
        print(f"Successfully saved {len(profiles)} profiles to {output_file}")
    except Exception as e:
        print(f"Error saving profiles to {output_file}: {e}")

