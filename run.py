from agent.preprocess import enrich_profile_json, update_intro_with_search
from scrappers.combine import search_profiles_from_json, get_profiles_details
from confidenceScore.profile_compare import get_embedding, VGG16ImageComparer, llm_validation, confidence_score
import os
from dotenv import load_dotenv
from agent.models import llm
import json # For potential error parsing
load_dotenv()


imgComparer = VGG16ImageComparer()

null = None
persona_json = [{ 
      "name": "Xe",
        "image": "https://avatars.slack-edge.com/2024-02-20/6656372408823_9879d0af2ffb3edb4c71_original.png",
        "intro": null,
        "timezone": "America/New_York",
        "company_industry": null,
        "company_size": null,
        "social_profile": [
            "https://github.com/Xe",
            "https://christine.website"
        ]
        }
      ]

# ... [previous code remains unchanged]
matched_personas = []
for persona in persona_json:
    search_persona = enrich_profile_json(llm, persona)

    linkedin_urls = search_profiles_from_json(search_persona, max_results=2)
    nth_personas = get_profiles_details(linkedin_urls)
    final_persona = update_intro_with_search(search_persona)
    print(final_persona)
    confidence_scores = []
    for ith_persona in nth_personas:
        cf = confidence_score(final_persona, ith_persona, get_embedding, imgComparer, llm_validation, llm, 0.05)
        confidence_scores.append(cf)

    # Find the best match
    if confidence_scores:
        # Extract numerical confidence values
        conf_values = [
            float(score['overall_confidence'].split()[0]) 
            for score in confidence_scores
        ]
        
        # Get index of highest confidence
        max_index = conf_values.index(max(conf_values))
        
        # Get corresponding LinkedIn URL
        best_match_url = linkedin_urls[max_index]
        matched_personas.append(best_match_url)
        print(f"\nBest match for {persona['name']}:")
        print(f"URL: {best_match_url}")
        print(f"Confidence: {conf_values[max_index]:.4f}")
    else:
        print("\nNo valid profiles found")


print(matched_personas)

