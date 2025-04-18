#ReceptoNLP High Prep PS

- **Python 3.8+**
- **Google Custom Search API** (for LinkedIn profile discovery)
- **Azure OpenAI API** (for LLM-based enrichment and validation)
- **Tavily API** (optional, for additional enrichment)
- **VGG16 Image Embedding** (for image similarity)
- **python-dotenv** (for secure environment variable management)

---

## Setup Instructions

### 1. Clone the Repository

```bash
git clone 
cd 
```

---

### 2. Create and Activate a Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```
[Reference][5][10]

---

### 3. Create and Configure the `.env` File

Create a `.env` file in the project root with the following variables (fill in your API keys and endpoints):

```
TAVILY_API_KEY=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_DEPLOYMENT_NAME=
AZURE_OPENAI_API_VERSION=
GOGGLE_JSON_KEY=
SEARCH_ENGINE_ID=
```
[Reference][4][6]

**Important:**   
- Add `.env` to your `.gitignore`.

---

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```
[Reference][10]

---

### 5. Add Your Persona JSON List

Edit the `run.py` (or your main script) and update the `persona_json` variable with your list of personas. Example:

```python
persona_json = [
    { 
        "name": "Eric Doty",
        "image": "https://avatars.slack-edge.com/2020-03-05/984845117296_258edf4c525224d42bff_original.jpg",
        "intro": "Content @ Dock",
        "timezone": "America/Los_Angeles",
        "company_industry": null,
        "company_size": null,
        "social_profile": null
}
]
```

---

### 6. Run the Project

```bash
python run.py
```

---

## Usage Example

When you run the script, for each persona in your list, the program will:

1. Enrich the persona profile using LLMs.
2. Search LinkedIn for matching profiles using Google Custom Search.
3. Fetch details for each found profile.
4. Score each match based on text and image similarity.
5. Print the best-matching LinkedIn profile URL and confidence score for each persona.

**Sample Output:**
```
Best match for Eric Doty:
URL: https://ca.linkedin.com/in/edoty
Stats: {'image_similarity': 'not defined (score < 0.05)', 'persona_similarity': '0.5423', 'llm_validation': '0.9500', 'llm_reason': "Both profiles share the exact same name 'Eric Doty' and are associated with the same company 'Dock'. Profile 1 provides detailed content marketing and freelancer onboarding expertise which aligns with the summary in Profile 2 about scaling as a content team. The images are different but could be due to different platforms or image update timings. Profile 2 has a LinkedIn URL that further supports the professional identity. The timezone from Profile 1 (America/Los_Angeles) is plausible and does n", 'overall_confidence': '0.6952 (using 0.4/1.0 weight)'}
Confidence: 69.5200
['https://ca.linkedin.com/in/edoty']
```

The final output will be a list of the highest matching LinkedIn profile URLs for your personas.

---

## Security Notes

- **API Keys:** Store all sensitive keys in the `.env` file. Never hardcode or share them.
- **.env File:** Always add `.env` to `.gitignore` to prevent accidental exposure.
- **Key Rotation:** Periodically update your API keys for security.

---

## License

This project is for educational and competition use. Please check with the organizers or your team for licensing details.

---
