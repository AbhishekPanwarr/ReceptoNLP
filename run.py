from agent.preprocess import enrich_profile_json, update_intro_with_search, find_linkedin_profiles_by_tavily
from scrappers.combine import search_profiles_from_json, get_profiles_details
from confidenceScore.profile_compare import get_embedding, VGG16ImageComparer, llm_validation, confidence_score
from agent.models import llm
from dotenv import load_dotenv
import os

load_dotenv()

imgComparer = VGG16ImageComparer()
null = None

def find_best_linkedin_match(persona: dict):
    search_persona = enrich_profile_json(llm, persona)
    final_persona = update_intro_with_search(search_persona)
    google_json_urls = search_profiles_from_json(search_persona, max_results=4)
    tavliy_urls = find_linkedin_profiles_by_tavily(search_persona)
    linkedin_urls = list(set(tavliy_urls + google_json_urls))

    nth_personas = get_profiles_details(linkedin_urls)
    confidence_scores = []
    
    for ith_persona in nth_personas:
        cf = confidence_score(final_persona, ith_persona, get_embedding, imgComparer, llm_validation, llm)
        confidence_scores.append(cf)

    if confidence_scores:
        conf_values = [
            float(score['overall_confidence'].split()[0]) 
            for score in confidence_scores
        ]
        max_index = conf_values.index(max(conf_values))
        best_match_url = linkedin_urls[max_index]
        best_confidence = conf_values[max_index]
        return {
            "linkedin_url": best_match_url,
            "confidence_score": best_confidence
        }
    else:
        return {
            "linkedin_url": None,
            "confidence_score": 0.0
        }
