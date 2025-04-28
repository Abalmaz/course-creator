import os
import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
PEXELS_VIDEO_SEARCH_URL = "https://api.pexels.com/videos/search"

def search_pexels_videos(query: str, per_page: int = 1, orientation: str = "landscape") -> list[str]:
    """Searches for videos on Pexels based on a query.

    Args:
        query: The search term(s).
        per_page: Number of results per page (max 80).
        orientation: Desired video orientation (landscape, portrait, square).

    Returns:
        A list of video URLs (specifically the highest quality MP4 link) or an empty list if error/no results.
    """
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
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        data = response.json()
        
        video_urls = []
        for video in data.get("videos", []):
            # Find the highest quality MP4 video file link
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
        logger.error(f"Error searching Pexels videos for query 	'{query}	': {e}")
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

