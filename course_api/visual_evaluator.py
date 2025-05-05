import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

# Initialize OpenAI client (ensure OPENAI_API_KEY is set in environment)
client = OpenAI()

class VisualEvaluator:
    """
    Evaluates visual content (images/videos) based on relevance, coherence, quality, and safety.
    Uses OpenAI's Vision and Moderation APIs.
    """

    def evaluate_visual(self, visual_url: str, scene_text: str) -> dict:
        """
        Evaluates a single visual against the scene text.

        Args:
            visual_url (str): The URL of the image or video to evaluate.
            scene_text (str): The text content of the scene.

        Returns:
            dict: A dictionary containing evaluation scores/flags for 
                  relevance, coherence, quality_assessment, and safety.
                  Example: {
                      "relevance_score": 0.8, 
                      "coherence_score": 0.7, 
                      "quality_assessment": "Good", 
                      "safety_flags": [], 
                      "overall_score": 0.75, 
                      "evaluation_notes": "Relevant visual, good quality."
                  }
        """
        evaluation = {
            "relevance_score": 0.0,
            "coherence_score": 0.0,
            "quality_assessment": "Unknown",
            "safety_flags": [],
            "overall_score": 0.0,
            "evaluation_notes": ""
        }

        # 1. Safety Check using Moderation API
        try:
            moderation_response = client.moderations.create(input=f"Visual content URL: {visual_url}\nScene context: {scene_text}")
            results = moderation_response.results[0]
            if results.flagged:
                evaluation["safety_flags"] = [cat for cat, flagged in results.categories.model_dump().items() if flagged]
                evaluation["evaluation_notes"] += f"Safety concerns flagged: {', '.join(evaluation['safety_flags'])}. "
                # Potentially return early or heavily penalize score if flagged
                # For now, just record flags and penalize overall score later
        except Exception as e:
            logger.error(f"Error during OpenAI Moderation API call for {visual_url}: {e}")
            evaluation["evaluation_notes"] += "Safety check failed. "
            evaluation["safety_flags"] = ["check_failed"]

        # 2. Relevance, Coherence, and Quality Check using Vision API (GPT-4 Vision)
        try:
            # Note: GPT-4 Vision currently works best with images. Video support is limited.
            # If visual_url is a video, this might not work as expected or might only analyze the first frame.
            # We might need a different approach for video evaluation (e.g., sampling frames).
            # For now, assume it works reasonably for images and potentially first frame of video.
            
            prompt = (
                f"Evaluate the visual content at the URL provided based on the following scene text:\n\n"
                f"Scene Text: "{scene_text}"\n\n"
                f"Assess the following criteria:\n"
                f"1. Relevance: How relevant is the visual to the scene text? (Score 0.0 to 1.0)
"
                f"2. Narrative Coherence: Does the visual fit logically and tonally with the scene text? (Score 0.0 to 1.0)
"
                f"3. Quality: Assess the visual quality (e.g., resolution, clarity, composition). (Rate as Poor, Fair, Good, Excellent)
"
                f"Provide your assessment in JSON format with keys: 'relevance_score', 'coherence_score', 'quality_assessment', 'brief_justification'."
            )

            vision_response = client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": visual_url},
                            },
                        ],
                    }
                ],
                max_tokens=300,
                # Ensure response format is JSON (might need specific prompting or model version)
                # For now, we parse the text response, assuming it's JSON-like
            )
            
            content = vision_response.choices[0].message.content
            # Attempt to parse the JSON response from the model
            try:
                # Clean potential markdown code block fences
                if content.startswith("```json"):
                    content = content.strip("```json\n")
                if content.endswith("```"):
                    content = content.strip("\n```")
                
                vision_eval = json.loads(content)
                evaluation["relevance_score"] = float(vision_eval.get("relevance_score", 0.0))
                evaluation["coherence_score"] = float(vision_eval.get("coherence_score", 0.0))
                evaluation["quality_assessment"] = str(vision_eval.get("quality_assessment", "Unknown"))
                evaluation["evaluation_notes"] += vision_eval.get("brief_justification", "")
            except (json.JSONDecodeError, TypeError, ValueError) as json_e:
                logger.error(f"Failed to parse GPT-4 Vision response as JSON for {visual_url}: {json_e}\nResponse: {content}")
                evaluation["evaluation_notes"] += "Vision evaluation parsing failed. "

        except Exception as e:
            # Handle potential errors like invalid URL, API errors, etc.
            logger.error(f"Error during OpenAI Vision API call for {visual_url}: {e}")
            evaluation["evaluation_notes"] += "Vision check failed. "

        # 3. Calculate Overall Score (Simple Example)
        # Penalize heavily if safety flags exist
        safety_penalty = 0.5 if evaluation["safety_flags"] and "check_failed" not in evaluation["safety_flags"] else 0.0
        # Basic average, could be weighted
        evaluation["overall_score"] = (evaluation["relevance_score"] + evaluation["coherence_score"]) / 2 * (1 - safety_penalty)
        # Adjust score based on quality assessment (optional)
        quality_map = {"Poor": 0.5, "Fair": 0.75, "Good": 1.0, "Excellent": 1.1}
        quality_multiplier = quality_map.get(evaluation["quality_assessment"], 0.9) # Default multiplier if Unknown
        evaluation["overall_score"] *= quality_multiplier
        evaluation["overall_score"] = max(0.0, min(1.0, evaluation["overall_score"])) # Clamp score between 0 and 1

        return evaluation

# Example Usage (for testing)
if __name__ == '__main__':
    # This part will only run when the script is executed directly
    # Requires OPENAI_API_KEY environment variable to be set
    evaluator = VisualEvaluator()
    test_url = "https://images.pexels.com/photos/1108099/pexels-photo-1108099.jpeg" # Example: Dogs
    test_scene = "A group of happy golden retriever puppies playing in a field."
    
    print(f"Evaluating visual: {test_url}")
    print(f"Scene text: {test_scene}")
    
    result = evaluator.evaluate_visual(test_url, test_scene)
    print("\nEvaluation Result:")
    import json
    print(json.dumps(result, indent=2))

