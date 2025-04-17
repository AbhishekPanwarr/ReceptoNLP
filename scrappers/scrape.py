# -*- coding: utf-8 -*-
"""
Module for scraping LinkedIn profile data.
Contains helper functions, Pydantic models, data extraction logic,
and the LinkedInProvider class.
"""

import json
import time
import requests
import re
import itertools
from typing import List, Dict, Any, Optional, Tuple

# Scraping/Transformation Specific Imports from original script
from bs4 import BeautifulSoup
from pydantic import BaseModel
from typing_extensions import TypedDict

# --- Constants and Global Initializations (Scraping/Transformation - moved here) ---
user_agents = [
    "Slackbot-LinkExpanding 1.0 (+https://api.slack.com/robots)",
    "LinkedInBot/1.0",
    "Twitterbot/1.0",
    "facebookexternalhit/1.1",
    "WhatsApp/2.0",
    "Googlebot/2.1 (+http://www.google.com/bot.html)",
]
user_agent_cycle = itertools.cycle(user_agents)

# --- Helper Functions (Scraping/Transformation - moved here) ---
def mimic_bot_headers() -> str:
    """Mimic bot headers"""
    return next(user_agent_cycle)

def get_first_last_name(name: str) -> tuple[Optional[str], Optional[str]]:
    """Extracts first and last name from full name"""
    if not name or not isinstance(name, str):
        return None, None
    name_parts = name.strip().split(" ")
    if not name_parts:
        return None, None
    first_name = name_parts[0]
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else None
    return first_name, last_name

# --- Pydantic/TypedDict Models (Scraping/Transformation - moved here) ---
class Workspace(TypedDict):
    name: str
    url: Optional[str]

class LinkedinPersonProfile(BaseModel):
    first_name: Optional[str]
    last_name: Optional[str]
    linkedin: Optional[str]
    workspaces: Optional[list[Workspace]]

# Note: LinkedinCompanyProfile is defined but not explicitly used in the provided workflow.
# Keeping it here as it was in the original scraping/transformation section.
class LinkedinCompanyProfile(BaseModel):
    name: Optional[str]
    website: Optional[str]
    description: Optional[str]
    address: Optional[str]
    number_of_employees: Optional[int]


