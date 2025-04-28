import os
import logging
from django.conf import settings
from django.db import transaction
from django.core.files.base import ContentFile

from .models import Scene, Module
from .video_utils import search_pexels_videos
from .tts_utils import generate_voiceover, save_voiceover
from .openai_utils import generate_voiceover_text

logger = logging.getLogger(__name__)

def generate_scene_content(scene_id):
    """
    Generate background video and voiceover for a scene.
    
    Args:
        scene_id: The ID of the scene to process
        
    Returns:
        dict: Status of the operation with details
    """
    try:
        scene = Scene.objects.get(pk=scene_id)
    except Scene.DoesNotExist:
        logger.error(f"Scene with ID {scene_id} not found")
        return {"success": False, "error": f"Scene with ID {scene_id} not found"}
    
    module = scene.module
    course = module.course
    
    # Generate search terms based on visual description
    search_terms = scene.visual_description[:100]  # Limit length for API
    
    # Get background video from Pexels
    video_urls = search_pexels_videos(search_terms, per_page=1)
    if not video_urls:
        logger.warning(f"No videos found for scene {scene_id} with search terms: {search_terms}")
        # Could try alternative search terms or fallback strategy here
    else:
        # Update the scene with the video URL
        scene.background_video_url = video_urls[0]
        scene.save(update_fields=["background_video_url"])
    
    # Generate optimized voiceover text if needed
    voiceover_text = scene.voiceover_text
    if voiceover_text:
        optimized_text = generate_voiceover_text(voiceover_text, course.language)
        if optimized_text and not optimized_text.startswith("Error:"):
            # Only update if optimization was successful
            scene.voiceover_text = optimized_text
            scene.save(update_fields=["voiceover_text"])
    
    # Generate voiceover audio
    if scene.voiceover_text:
        # Select voice based on course settings (could be customized)
        voice = "alloy"  # Default voice
        
        # Generate the audio file
        temp_path, audio_data = generate_voiceover(scene.voiceover_text, voice)
        
        if temp_path and audio_data:
            # Save to media storage
            file_name = f"scene_{scene.id}_voiceover.mp3"
            content_file = ContentFile(audio_data)
            
            # Save to the model's FileField
            scene.voiceover_audio_file.save(file_name, content_file, save=True)
            
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"Failed to delete temporary file {temp_path}: {e}")
                
            return {
                "success": True, 
                "scene_id": scene.id,
                "video_url": scene.background_video_url,
                "audio_file": scene.voiceover_audio_file.url if scene.voiceover_audio_file else None
            }
        else:
            return {"success": False, "error": "Failed to generate voiceover audio"}
    else:
        return {"success": False, "error": "No voiceover text available for the scene"}

@transaction.atomic
def process_module_scenes(module_id):
    """
    Process all scenes in a module to generate videos and voiceovers.
    
    Args:
        module_id: The ID of the module to process
        
    Returns:
        dict: Status of the operation with details
    """
    try:
        module = Module.objects.get(pk=module_id)
    except Module.DoesNotExist:
        logger.error(f"Module with ID {module_id} not found")
        return {"success": False, "error": f"Module with ID {module_id} not found"}
    
    scenes = module.scenes.all().order_by('scene_number')
    if not scenes:
        return {"success": False, "error": "No scenes found for this module"}
    
    results = []
    for scene in scenes:
        result = generate_scene_content(scene.id)
        results.append(result)
    
    success_count = sum(1 for r in results if r.get("success", False))
    
    return {
        "success": success_count > 0,
        "module_id": module_id,
        "total_scenes": len(results),
        "successful_scenes": success_count,
        "scene_results": results
    }
