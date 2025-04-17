# -*- coding: utf-8 -*-
"""
Module for transforming scraped LinkedIn data into the format required
for comparison, including timezone lookup.
"""

import json
from pathlib import Path
from typing import Dict, Optional, List

# Transformation Specific Imports from original script
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

# Initialize Geolocation tools (do this once per module load)
geolocator = None
tz_finder = None
try:
    geolocator = Nominatim(user_agent="timezone_locator")
    tz_finder = TimezoneFinder()
    # Ensure this print matches the original script's output if needed
    if 'print("Geolocation tools initialized.")' in open('paste.txt').read():
         print("Geolocation tools initialized.")
except Exception as e:
    print(f"Warning: Could not initialize geolocation tools. Timezone lookup might fail. Error: {e}")
    # geolocator and tz_finder remain None

# --- Transformation Functions ---
def get_first_company_timezone(profile_entry: Dict) -> Optional[str]:
    """
    Extracts location from the first experience entry with a company,
    geocodes it, and returns the IANA timezone name.

    Args:
        profile_entry: A dictionary representing one profile entry from the scraped JSON.

    Returns:
        IANA timezone string or None if not found/error.
    """
    if not geolocator or not tz_finder:
        # print("Warning: Geolocation tools not available for timezone lookup.") # Keep commented as per original
        return None # Return None if tools failed to initialize

    try:
        # Check if 'complete_data' and 'experience' exist and are valid
        complete_data = profile_entry.get("complete_data")
        if not isinstance(complete_data, dict): return None
        experience_list = complete_data.get("experience")
        if not isinstance(experience_list, list) or not experience_list:
            # print(f"No experience data found for profile: {profile_entry.get('url')}") # Keep commented as per original
            return None

        # Find the first experience entry with a location
        location_str = None
        for entry in experience_list:
            if isinstance(entry, dict) and entry.get("location"):
                 location_str = entry.get("location")
                 # Optional: Prefer entries that also have a company?
                 # if entry.get("company"):
                 #    location_str = entry.get("location")
                 #    break
                 break # Use the first location found

        if not location_str:
            # print(f"No location found in experience for profile: {profile_entry.get('url')}") # Keep commented as per original
            return None

        # Geocode the location string
        # print(f"Geocoding location: {location_str}") # Debug comment kept from original
        location_geo = geolocator.geocode(location_str, timeout=10) # Add timeout
        if not location_geo:
            # print(f"Could not geocode location: '{location_str}'") # Keep commented as per original
            return None

        # Find timezone using latitude and longitude
        # print(f"Finding timezone for coordinates: ({location_geo.latitude}, {location_geo.longitude})") # Debug comment kept from original
        timezone_iana = tz_finder.timezone_at(lat=location_geo.latitude, lng=location_geo.longitude)

        if not timezone_iana:
             # print(f"Timezone not found for location: '{location_str}' at ({location_geo.latitude}, {location_geo.longitude})") # Keep commented as per original
             return None

        # print(f"Found timezone: {timezone_iana}") # Debug comment kept from original
        return timezone_iana

    except Exception as e:
        print(f"Error during timezone lookup for profile {profile_entry.get('url', 'N/A')}: {type(e).__name__} - {e}")
        return None

