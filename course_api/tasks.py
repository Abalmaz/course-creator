import os
import requests
import tempfile
import logging
from celery import shared_task
from moviepy.editor import (
    VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, concatenate_videoclips
)
from django.conf import settings
from django.core.files.base import ContentFile

from .models import Scene, Module
from .avatar_utils import HeyGenAvatarManager

logger = logging.getLogger(__name__)

@shared_task
def render_scene_video(scene_id):
    """
    Celery task to render a single scene video using MoviePy.
    Combines background video, voiceover, and text overlay.
    Optionally uses an avatar video if available.
    """
    try:
        scene = Scene.objects.get(pk=scene_id)
    except Scene.DoesNotExist:
        logger.error(f"Scene {scene_id} not found for rendering.")
        return {"success": False, "error": f"Scene {scene_id} not found"}

    # --- Get Required Assets --- 
    voiceover_path = None
    background_video_path = None
    avatar_video_path = None
    final_video_path = None
    temp_files = []

    try:
        # 1. Voiceover Audio
        if not scene.voiceover_audio_file:
            logger.error(f"No voiceover audio file for scene {scene_id}")
            return {"success": False, "error": "Missing voiceover audio"}
        voiceover_path = scene.voiceover_audio_file.path
        if not os.path.exists(voiceover_path):
             logger.error(f"Voiceover file not found at {voiceover_path} for scene {scene_id}")
             return {"success": False, "error": "Voiceover file not found"}
        audio_clip = AudioFileClip(voiceover_path)
        video_duration = audio_clip.duration

        # 2. Background Video (or Avatar Video)
        use_avatar = False
        course_avatar = getattr(scene.module.course, "courseavatar", None)
        if course_avatar and course_avatar.avatar:
            # TODO: Implement logic to get the rendered avatar video from HeyGen
            # This might involve calling HeyGen API to generate video with avatar + voice
            # For now, we assume avatar_video_url is populated if avatar is used
            if scene.avatar_video_url: # Assuming a field `avatar_video_url` exists on Scene
                logger.info(f"Using avatar video for scene {scene_id}")
                use_avatar = True
                # Download avatar video
                response = requests.get(scene.avatar_video_url, stream=True)
                response.raise_for_status()
                temp_avatar_video = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                for chunk in response.iter_content(chunk_size=8192):
                    temp_avatar_video.write(chunk)
                avatar_video_path = temp_avatar_video.name
                temp_avatar_video.close()
                temp_files.append(avatar_video_path)
                video_clip = VideoFileClip(avatar_video_path).subclip(0, video_duration)
            else:
                logger.warning(f"Course has avatar but no avatar video URL for scene {scene_id}. Falling back to background video.")

        if not use_avatar:
            if not scene.background_video_url:
                logger.error(f"No background video URL for scene {scene_id}")
                # TODO: Handle missing background - maybe use a solid color?
                return {"success": False, "error": "Missing background video"}
            
            # Download background video
            response = requests.get(scene.background_video_url, stream=True)
            response.raise_for_status()
            temp_bg_video = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            for chunk in response.iter_content(chunk_size=8192):
                temp_bg_video.write(chunk)
            background_video_path = temp_bg_video.name
            temp_bg_video.close()
            temp_files.append(background_video_path)
            video_clip = VideoFileClip(background_video_path).subclip(0, video_duration)
            # Resize if needed, ensure aspect ratio matches target (e.g., 16:9)
            # video_clip = video_clip.resize(height=720) # Example resize

        # --- Create Text Overlay --- 
        clips_to_composite = [video_clip]
        if scene.on_screen_text:
            # Customize text appearance (font, size, color, position)
            txt_clip = TextClip(
                scene.on_screen_text,
                fontsize=40, 
                color=\'white\',
                font=\'Arial-Bold\', # Ensure font is available on the system
                bg_color=\'black\', # Optional background for readability
                size=(video_clip.w * 0.8, None), # Width relative to video
                method=\'caption\' # Auto-wrap text
            )
            txt_clip = txt_clip.set_position((\'center\', \'bottom\')).set_duration(video_duration)
            clips_to_composite.append(txt_clip)

        # --- Composite Video and Add Audio --- 
        final_clip = CompositeVideoClip(clips_to_composite)
        final_clip = final_clip.set_audio(audio_clip)
        final_clip = final_clip.set_duration(video_duration)

        # --- Save Final Video --- 
        output_dir = os.path.join(settings.MEDIA_ROOT, "rendered_videos", str(scene.module.id))
        os.makedirs(output_dir, exist_ok=True)
        output_filename = f"scene_{scene.id}_rendered.mp4"
        final_video_path = os.path.join(output_dir, output_filename)
        
        # Render the video (codec, bitrate, etc. can be specified)
        final_clip.write_videofile(final_video_path, codec="libx264", audio_codec="aac", threads=4, logger=\'bar\')

        # --- Update Scene Model --- 
        # Save the relative path to the media root
        relative_path = os.path.relpath(final_video_path, settings.MEDIA_ROOT)
        scene.rendered_video_file.name = relative_path
        scene.save(update_fields=["rendered_video_file"])

        logger.info(f"Successfully rendered video for scene {scene_id} to {final_video_path}")
        return {"success": True, "scene_id": scene_id, "output_path": final_video_path}

    except Exception as e:
        logger.exception(f"Error rendering video for scene {scene_id}: {e}")
        return {"success": False, "error": str(e)}
    finally:
        # Clean up temporary files
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                logger.warning(f"Failed to remove temporary file {temp_file}: {e}")
        # Close MoviePy clips to release resources
        if \'audio_clip\' in locals() and audio_clip: audio_clip.close()
        if \'video_clip\' in locals() and video_clip: video_clip.close()
        if \'txt_clip\' in locals() and txt_clip: txt_clip.close()
        if \'final_clip\' in locals() and final_clip: final_clip.close()

@shared_task
def render_module_video(module_id):
    """
    Celery task to render the full video for a module by concatenating scene videos.
    """
    try:
        module = Module.objects.get(pk=module_id)
    except Module.DoesNotExist:
        logger.error(f"Module {module_id} not found for final rendering.")
        return {"success": False, "error": f"Module {module_id} not found"}

    scenes = module.scenes.filter(rendered_video_file__isnull=False).exclude(rendered_video_file=\'\').order_by(\'scene_number\')
    
    if not scenes.exists():
        logger.error(f"No rendered scenes found for module {module_id}")
        return {"success": False, "error": "No rendered scenes to concatenate"}

    scene_clips = []
    final_video_path = None
    try:
        for scene in scenes:
            scene_video_path = os.path.join(settings.MEDIA_ROOT, scene.rendered_video_file.name)
            if os.path.exists(scene_video_path):
                scene_clips.append(VideoFileClip(scene_video_path))
            else:
                logger.warning(f"Rendered video file not found for scene {scene.id} at {scene_video_path}")
        
        if not scene_clips:
             logger.error(f"No valid scene video files found for module {module_id}")
             return {"success": False, "error": "No valid scene files"}

        final_module_clip = concatenate_videoclips(scene_clips, method="compose")

        # Save final module video
        output_dir = os.path.join(settings.MEDIA_ROOT, "rendered_videos")
        os.makedirs(output_dir, exist_ok=True)
        output_filename = f"module_{module.id}_final.mp4"
        final_video_path = os.path.join(output_dir, output_filename)
        
        final_module_clip.write_videofile(final_video_path, codec="libx264", audio_codec="aac", threads=4, logger=\'bar\')

        # Update Module Model
        relative_path = os.path.relpath(final_video_path, settings.MEDIA_ROOT)
        module.final_video_file.name = relative_path
        module.save(update_fields=["final_video_file"])

        logger.info(f"Successfully rendered final video for module {module_id} to {final_video_path}")
        return {"success": True, "module_id": module_id, "output_path": final_video_path}

    except Exception as e:
        logger.exception(f"Error concatenating videos for module {module_id}: {e}")
        return {"success": False, "error": str(e)}
    finally:
        # Close MoviePy clips
        for clip in scene_clips:
            clip.close()
        if \'final_module_clip\' in locals() and final_module_clip: final_module_clip.close()

