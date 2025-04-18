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
persona_json = [
    { "name": "Eric Doty",
        "image": "https://avatars.slack-edge.com/2020-03-05/984845117296_258edf4c525224d42bff_original.jpg",
        "intro": "Content @ Dock",
        "timezone": "America/Los_Angeles",
        "company_industry": null,
        "company_size": null,
        "social_profile": null
}
      ]

matched_personas = []
for persona in persona_json:
    search_persona = enrich_profile_json(llm, persona)

    linkedin_urls = search_profiles_from_json(search_persona, max_results=12)
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
        print(f'Stats: {confidence_scores[max_index]}')
        print(f"Confidence: {conf_values[max_index]*100:.4f}")
        
    else:
        print("\nNo valid profiles found")
        matched_personas.append("Not able to find a valid profile")


print(matched_personas)

