import os
import requests
from django.conf import settings
import logging
from typing import Set # Import Set for type hinting

from .visual_evaluator import VisualEvaluator # Import the evaluator

logger = logging.getLogger(__name__)

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
PEXELS_VIDEO_SEARCH_URL = "https://api.pexels.com/videos/search"

def search_and_evaluate_pexels_videos(
    query: str, 
    scene_text: str, 
    used_urls: Set[str] | None = None, # Added parameter to track used URLs
    num_candidates_per_page: int = 5, # Fetch more candidates per page
    max_pages: int = 3, # Limit number of pages to fetch
    max_total_evaluations: int = 15, # Limit total evaluations
    orientation: str = "landscape"
) -> str | None:
    """Searches for videos on Pexels, evaluates them, avoids used URLs, and returns the best one.

    Args:
        query: The search term(s) derived from scene text.
        scene_text: The full text of the scene for evaluation context.
        used_urls: A set of video URLs already used in the current module.
        num_candidates_per_page: Number of video candidates to retrieve per API call.
        max_pages: Maximum number of pages to fetch from Pexels.
        max_total_evaluations: Maximum number of candidates to evaluate in total.
        orientation: Desired video orientation (landscape, portrait, square).

    Returns:
        The URL of the best evaluated *new* video, or None if no suitable video is found.
    """
    if not PEXELS_API_KEY:
        logger.error("PEXELS_API_KEY not found. Cannot search Pexels.")
        return None

    if used_urls is None:
        used_urls = set()

    headers = {
        "Authorization": PEXELS_API_KEY
    }
    
    evaluator = VisualEvaluator()
    best_video_url = None
    highest_score = -1.0
    evaluation_results = []
    evaluated_count = 0
    current_page = 1

    logger.info(f"Searching for unique video for query: 	'{query}'")

    while current_page <= max_pages and evaluated_count < max_total_evaluations:
        params = {
            "query": query,
            "per_page": num_candidates_per_page,
            "orientation": orientation,
            "page": current_page
        }

        try:
            response = requests.get(PEXELS_VIDEO_SEARCH_URL, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Pexels page {current_page} for query 	'{query}'	: {e}")
            # Stop searching if there's an API error
            break 
        except Exception as e:
            logger.exception(f"An unexpected error occurred during Pexels search on page {current_page}: {e}")
            break

        candidate_videos_on_page = []
        for video in data.get("videos", []):
            best_link = None
            max_width = 0
            for vf in video.get("video_files", []):
                target_width = 1920
                if vf.get("file_type") == "video/mp4":
                    current_width = vf.get("width", 0)
                    if current_width > max_width:
                         max_width = current_width
                         best_link = vf.get("link")
                    elif best_link and abs(current_width - target_width) < abs(max_width - target_width):
                         max_width = current_width
                         best_link = vf.get("link")
            if best_link:
                candidate_videos_on_page.append(best_link)

        if not candidate_videos_on_page:
            logger.warning(f"No more video candidates found on Pexels for query: 	'{query}'	 on page {current_page}.")
            break # No more videos on subsequent pages

        logger.info(f"Evaluating {len(candidate_videos_on_page)} candidates (Page {current_page}) for scene: 	'{scene_text[:50]}...' (Total evaluated: {evaluated_count})")
        
        page_best_url = None
        page_highest_score = -1.0

        for video_url in candidate_videos_on_page:
            evaluated_count += 1
            if evaluated_count > max_total_evaluations:
                logger.warning(f"Reached max candidate evaluation limit ({max_total_evaluations}). Stopping search.")
                break 

            # *** Check if URL is already used ***
            if video_url in used_urls:
                logger.info(f"  - Skipping used candidate: {video_url}")
                continue

            evaluation = evaluator.evaluate_visual(video_url, scene_text)
            evaluation_results.append({"url": video_url, "evaluation": evaluation})
            logger.info(f"  - Candidate: {video_url}, Score: {evaluation.get('overall_score')}, Notes: {evaluation.get('evaluation_notes')}")
            
            is_safe = not evaluation.get("safety_flags") or "check_failed" in evaluation.get("safety_flags")
            current_score = evaluation.get("overall_score", 0.0)
            
            MIN_ACCEPTABLE_SCORE = 0.5 
            # *** Track the best *new* video found *so far* across all pages ***
            if is_safe and current_score > highest_score and current_score >= MIN_ACCEPTABLE_SCORE:
                highest_score = current_score
                best_video_url = video_url # Update overall best
                logger.info(f"    -> New best candidate found: {video_url} (Score: {highest_score})")
            
            # Track best on current page just for info, not strictly needed for logic
            if is_safe and current_score > page_highest_score and current_score >= MIN_ACCEPTABLE_SCORE:
                 page_highest_score = current_score
                 page_best_url = video_url

        if evaluated_count >= max_total_evaluations:
            break # Exit outer loop if max evaluations reached during inner loop

        current_page += 1 # Move to the next page

    # After checking all pages/candidates up to limits
    if best_video_url:
        logger.info(f"Selected best unique video: {best_video_url} with score {highest_score}")
    else:
        logger.warning(f"No suitable *unique* video found after evaluation for query: 	'{query}'")
        # logger.debug(f"Evaluation details: {evaluation_results}")

    return best_video_url

# Keep the old function for compatibility or direct use if needed, but mark as potentially deprecated
def search_pexels_videos(query: str, per_page: int = 1, orientation: str = "landscape") -> list[str]:
    """DEPRECATED: Use search_and_evaluate_pexels_videos instead.
    Searches for videos on Pexels based on a query.
    Returns a list of video URLs without evaluation.
    """
    # ... (implementation remains the same) ...
    logger.warning("Using deprecated search_pexels_videos. Consider search_and_evaluate_pexels_videos.")
    if not PEXELS_API_KEY:
        logger.error("PEXELS_API_KEY not found in environment variables. Cannot search Pexels.")
        return []

    headers = {
        "Authorization": PEXELS_API_KEY
    }
    params = {
        "query": query,
        "per_page": per_page,
        "orientation": orientation,
    }

    try:
        response = requests.get(PEXELS_VIDEO_SEARCH_URL, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        video_urls = []
        for video in data.get("videos", []):
            best_link = None
            max_width = 0
            for vf in video.get("video_files", []):
                if vf.get("file_type") == "video/mp4" and vf.get("width", 0) > max_width:
                    max_width = vf["width"]
                    best_link = vf.get("link")
            if best_link:
                video_urls.append(best_link)
                
        return video_urls

    except requests.exceptions.RequestException as e:
        logger.error(f"Error searching Pexels videos for query 	'{query}'	: {e}")
        return []
    except Exception as e:
        logger.error(f"An unexpected error occurred during Pexels search: {e}")
        return []

# Placeholder for Pixabay integration if needed
def search_pixabay_videos(query: str) -> list[str]:
    """Searches for videos on Pixabay."""
    # Implementation needed - requires Pixabay API key and integration
    logger.warning("Pixabay integration is not yet implemented.")
    return []