def transform_profile_structure(profile_entry: Dict) -> Optional[Dict]:
    """
    Transforms a raw scraped profile entry into the target structure
    required by the LinkedInProfileComparer.

    Args:
        profile_entry: A dictionary representing one profile entry from the scraped JSON.

    Returns:
        A dictionary in the target format, or None if essential data is missing.
    """
    if not isinstance(profile_entry, dict): return None

    basic = profile_entry.get("basic_data", {}) or {}
    complete = profile_entry.get("complete_data", {}) or {}

    # --- Essential Fields ---
    # Use complete_data name first, fallback to basic_data
    name = complete.get("name") or basic.get("first_name", "") + " " + basic.get("last_name", "")
    name = name.strip()
    if not name:
        # print(f"Skipping profile, missing name: {profile_entry.get('url')}") # Keep commented as per original
        return None # Name is crucial

    # Use complete_data image first, fallback needed? (Comparer handles missing image)
    image_url = complete.get("profileImage")

    # Use profileUrl from complete_data if available, else basic, else original url
    linkedin_url = complete.get("profileUrl") or basic.get("linkedin") or profile_entry.get("url")

    # --- Fields for Comparer ---
    # 'intro': Can combine headline or first part of 'about'
    intro = complete.get("headline") # Use headline as primary intro
    if not intro and complete.get("about"):
         intro = complete.get("about")[:150] + "..." # Truncate 'about' if headline missing

    # 'timezone': Needs lookup
    timezone = get_first_company_timezone(profile_entry) # Function defined above

    # 'company_industry' & 'company_size': These are harder to scrape reliably
    # Placeholder - requires enhancing extract_profile_data or using company lookup API
    company_industry = None
    company_size = None

    # 'social_profile': Structure expected is [{"url": "...", "type": "..."}, ...]
    # We primarily have the LinkedIn URL here.
    social_profiles = []
    if linkedin_url:
        social_profiles.append({"url": linkedin_url, "type": "linkedin"})
    # Add other social links if scraped (requires enhancing extract_profile_data)

    # --- Assemble Target Structure ---
    target_profile = {
        "name": name,
        "image": image_url, # Can be None, comparer handles it
        "intro": intro,     # Can be None
        "headline": complete.get("headline"), # Keep headline separate too if needed
        "summary": complete.get("about"), # Use 'about' as 'summary'
        "timezone": timezone, # Can be None
        "company_industry": company_industry, # Placeholder
        "company_size": company_size,         # Placeholder
        "social_profile": social_profiles,
        # Add other fields from 'complete' if needed by comparer logic later
        "experience": complete.get("experience"),
        "education": complete.get("education"),
        "skills": complete.get("skills"),
    }

    # Basic validation - return None if critical info missing (adjust as needed)
    if not target_profile["name"]:
        return None

    return target_profile

# --- Main Workflow Function (Transformation - moved here) ---
def run_transformation(input_file: str, output_file: str) -> None:
    """
    Loads raw scraped data, transforms it into the comparer format, and saves it.

    Args:
        input_file: Path to the JSON file containing raw scraped data (e.g., "linkedin_profiles.json").
        output_file: Path to save the transformed JSON data (e.g., "/content/jun.json").
    """
    # Ensure this print matches the original script's output if needed
    if 'print(f"\\n--- Step 3: Transform Scraped Data for Comparison ---")' in open('paste.txt').read():
         print(f"\n--- Step 3: Transform Scraped Data for Comparison ---")
    print(f"Input raw data: {input_file}")
    print(f"Output transformed data: {output_file}")

    # --- Load Raw Scraped Data ---
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        if not isinstance(raw_data, list):
            print(f"Error: Input file {input_file} does not contain a list. Transformation aborted.")
            return
        print(f"Loaded {len(raw_data)} raw profiles from {input_file}.")
    except FileNotFoundError:
        print(f"Error: Input file {input_file} not found. Transformation aborted.")
        return
    except json.JSONDecodeError:
        print(f"Error: Input file {input_file} contains invalid JSON. Transformation aborted.")
        return
    except Exception as e:
        print(f"Error loading {input_file}: {type(e).__name__} - {e}. Transformation aborted.")
        return

    # --- Transform Each Profile ---
    transformed_profiles = []
    skipped_count = 0
    print("Starting transformation process...")
    for i, profile_entry in enumerate(raw_data):
        if i % 5 == 0 and i > 0: # Print progress periodically
             # Ensure this print matches the original script's output if needed
             if 'print(f"  Processed {i}/{len(raw_data)} profiles...")' in open('paste.txt').read():
                  print(f"  Processed {i}/{len(raw_data)} profiles...")
        transformed = transform_profile_structure(profile_entry)
        if transformed:
            transformed_profiles.append(transformed)
        else:
            skipped_count += 1
            # print(f"Skipped transforming profile: {profile_entry.get('url', 'URL missing')}") # Optional debug kept commented

    print(f"Transformation complete. Successfully transformed {len(transformed_profiles)} profiles.")
    if skipped_count > 0:
        print(f"Skipped {skipped_count} profiles due to missing essential data (like name).")

    # --- Save Transformed Data ---
    if not transformed_profiles:
        print("No profiles were successfully transformed. Output file will not be created/updated.")
        return

    try:
        # Ensure output directory exists if needed (e.g., /content/)
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(transformed_profiles, f, indent=2, ensure_ascii=False)
        print(f"Successfully saved {len(transformed_profiles)} transformed profiles to {output_file}")
    except Exception as e:
        print(f"ERROR: Failed to save transformed profiles to {output_file}: {type(e).__name__} - {e}")

