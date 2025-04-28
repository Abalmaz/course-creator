import os
import requests
import logging
import json
from django.conf import settings
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)

# HeyGen API configuration
HEYGEN_API_KEY = os.environ.get('HEYGEN_API_KEY', '')
HEYGEN_API_BASE_URL = 'https://api.heygen.com/v1'

class HeyGenAvatarManager:
    """
    Manager class for HeyGen avatar creation and management.
    
    This class handles:
    1. Creating photo avatars from user uploads
    2. Training avatar models
    3. Retrieving available avatars
    4. Managing avatar metadata
    """
    
    def __init__(self, api_key=None):
        """Initialize with API key from settings or environment variable."""
        self.api_key = api_key or HEYGEN_API_KEY
        if not self.api_key:
            logger.warning("HEYGEN_API_KEY not found. Avatar creation will not work.")
        
        self.headers = {
            'X-Api-Key': self.api_key,
            'Content-Type': 'application/json'
        }
    
    def list_available_avatars(self):
        """
        List all available avatars (both stock and custom).
        
        Returns:
            dict: Response containing available avatars or error message
        """
        if not self.api_key:
            return {"error": "API key not configured"}
            
        try:
            response = requests.get(
                f"{HEYGEN_API_BASE_URL}/avatars",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error listing avatars: {e}")
            return {"error": str(e)}
    
    def create_photo_avatar(self, image_path, avatar_name):
        """
        Create a photo avatar from an image file.
        
        Args:
            image_path: Path to the image file
            avatar_name: Name for the avatar
            
        Returns:
            dict: Response containing avatar ID and status or error message
        """
        if not self.api_key:
            return {"error": "API key not configured"}
            
        if not os.path.exists(image_path):
            return {"error": f"Image file not found: {image_path}"}
            
        try:
            # First, upload the image to HeyGen
            with open(image_path, 'rb') as image_file:
                files = {'file': image_file}
                upload_headers = {
                    'X-Api-Key': self.api_key
                }
                
                upload_response = requests.post(
                    f"{HEYGEN_API_BASE_URL}/photo_avatar/photo/generate",
                    headers=upload_headers,
                    files=files,
                    data={'name': avatar_name}
                )
                upload_response.raise_for_status()
                upload_data = upload_response.json()
                
                # Return the photo avatar data
                return upload_data
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating photo avatar: {e}")
            return {"error": str(e)}
    
    def train_avatar_model(self, photo_avatar_id, avatar_name):
        """
        Train an avatar model from a photo avatar.
        
        Args:
            photo_avatar_id: ID of the photo avatar
            avatar_name: Name for the trained avatar
            
        Returns:
            dict: Response containing training status or error message
        """
        if not self.api_key:
            return {"error": "API key not configured"}
            
        try:
            payload = {
                "photo_avatar_id": photo_avatar_id,
                "name": avatar_name
            }
            
            response = requests.post(
                f"{HEYGEN_API_BASE_URL}/photo_avatar/train",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error training avatar model: {e}")
            return {"error": str(e)}
    
    def check_avatar_training_status(self, task_id):
        """
        Check the status of an avatar training task.
        
        Args:
            task_id: ID of the training task
            
        Returns:
            dict: Response containing training status or error message
        """
        if not self.api_key:
            return {"error": "API key not configured"}
            
        try:
            response = requests.get(
                f"{HEYGEN_API_BASE_URL}/photo_avatar/train/status/{task_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error checking avatar training status: {e}")
            return {"error": str(e)}
    
    def create_avatar_video(self, avatar_id, voice_id, script_text):
        """
        Create a video using an avatar.
        
        Args:
            avatar_id: ID of the avatar to use
            voice_id: ID of the voice to use
            script_text: Text for the avatar to speak
            
        Returns:
            dict: Response containing video creation status or error message
        """
        if not self.api_key:
            return {"error": "API key not configured"}
            
        try:
            payload = {
                "avatar_id": avatar_id,
                "voice_id": voice_id,
                "input_text": script_text,
                "background_color": "#ffffff"  # Optional: white background
            }
            
            response = requests.post(
                f"{HEYGEN_API_BASE_URL}/video/generate",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating avatar video: {e}")
            return {"error": str(e)}
    
    def get_video_status(self, video_id):
        """
        Check the status of a video generation task.
        
        Args:
            video_id: ID of the video
            
        Returns:
            dict: Response containing video status or error message
        """
        if not self.api_key:
            return {"error": "API key not configured"}
            
        try:
            response = requests.get(
                f"{HEYGEN_API_BASE_URL}/video/{video_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error checking video status: {e}")
            return {"error": str(e)}
