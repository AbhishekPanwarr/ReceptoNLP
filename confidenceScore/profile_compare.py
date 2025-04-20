import numpy as np
import os
from sklearn.metrics.pairwise import cosine_similarity
from PIL import Image, UnidentifiedImageError
import requests
from io import BytesIO
import json

from torchvision import models, transforms
import torch
import torch.nn as nn
import json
from sentence_transformers import SentenceTransformer
from langchain_openai import AzureChatOpenAI  # Add this import


# ----------------- IMAGE SIMILARITY -----------------

import requests
from PIL import Image, UnidentifiedImageError
from io import BytesIO

class VGG16ImageComparer:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        vgg = models.vgg16(weights=models.VGG16_Weights.DEFAULT)
        self.model = nn.Sequential(*list(vgg.features.children()))
        self.model.to(self.device)
        self.model.eval()
        self.transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        self.cache = {}

    import os

    def download_image(self, url, save_as="img"):
            """Download image from a URL (supports Google Drive), detect format, save with proper extension."""
            if not url or not isinstance(url, str):
                print(f"Invalid URL: {url}")
                return None

            # Return cached image if already downloaded
            if url in self.cache:
                print(f"Using cached image for URL: {url}")
                return self.cache[url]

            headers = {
                'User-Agent': 'Mozilla/5.0'
            }

            try:
                # Handle Google Drive shared links
                if 'drive.google.com' in url and '/file/d/' in url:
                    file_id = url.split('/d/')[1].split('/')[0]
                    url = f'https://drive.google.com/uc?id={file_id}'

                response = requests.get(url, headers=headers, timeout=20, stream=True)
                response.raise_for_status()

                image_data = BytesIO(response.content)
                img = Image.open(image_data).convert('RGB')

                # Detect format and define file extension
                img_format = img.format.lower() if img.format else 'png'
                extension = 'jpg' if img_format == 'jpeg' else img_format

                # Save image with proper extension
                os.makedirs("downloaded_images", exist_ok=True)
                filename = f"downloaded_images/{save_as}.{extension}"
                img.save(filename)
                print(f"Saved image to: {filename}")

                # Cache the image
                self.cache[url] = img
                return img

            except requests.exceptions.RequestException as req_error:
                print(f"Request error: {str(req_error)}")
            except UnidentifiedImageError as img_error:
                print(f"Unrecognized image: {str(img_error)}")
            except Exception as e:
                print(f"Download failed: {str(e)}")

            self.cache[url] = None
            return None



    def get_features(self, img):
        if img is None: 
            return None
        try:
            img_t = self.transform(img).unsqueeze(0).to(self.device)
            with torch.no_grad():
                features = self.model(img_t)
                features = torch.nn.functional.adaptive_avg_pool2d(features, (1, 1)).squeeze()
            return features.cpu().numpy()
        except Exception as e:
            print(f"Feature extraction error: {str(e)[:200]}")
            return None

    def similarity(self, url1, url2):
        if not url1 or not url2:
            return 0.0

        if url1 == url2:
            return 1.0

        # Download and load images as PIL.Image
        img1 = self.download_image(url1, save_as="img1")
        img2 = self.download_image(url2, save_as="img2")

        if img1 is None or img2 is None:
            return 0.0

        f1 = self.get_features(img1)
        f2 = self.get_features(img2)

        if f1 is None or f2 is None:
            return 0.0

        f1 = f1.reshape(1, -1)
        f2 = f2.reshape(1, -1)
        sim = cosine_similarity(f1, f2)[0][0]

        return max(0.0, min(1.0, sim))



# ----------------- TEXT EMBEDDING SIMILARITY -----------------
def persona_similarity(profile1, profile2, embedder):
    text1 = profile1.get("original_keys").get("intro")
    text2 = profile2.get("summary", "")
    
    if not text1 or not text2: 
        return 0.0
        
    e1 = embedder(text1)
    e2 = embedder(text2)
    
    # Validate embeddings
    if np.linalg.norm(e1) < 1e-6 or np.linalg.norm(e2) < 1e-6:
        return 0.0
        
    try:
        return float(cosine_similarity([e1], [e2])[0][0])
    except Exception as e:
        print(f"Similarity error: {str(e)[:200]}")
        return 0.0

