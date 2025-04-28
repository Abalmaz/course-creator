from django.db import models
import uuid
import os

def document_upload_path(instance, filename):
    """Generate a unique path for uploaded documents"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('documents', filename)

def avatar_upload_path(instance, filename):
    """Generate a unique path for uploaded avatar images"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('avatars', filename)

class Course(models.Model):
    """Model representing a video course"""
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('es', 'Spanish'),
        ('fr', 'French'),
        ('de', 'German'),
        ('zh', 'Chinese'),
        ('ja', 'Japanese'),
        ('ru', 'Russian'),
        ('ar', 'Arabic'),
        ('hi', 'Hindi'),
        ('pt', 'Portuguese'),
    ]
    
    STYLE_CHOICES = [
        ('formal', 'Formal'),
        ('conversational', 'Conversational'),
        ('technical', 'Technical'),
        ('creative', 'Creative'),
        ('motivational', 'Motivational'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default='en')
    target_audience = models.CharField(max_length=255)
    content_style = models.CharField(max_length=20, choices=STYLE_CHOICES, default='conversational')
    documents = models.FileField(upload_to=document_upload_path, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

class Objective(models.Model):
    """Model representing a learning objective for a course"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, related_name='objectives', on_delete=models.CASCADE)
    text = models.TextField()
    selected = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.course.name} - Objective {self.order + 1}"

class Module(models.Model):
    """Model representing a module within a course"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, related_name='modules', on_delete=models.CASCADE)
    objective = models.OneToOneField(Objective, related_name='module', on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.course.name} - {self.title}"

class Scene(models.Model):
    """Model representing a scene within a module video"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module = models.ForeignKey(Module, related_name='scenes', on_delete=models.CASCADE)
    scene_number = models.PositiveIntegerField()
    visual_description = models.TextField()
    on_screen_text = models.TextField()
    voiceover_text = models.TextField()
    background_video_url = models.URLField(blank=True, null=True)
    voiceover_audio_file = models.FileField(upload_to='voiceovers', blank=True, null=True)
    
    class Meta:
        ordering = ['scene_number']
    
    def __str__(self):
        return f"{self.module.title} - Scene {self.scene_number}"

class KnowledgeCheck(models.Model):
    """Model representing a knowledge check quiz for a module"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module = models.OneToOneField(Module, related_name='knowledge_check', on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    
    def __str__(self):
        return f"Knowledge Check: {self.module.title}"

class Question(models.Model):
    """Model representing a question in a knowledge check"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    knowledge_check = models.ForeignKey(KnowledgeCheck, related_name='questions', on_delete=models.CASCADE)
    question_text = models.TextField()
    explanation = models.TextField()
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"Question {self.order + 1} for {self.knowledge_check}"

class Option(models.Model):
    """Model representing an answer option for a question"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(Question, related_name='options', on_delete=models.CASCADE)
    text = models.TextField()
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"Option {self.order + 1} for {self.question}"

class Avatar(models.Model):
    """Model representing a user avatar for videos"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to=avatar_upload_path)
    api_reference_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class CourseAvatar(models.Model):
    """Model representing the association between a course and an avatar"""
    course = models.OneToOneField(Course, related_name='course_avatar', on_delete=models.CASCADE)
    avatar = models.ForeignKey(Avatar, related_name='courses', on_delete=models.SET_NULL, null=True)
    use_avatar = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.course.name} - {self.avatar.name if self.avatar else 'No Avatar'}"
