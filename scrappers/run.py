from combine import search_profiles_from_json, get_profiles_details

# Example profile JSON with search criteria
profile_json = {
    "name": "Zach Hawtof",
    "image": "https://drive.google.com/file/d/1G4nkXOR_f-RGKdXw0HJctVmVVcSU6VS2/view?usp=drive_link",
    "intro": "Community Leader. Occasional CEO. Tightknit (https://community.tightknit.ai)",
    "timezone": "America/New_York",
    "company_industry": None,
    "company_size": None,
    "social_profile": []
}

# Get a list of LinkedIn profile URLs
linkedin_urls = search_profiles_from_json(profile_json, max_results=5)

# Use the URLs from the search or provide your own list
profile_details = get_profiles_details(linkedin_urls)
print(profile_details)
