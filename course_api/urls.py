from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import avatar_views # Import avatar views
from . import render_views # Import render views

router = DefaultRouter()
router.register(r'courses', views.CourseViewSet)
router.register(r'modules', views.ModuleViewSet)
router.register(r'avatars', views.AvatarViewSet)

# Define urlpatterns for specific actions and views
urlpatterns = [
    # Router URLs for standard ViewSet actions
    path('', include(router.urls)),
    
    # Course specific avatar setting
    path('courses/<uuid:course_pk>/avatar/', views.CourseAvatarView.as_view(), name='course-avatar'),
    
    # Avatar creation and management URLs from avatar_views
    path('avatars/create/', avatar_views.create_avatar, name='create-avatar'),
    path('avatars/training/<uuid:avatar_id>/', avatar_views.check_avatar_training, name='check-avatar-training'),
    path('avatars/list/', avatar_views.list_avatars, name='list-avatars'),
    
    # Video rendering URLs from render_views
    path('scenes/<uuid:scene_id>/render/', render_views.render_scene, name='render-scene'),
    path('modules/<uuid:module_id>/render/', render_views.render_module, name='render-module'),
    path('render/status/<str:task_id>/', render_views.check_render_status, name='check-render-status'),
]