# ----------------- LLM VALIDATION -----------------


def llm_validation(profile1, profile2, llm_client: AzureChatOpenAI):
    """LLM validation using pre-initialized AzureChatOpenAI client"""
    validation_prompt = f"""
    You are an expert at verifying if two professional profiles belong to the same person.
    Analyze the following profiles and give a score between 0 and 1 (1=definitely same, 0=definitely different).
    Consider job history, skills, education, social links, any other detail present in the personas and most importantly match timezone, company industry and size from the personas.
    Return JSON: {{"score": float, "reason": string}}

    Profile 1:
    {json.dumps(profile1, indent=2)}

    Profile 2:
    {json.dumps(profile2, indent=2)}
    """
    
    try:
        response = llm_client.invoke([
            {"role": "system", "content": "You are a HR verification AI that outputs JSON"},
            {"role": "user", "content": validation_prompt}
        ])
        
        # Parse response
        content = response.content
        data = json.loads(content)
        
        # Validate response structure
        score = max(0.0, min(1.0, float(data.get("score", 0.0))))
        reason = data.get("reason", "")[:500]  # Truncate long reasons
        
        return score, reason
        
    except json.JSONDecodeError:
        print("LLM returned invalid JSON")
        return 0.0, "Validation error"
    except Exception as e:
        print(f"LLM validation failed: {str(e)[:200]}")
        return 0.0, "Service error"



def get_embedding(text: str) -> np.ndarray:
    """
    Generate an embedding for the input text using the specified transformer model.

    Args:
        model_id (str): Hugging Face model ID (e.g., "sentence-transformers/all-MiniLM-L6-v2")
        text (str): The input text to embed

    Returns:
        np.ndarray: The generated embedding as a numpy array
    """
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    embedding = model.encode(text)
    return embedding

# ----------------- MAIN COMPARISON FUNCTION -----------------
def confidence_score(profile1, profile2, embedder, image_comparer, llm_validation, 
                     llm_client: AzureChatOpenAI):
    """Calculate confidence score with adaptive weighting when image similarity is too low"""

    # 1. Calculate raw scores
    og_keys = profile1.get("original_keys")
    img_score = image_comparer.similarity(og_keys.get("image"), profile2.get("image"))
    persona_score = persona_similarity(profile1, profile2, embedder)
    llm_score, llm_reason = llm_validation(profile1, profile2, llm_client)

    # 2. Fixed component weights
    original_weights = {'image': 0.6, 'persona': 0.25, 'llm': 0.15}

    # 3. Adjust weights if image similarity is too low
    if img_score < 5e-4:
        print(f"Image similarity too low ({img_score:.4f}) — redistributing weight.")
        persona_share = original_weights['persona'] / (original_weights['persona'] + original_weights['llm'])
        llm_share = 1 - persona_share

        adjusted_weights = {
            'image': 0.0,
            'persona': 0.75,
            'llm': 0.25
        }
    else:
        adjusted_weights = original_weights

    # 4. Prepare component data with new weights
    component_data = [
        ('image', img_score, adjusted_weights['image']),
        ('persona', persona_score, adjusted_weights['persona']),
        ('llm', llm_score, adjusted_weights['llm'])
    ]

    # 5. Weighted confidence calculation
    total_weight = sum(w for _, _, w in component_data)
    weighted_sum = sum(score * weight for _, score, weight in component_data)
    score_status = {name: f"{score:.4f}" for name, score, _ in component_data}

    # 6. Final result
    overall = weighted_sum / total_weight if total_weight > 0 else 0.0

    return {
        "image_similarity": score_status['image'],
        "persona_similarity": score_status['persona'],
        "llm_validation": score_status['llm'],
        "llm_reason": llm_reason,
        "overall_confidence": f"{overall:.4f} (using {total_weight:.1f}/1.0 weight)"
    }