# --- Profile Data Extraction Function (Scraping) ---
def extract_profile_data(html):
    """Extracts detailed profile data from LinkedIn HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    data = {}

    # Name
    name_tag = soup.find('h1', class_=lambda x: x and 'top-card-layout__title' in x)
    data["name"] = name_tag.get_text(strip=True) if name_tag else None

    # Profile URL
    canonical = soup.find('link', rel="canonical")
    data["profileUrl"] = canonical['href'] if canonical and canonical.get('href') else None

    # Profile Image
    img_alt = data.get("name") # Use extracted name if available
    profile_img = None
    if img_alt:
        profile_img = soup.find('img', alt=img_alt)
    if not profile_img: # Fallback if name wasn't found or image alt doesn't match
        profile_img = soup.find('img', class_=lambda x: x and 'profile-photo-edit__preview' in x) # Common class
    if profile_img:
        # Prioritize data-delayed-url if available
        data["profileImage"] = profile_img.get('data-delayed-url') or profile_img.get('src')
    else:
        data["profileImage"] = None

    # Headline
    headline_tag = soup.find('h2', class_=lambda x: x and 'top-card-layout__headline' in x)
    data["headline"] = headline_tag.get_text(strip=True) if headline_tag else None

    # About Section
    # Note: LinkedIn frequently changes class names. These are common patterns.
    about_section = soup.find('section', class_=lambda x: x and 'summary' in x) or \
                    soup.find('section', id='about') or \
                    soup.find('div', class_=lambda x: x and 'pv-about-section' in x) # Another common class
    if about_section:
        # Find the main text block, often within nested divs/spans
        about_text_container = about_section.find('div', class_=lambda x: x and ('inline-show-more-text' in x or 'core-section-container__content' in x)) or \
                               about_section.find('p') # Fallback to paragraph
        if about_text_container:
            # Extract text, handling potential "See more" links if needed
            full_text = about_text_container.get_text(separator=' ', strip=True)
            # Basic cleanup (can be expanded)
            data["about"] = re.sub(r'\s+see more$', '', full_text, flags=re.IGNORECASE).strip()
        else:
             data["about"] = about_section.get_text(strip=True) # Fallback if specific container not found
    else:
        data["about"] = None

    # Experience
    exp_items = []
    # Look for the experience section using various potential identifiers
    exp_section = soup.find('section', attrs={"data-section": "experience"}) or \
                  soup.find('div', id='experience-section') or \
                  soup.find('div', id='experience') or \
                  soup.find('section', class_=lambda x: x and 'experience' in x.lower())

    if exp_section:
        # Find individual experience items (often <li> elements)
        list_items = exp_section.find_all('li', class_=lambda x: x and ('experience-item' in x or 'result-card' in x or 'list-style-none' in x)) # Add more potential classes
        if not list_items: # Fallback if li not found
             list_items = exp_section.find_all('div', class_=lambda x: x and 'pv-entity__position-group-pager' in x) # Grouped positions

        for item in list_items:
            exp_entry = {}

            # Try different ways to find title, company, date, location
            title_tag = item.find(['h3', 'span'], class_=lambda x: x and ('result-card__title' in x or 'item__title' in x or 't-bold' in x))
            company_tag = item.find(['span','h4'], class_=lambda x: x and ('result-card__subtitle' in x or 'item__subtitle' in x or 'job-details' in x))
            date_tag = item.find('span', class_=lambda x: x and ('date-range' in x or 'duration' in x))
            location_tag = item.find('span', class_=lambda x: x and ('location' in x or 'job-result-card__location' in x))

            exp_entry["title"] = title_tag.get_text(strip=True) if title_tag else None
            # Handle company name potentially having extra text like 'Full-time'
            if company_tag:
                company_text = company_tag.get_text(strip=True)
                # Simple split heuristic (may need refinement)
                parts = company_text.split('·')
                exp_entry["company"] = parts[0].strip() if parts else company_text
            else:
                exp_entry["company"] = None

            exp_entry["date"] = date_tag.get_text(strip=True) if date_tag else None
            exp_entry["location"] = location_tag.get_text(strip=True) if location_tag else None

            # Add if at least title or company is found
            if exp_entry["title"] or exp_entry["company"]:
                exp_items.append(exp_entry)

    data["experience"] = exp_items

    # Skills extraction (Combine various strategies)
    skills_items = []
    skills_section = soup.find('section', attrs={"data-section": "skills"}) or \
                    soup.find('section', id=lambda x: x and 'skills' in (x or '').lower()) or \
                    soup.find('section', class_=lambda x: x and 'skills' in (x or '').lower()) or \
                    soup.find('div', id=lambda x: x and 'skills' in (x or '').lower()) or \
                    soup.find('div', class_=lambda x: x and 'skills' in (x or '').lower())

    processed_skills = set() # To avoid duplicates
    if skills_section:
        # Strategy 1: Look for specific skill list items or elements containing 'skill' in class
        skill_elements = skills_section.find_all(lambda tag: tag.name in ['li', 'div', 'span'] and
                                                any(c and 'skill' in c.lower() for c in (tag.get('class') or [])))
        if not skill_elements: # Strategy 2: Look for common skill name classes
             skill_elements = skills_section.find_all(['h3', 'h4', 'p', 'span'], class_=lambda x: x and any(c in (x or '').lower() for c in ['skill-name', 'skill-card__name', 'pv-skill-category-entity__name-text']))

        for skill_elem in skill_elements:
            skill_name = skill_elem.get_text(strip=True)
            # Clean up common noise like endorsement counts
            skill_name = re.sub(r'\s*\d+\s*(endorsements?|recommendations?)$', '', skill_name, flags=re.IGNORECASE).strip()
            skill_name = re.sub(r'^see all \d+ skills$', '', skill_name, flags=re.IGNORECASE).strip() # Remove "see all skills" text

            if skill_name and len(skill_name) > 1 and len(skill_name) < 100 and skill_name.lower() not in processed_skills:
                skills_items.append({"name": skill_name})
                processed_skills.add(skill_name.lower())

        # Strategy 3: If still no skills, check section text for keyword patterns
        if not skills_items:
            text = skills_section.get_text(' ', strip=True)
            # Look for patterns like "Skills: skill1, skill2..."
            match = re.search(r'(?:Skills|Expertise)\s*:?\s*([\w\s,\-\+\#\.\(\)]+)(?:$|Endorsed|Show|Education|Experience)', text, re.IGNORECASE)
            if match:
                skills_text = match.group(1).strip()
                potential_skills = re.split(r'[,•|&]|\sand\s|\n', skills_text) # Split by common delimiters
                for skill in potential_skills:
                    skill = skill.strip()
                    if skill and len(skill) > 1 and len(skill) < 100 and skill.lower() not in processed_skills:
                        skills_items.append({"name": skill})
                        processed_skills.add(skill.lower())

    # Strategy 4: Look for skills in the 'About' section if none found yet
    if not skills_items and data.get("about"):
        about_text = data["about"]
        skill_match = re.search(r'(?:Skills|Expertise|Specialties)(?:\s*:|\s+include)?\s*([\w\s,\-\+\#\.\(\)]+)(?:$|\.|\n|Experience|Education)', about_text, re.IGNORECASE)
        if skill_match:
            skills_text = skill_match.group(1).strip()
            potential_skills = re.split(r'[,•|&]|\sand\s|\n', skills_text)
            for skill in potential_skills:
                skill = skill.strip()
                if skill and len(skill) > 1 and len(skill) < 100 and skill.lower() not in processed_skills:
                    skills_items.append({"name": skill})
                    processed_skills.add(skill.lower())

    data["skills"] = skills_items

    # Education
    edu_items = []
    # Look for education section using various potential identifiers
    edu_section = soup.find('section', attrs={"data-section": "educationsDetails"}) or \
                  soup.find('div', id='education-section') or \
                  soup.find('div', id='education') or \
                  soup.find('section', class_=lambda x: x and 'education' in x.lower())

    if edu_section:
        list_items = edu_section.find_all('li', class_=lambda x: x and ('education__list-item' in x or 'result-card' in x))
        if not list_items: # Fallback
             list_items = edu_section.find_all('div', class_=lambda x: x and 'pv-entity__school-details' in x)

        for item in list_items:
            edu_entry = {}
            # Try different ways to find institution, degree, dates
            inst_tag = item.find(['h3', 'span'], class_=lambda x: x and ('result-card__title' in x or 'item__title' in x or 'school-name' in x))
            degree_tag = item.find(['span', 'p'], class_=lambda x: x and ('result-card__subtitle' in x or 'item__subtitle' in x or 'degree-name' in x))
            date_tag = item.find('span', class_=lambda x: x and ('date-range' in x or 'education-date' in x))
            desc_tag = item.find('div', class_=lambda x: x and ('show-more-less-text' in x or 'description' in x))

            edu_entry["institution"] = inst_tag.get_text(strip=True) if inst_tag else None
            # Handle degree potentially containing field of study
            if degree_tag:
                degree_text = degree_tag.get_text(strip=True)
                # Attempt to split degree and field
                parts = degree_text.split(',')
                edu_entry["degree"] = parts[0].strip() if parts else degree_text
                edu_entry["field_of_study"] = parts[1].strip() if len(parts) > 1 else None
            else:
                edu_entry["degree"] = None
                edu_entry["field_of_study"] = None

            edu_entry["period"] = date_tag.get_text(strip=True) if date_tag else None
            edu_entry["description"] = desc_tag.get_text(" ", strip=True) if desc_tag else None

            if edu_entry["institution"]: # Add if institution is found
                edu_items.append(edu_entry)

    data["education"] = edu_items

    # Extract Highlights (Often contain Education or Certifications)
    highlight_data = []
    highlights_section = soup.find('section', class_=lambda x: x and 'highlights' in x.lower()) or \
                       soup.find('div', id='highlights') or \
                       soup.find('div', class_=lambda x: x and 'highlights' in x.lower())

    if highlights_section:
        # Look for list items or divs within highlights
        highlight_items = highlights_section.find_all(['li', 'div'], class_=lambda x: x and ('highlight' in x.lower() or 'pv-highlight-entity' in x))
        for item in highlight_items:
            highlight_text = item.get_text(strip=True)
            # Filter out common noise like button text
            if highlight_text and "Message" not in highlight_text and "Connect" not in highlight_text and len(highlight_text) > 10:
                 # Clean up the text
                highlight_text = re.sub(r'\s+', ' ', highlight_text).strip()
                highlight_data.append(highlight_text)
        # Fallback: get all text if specific items not found
        if not highlight_data:
             full_highlight_text = highlights_section.get_text(" ", strip=True)
             # Split into potential sentences or phrases
             potential_highlights = re.split(r'\.\s+|\n', full_highlight_text)
             for text in potential_highlights:
                  text = text.strip()
                  if text and "Message" not in text and "Connect" not in text and len(text) > 10:
                       highlight_data.append(text)


    data["highlights"] = highlight_data if highlight_data else None

    # Languages
    languages = []
    lang_section = soup.find('section', class_=lambda x: x and 'languages' in x) or \
                   soup.find('div', id='languages')
    if lang_section:
        list_items = lang_section.find_all(['li', 'div'], class_=lambda x: x and ('pv-language-entity' in x or 'list-item' in x))
        for item in list_items:
            language = None
            proficiency = None
            lang_name_tag = item.find(['h3', 'span'], class_=lambda x: x and 'pv-entity__description' not in x) # Try to exclude proficiency span
            prof_tag = item.find(['h4', 'span', 'p'], class_=lambda x: x and ('pv-entity__description' in x or 'proficiency' in x.lower()))

            if lang_name_tag:
                language = lang_name_tag.get_text(strip=True)
            if prof_tag:
                proficiency = prof_tag.get_text(strip=True)

            # Basic validation
            if language and len(language) < 50: # Avoid grabbing large text blocks
                 # Clean proficiency if it's just the language name repeated
                 if proficiency and proficiency.lower() == language.lower():
                     proficiency = None
                 languages.append({"language": language, "proficiency": proficiency})

    data["languages"] = languages

    # Recommendations Received (Count)
    recommendations_received = None
    rec_section = soup.find('section', class_=lambda x: x and 'recommendations' in x) or \
                  soup.find('div', id='recommendation') # Different IDs possible
    if rec_section:
        # Try finding a specific count element first
        count_tag = rec_section.find('span', class_=lambda x: x and 'count' in x) # Hypothetical class
        if count_tag:
             try:
                 recommendations_received = int(count_tag.get_text(strip=True))
             except ValueError:
                 pass # Ignore if not a number

        # Fallback: Use regex on the section text
        if recommendations_received is None:
            rec_text = rec_section.get_text(" ", strip=True)
            # Look for patterns like "X recommendations", "Received (Y)"
            m = re.search(r"received\s*\((\d+)\)|(\d+)\s+(?:people have recommended|recommendations?)", rec_text, re.IGNORECASE)
            if m:
                count_str = m.group(1) or m.group(2)
                if count_str:
                    try:
                        recommendations_received = int(count_str)
                    except ValueError:
                         pass # Ignore if not a number

    data["recommendationsReceived"] = recommendations_received

    return data

# --- LinkedIn Provider Class (Scraping) ---
class LinkedInProvider:
    """Get data from linkedin URL using web scraping"""

    def _fetch_data(self, url: str) -> Optional[str]:
        """Fetches HTML content for a given URL with retries and proxy."""
        retry_count = 3
        # Use your Bright Data proxy details here
        # Ensure these are securely managed, e.g., via environment variables or a secrets manager
        proxy_user = "brd-customer-hl_6c1f36a6-zone-datacenter_proxy2" # Replace if necessary
        proxy_pass = "1qyqs0lnh5zi"                                    # Replace if necessary
        proxy_host = "brd.superproxy.io"
        proxy_port = "33335" # Check if this port is correct for your zone

        proxies = {
            "http": f"http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}",
            "https": f"http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}",
        }

        for attempt in range(retry_count):
            user_agent = mimic_bot_headers()
            headers = {"User-Agent": user_agent}

            try:
                # Ensure this print matches the original script's output if needed
                if 'print(f"Attempt {attempt + 1}/{retry_count}: Fetching {url} with User-Agent: {user_agent}")' in open('paste.txt').read():
                     print(f"Attempt {attempt + 1}/{retry_count}: Fetching {url} with User-Agent: {user_agent}")
                response = requests.get(
                    url,
                    headers=headers,
                    proxies=proxies,
                    timeout=45,  # Increased timeout
                    verify=False # Added verify=False (use with caution, understands security implications)
                )
                response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
                # Ensure this print matches the original script's output if needed
                if 'print(f"Success: Status code {response.status_code}")' in open('paste.txt').read():
                     print(f"Success: Status code {response.status_code}")
                return response.text

            except requests.exceptions.Timeout:
                print(f"Attempt {attempt + 1} failed: Timeout occurred.")
            except requests.exceptions.HTTPError as e:
                print(f"Attempt {attempt + 1} failed: HTTP Error {e.response.status_code} for URL: {url}")
                # Specific handling for common block codes
                if e.response.status_code in [403, 429, 503]:
                     print("Potential block or rate limit detected.")
                     time.sleep(5 * (attempt + 1)) # Exponential backoff
                else:
                     break # Don't retry on other client/server errors like 404
            except requests.exceptions.ProxyError as e:
                 print(f"Attempt {attempt + 1} failed: Proxy Error: {e}")
                 print("Check proxy configuration and credentials.")
                 time.sleep(5) # Wait before retrying proxy issue
            except requests.exceptions.RequestException as e:
                print(f"Attempt {attempt + 1} failed: Request Exception: {e}")
                time.sleep(3 * (attempt + 1)) # General backoff

            # Wait before retrying
            if attempt < retry_count - 1:
                wait_time = 3 * (attempt + 1)
                print(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)

        print(f"Failed to fetch the linkedin URL after {retry_count} attempts: {url}")
        return None

    def _json_ld_data(self, html_content: str) -> Optional[dict]:
        """Extracts JSON-LD data from HTML, trying different script types."""
        if not html_content: return {}
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            # Standard JSON-LD
            script_tag = soup.find("script", {"type": "application/ld+json"})
            if script_tag and script_tag.string:
                try: return json.loads(script_tag.string)
                except json.JSONDecodeError: pass # Try next method if parsing fails

            # Look for data embedded in other script tags (common in SPAs)
            # This requires inspecting the page source to find the right pattern
            all_scripts = soup.find_all("script")
            for script in all_scripts:
                if script.string:
                    # Example: Look for a script containing "window.__INITIAL_STATE__ ="
                    if "window.__INITIAL_STATE__" in script.string:
                        try:
                            # Extract the JSON part carefully
                            json_str = script.string.split('window.__INITIAL_STATE__ =', 1)[1].split(';</script>', 1)[0].strip()
                            # Remove potential trailing semicolon
                            if json_str.endswith(';'):
                                json_str = json_str[:-1]
                            return json.loads(json_str)
                        except (IndexError, json.JSONDecodeError) as e:
                            # Ensure this print matches the original script's output if needed
                            if 'print(f"Error parsing assumed initial state JSON: {e}")' in open('paste.txt').read():
                                 print(f"Error parsing assumed initial state JSON: {e}")
                            continue # Try next script
            return {} # Return empty if no suitable script found
        except Exception as e:
            print(f"Error in extracting JSON-LD or embedded script data: {e}")
            return {}

    def person_profile(self, url: str) -> Tuple[Optional[LinkedinPersonProfile], Optional[Dict]]:
        """Extracts basic (Pydantic) and complete (scraped) profile details of a person."""
        try:
            html_content = self._fetch_data(url)
            if not html_content:
                # Ensure this print matches the original script's output if needed
                if 'print(f"No HTML content retrieved for URL: {url}")' in open('paste.txt').read():
                     print(f"No HTML content retrieved for URL: {url}")
                return None, None

            # --- Perform Full HTML Scraping FIRST ---
            scraped_data = extract_profile_data(html_content)

            # --- Attempt JSON-LD Extraction (Secondary/Complementary) ---
            json_ld_data = self._json_ld_data(html_content)

            # --- Construct Basic Pydantic Profile (using best available data) ---
            basic_profile = None
            name = None
            workplaces = []
            linkedin_url_final = url # Default to input URL

            # Try getting name from scraped data first (often more reliable)
            if scraped_data and scraped_data.get("name"):
                name = scraped_data.get("name")
                linkedin_url_final = scraped_data.get("profileUrl") or url # Use canonical if available
            # Fallback to JSON-LD name
            elif json_ld_data:
                person_data_ld = {}
                if json_ld_data.get("@type") == "ProfilePage":
                    person_data_ld = json_ld_data.get("mainEntity", {})
                elif isinstance(json_ld_data.get("@graph"), list):
                     try:
                          person_data_ld = next((item for item in json_ld_data["@graph"] if item.get("@type") == "Person"),{})
                     except StopIteration: pass
                name = person_data_ld.get("name") or name # Use if not already set

            # Try getting workplaces from scraped experience
            if scraped_data and scraped_data.get("experience"):
                seen_companies = set()
                for exp in scraped_data["experience"]:
                    if exp.get("company") and exp["company"].lower() not in seen_companies:
                        workplaces.append({"name": exp["company"], "url": None}) # Scraped data rarely has company URL
                        seen_companies.add(exp["company"].lower())
            # Fallback/Supplement with JSON-LD workplaces
            elif json_ld_data:
                 person_data_ld = {} # Re-fetch person data if needed
                 # (Logic to find person_data_ld as above)
                 if json_ld_data.get("@type") == "ProfilePage": person_data_ld = json_ld_data.get("mainEntity", {})
                 elif isinstance(json_ld_data.get("@graph"), list):
                     try: person_data_ld = next((item for item in json_ld_data["@graph"] if item.get("@type") == "Person"),{})
                     except StopIteration: pass

                 ld_works_for = person_data_ld.get("worksFor", [])
                 if isinstance(ld_works_for, dict): # Handle single org case
                      ld_works_for = [ld_works_for]
                 if isinstance(ld_works_for, list):
                      seen_companies_ld = {wp['name'].lower() for wp in workplaces} # Track already added
                      for org in ld_works_for:
                           if isinstance(org, dict) and "name" in org and org["name"].lower() not in seen_companies_ld:
                                workplaces.append({
                                     "name": org.get("name"),
                                     "url": org.get("url", None),
                                })
                                seen_companies_ld.add(org["name"].lower())

            # Construct the basic profile if we have a name
            if name:
                first_name, last_name = get_first_last_name(name)
                basic_profile = LinkedinPersonProfile(
                    first_name=first_name,
                    last_name=last_name,
                    linkedin=linkedin_url_final,
                    workspaces=workplaces if workplaces else None,
                )

            return basic_profile, scraped_data # Return both basic and complete data

        except Exception as e:
            print(f"Error occurred during person profile extraction for {url}: {e}")
            import traceback
            traceback.print_exc()
            return None, None # Return Nones if error
