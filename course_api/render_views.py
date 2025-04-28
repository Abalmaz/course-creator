from django.urls import path
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import logging

from .models import Scene, Module
from .tasks import render_scene_video, render_module_video

logger = logging.getLogger(__name__)

@api_view(['POST'])
def render_scene(request, scene_id):
    """
    API endpoint to trigger asynchronous rendering of a scene video.
    
    Args:
        scene_id: ID of the scene to render
        
    Returns:
        Task ID and status information
    """
    try:
        scene = Scene.objects.get(pk=scene_id)
    except Scene.DoesNotExist:
        return Response({"error": f"Scene with ID {scene_id} not found"}, status=status.HTTP_404_NOT_FOUND)
    
    # Check if scene has required assets
    if not scene.voiceover_audio_file:
        return Response({"error": "Scene has no voiceover audio file"}, status=status.HTTP_400_BAD_REQUEST)
    
    if not scene.background_video_url and not scene.avatar_video_url:
        return Response({"error": "Scene has no background video or avatar video"}, status=status.HTTP_400_BAD_REQUEST)
    
    # Trigger the Celery task
    task = render_scene_video.delay(scene_id)
    
    return Response({
        "task_id": task.id,
        "status": "rendering",
        "scene_id": scene_id
    })

@api_view(['POST'])
def render_module(request, module_id):
    """
    API endpoint to trigger asynchronous rendering of a complete module video.
    
    Args:
        module_id: ID of the module to render
        
    Returns:
        Task ID and status information
    """
    try:
        module = Module.objects.get(pk=module_id)
    except Module.DoesNotExist:
        return Response({"error": f"Module with ID {module_id} not found"}, status=status.HTTP_404_NOT_FOUND)
    
    # Check if module has rendered scenes
    scenes = module.scenes.filter(rendered_video_file__isnull=False).exclude(rendered_video_file='')
    if not scenes.exists():
        return Response({
            "error": "No rendered scenes found for this module. Render individual scenes first.",
            "scene_count": module.scenes.count(),
            "rendered_scene_count": scenes.count()
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Trigger the Celery task
    task = render_module_video.delay(module_id)
    
    return Response({
        "task_id": task.id,
        "status": "rendering",
        "module_id": module_id,
        "scene_count": scenes.count()
    })

@api_view(['GET'])
def check_render_status(request, task_id):
    """
    API endpoint to check the status of a rendering task.
    
    Args:
        task_id: ID of the Celery task
        
    Returns:
        Task status information
    """
    from celery.result import AsyncResult
    
    task_result = AsyncResult(task_id)
    
    result = {
        "task_id": task_id,
        "status": task_result.status,
    }
    
    if task_result.successful():
        result["result"] = task_result.result
    elif task_result.failed():
        result["error"] = str(task_result.result)
    
    return Response(result)

# Add these URLs to your urls.py
urlpatterns = [
    path('scenes/<uuid:scene_id>/render/', render_scene, name='render-scene'),
    path('modules/<uuid:module_id>/render/', render_module, name='render-module'),
    path('render/status/<str:task_id>/', check_render_status, name='check-render-status'),
]
