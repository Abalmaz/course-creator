from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
import json
import os
import logging

from .models import Avatar, CourseAvatar
from .avatar_utils import HeyGenAvatarManager

logger = logging.getLogger(__name__)

@csrf_exempt
@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def create_avatar(request):
    """
    API endpoint to create a custom avatar using HeyGen API.
    
    Requires:
    - avatar_image: Image file for avatar creation
    - name: Name for the avatar
    
    Returns:
    - Avatar details including ID and status
    """
    if 'avatar_image' not in request.FILES:
        return Response({"error": "No avatar image provided"}, status=status.HTTP_400_BAD_REQUEST)
    
    if 'name' not in request.data:
        return Response({"error": "No avatar name provided"}, status=status.HTTP_400_BAD_REQUEST)
    
    avatar_image = request.FILES['avatar_image']
    avatar_name = request.data['name']
    
    # Save the uploaded image temporarily
    temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, avatar_image.name)
    
    with open(temp_path, 'wb+') as destination:
        for chunk in avatar_image.chunks():
            destination.write(chunk)
    
    # Create the avatar using HeyGen API
    avatar_manager = HeyGenAvatarManager()
    result = avatar_manager.create_photo_avatar(temp_path, avatar_name)
    
    # Clean up the temporary file
    try:
        os.remove(temp_path)
    except Exception as e:
        logger.warning(f"Failed to remove temporary file {temp_path}: {e}")
    
    if "error" in result:
        return Response({"error": result["error"]}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Start training the avatar model
    photo_avatar_id = result.get("id")
    if not photo_avatar_id:
        return Response({"error": "No photo avatar ID returned from API"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    training_result = avatar_manager.train_avatar_model(photo_avatar_id, avatar_name)
    
    if "error" in training_result:
        return Response({"error": training_result["error"]}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Save avatar information to database
    try:
        avatar = Avatar.objects.create(
            name=avatar_name,
            api_reference_id=photo_avatar_id,
            # Save the original image to our system
            image=avatar_image
        )
        
        return Response({
            "id": str(avatar.id),
            "name": avatar.name,
            "api_reference_id": avatar.api_reference_id,
            "image_url": avatar.image.url if avatar.image else None,
            "created_at": avatar.created_at,
            "training_status": training_result
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error saving avatar to database: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def check_avatar_training(request, avatar_id):
    """
    Check the training status of an avatar.
    
    Args:
        avatar_id: ID of the avatar in our system
        
    Returns:
        Training status from HeyGen API
    """
    try:
        avatar = Avatar.objects.get(pk=avatar_id)
    except Avatar.DoesNotExist:
        return Response({"error": "Avatar not found"}, status=status.HTTP_404_NOT_FOUND)
    
    # Get the training status from HeyGen API
    avatar_manager = HeyGenAvatarManager()
    result = avatar_manager.check_avatar_training_status(avatar.api_reference_id)
    
    if "error" in result:
        return Response({"error": result["error"]}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response({
        "id": str(avatar.id),
        "name": avatar.name,
        "training_status": result
    })

@api_view(['GET'])
def list_avatars(request):
    """
    List all available avatars, both from our database and HeyGen API.
    
    Returns:
        Combined list of avatars
    """
    # Get avatars from our database
    local_avatars = Avatar.objects.all()
    local_avatar_data = [{
        "id": str(avatar.id),
        "name": avatar.name,
        "image_url": avatar.image.url if avatar.image else None,
        "created_at": avatar.created_at,
        "source": "local"
    } for avatar in local_avatars]
    
    # Get avatars from HeyGen API
    avatar_manager = HeyGenAvatarManager()
    api_result = avatar_manager.list_available_avatars()
    
    api_avatars = []
    if "error" not in api_result:
        # Format the API avatars to match our structure
        api_avatars = [{
            "id": avatar.get("id"),
            "name": avatar.get("name"),
            "image_url": avatar.get("preview_url"),
            "source": "heygen"
        } for avatar in api_result.get("data", [])]
    
    # Combine the results
    return Response({
        "local_avatars": local_avatar_data,
        "api_avatars": api_avatars
    })

# Add these URLs to your urls.py
urlpatterns = [
    path('avatars/create/', create_avatar, name='create-avatar'),
    path('avatars/training/<uuid:avatar_id>/', check_avatar_training, name='check-avatar-training'),
    path('avatars/list/', list_avatars, name='list-avatars'),
]
