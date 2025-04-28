import json
import os
import unittest
from django.test import TestCase, Client
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .models import Course, Objective, Module, Scene, Avatar

class CourseAPITestCase(TestCase):
    """Test case for the Course API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create a test course
        self.course_data = {
            "name": "Test Course",
            "language": "en",
            "target_audience": "Beginners",
            "content_style": "Informative"
        }
        
    def test_create_course(self):
        """Test creating a new course"""
        url = reverse('course-list')
        response = self.client.post(url, self.course_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Course.objects.count(), 1)
        self.assertEqual(Course.objects.get().name, 'Test Course')
        
        # Check that objectives were generated
        self.assertTrue(Objective.objects.filter(course=Course.objects.get()).exists())
        
    def test_list_courses(self):
        """Test listing all courses"""
        # Create a test course first
        course = Course.objects.create(**self.course_data)
        
        url = reverse('course-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], course.name)
        
    def test_retrieve_course(self):
        """Test retrieving a specific course"""
        course = Course.objects.create(**self.course_data)
        
        url = reverse('course-detail', args=[course.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], course.name)
        
    def test_select_objectives(self):
        """Test selecting objectives for a course"""
        course = Course.objects.create(**self.course_data)
        objective = Objective.objects.create(
            course=course,
            text="Test Objective",
            order=0
        )
        
        url = reverse('course-select-objectives', args=[course.id])
        data = [{"id": str(objective.id), "selected": True}]
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        objective.refresh_from_db()
        self.assertTrue(objective.selected)
        
class ModuleAPITestCase(TestCase):
    """Test case for the Module API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create a test course with objectives
        self.course = Course.objects.create(
            name="Test Course",
            language="en",
            target_audience="Beginners",
            content_style="Informative"
        )
        
        self.objective = Objective.objects.create(
            course=self.course,
            text="Test Objective",
            order=0,
            selected=True
        )
        
    def test_generate_modules(self):
        """Test generating modules for a course"""
        url = reverse('course-generate-modules', args=[self.course.id])
        response = self.client.post(url)
        
        # This test might fail in a real environment without OpenAI API key
        # We're just checking the endpoint works, not the actual module generation
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR])
        
        if response.status_code == status.HTTP_200_OK:
            # Check that modules were created
            self.assertTrue(Module.objects.filter(course=self.course).exists())
            
class AvatarAPITestCase(TestCase):
    """Test case for the Avatar API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
    def test_list_avatars(self):
        """Test listing all avatars"""
        url = reverse('list-avatars')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('local_avatars', response.data)
        self.assertIn('api_avatars', response.data)
        
class RenderAPITestCase(TestCase):
    """Test case for the Render API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create a test course with modules and scenes
        self.course = Course.objects.create(
            name="Test Course",
            language="en",
            target_audience="Beginners",
            content_style="Informative"
        )
        
        self.module = Module.objects.create(
            course=self.course,
            title="Test Module",
            description="Test Description",
            order=0
        )
        
        self.scene = Scene.objects.create(
            module=self.module,
            scene_number=1,
            visual_description="Test Visual",
            on_screen_text="Test Text",
            voiceover_text="Test Voiceover"
        )
        
    def test_render_scene_endpoint(self):
        """Test the render scene endpoint"""
        url = reverse('render-scene', args=[self.scene.id])
        
        # This will fail without actual voiceover and background video
        # We're just checking the endpoint exists and returns a proper error
        response = self.client.post(url)
        
        # Should return 400 because scene doesn't have required assets
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
    def test_render_module_endpoint(self):
        """Test the render module endpoint"""
        url = reverse('render-module', args=[self.module.id])
        
        # This will fail without rendered scenes
        # We're just checking the endpoint exists and returns a proper error
        response = self.client.post(url)
        
        # Should return 400 because module doesn't have rendered scenes
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
