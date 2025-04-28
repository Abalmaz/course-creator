from rest_framework import serializers
from .models import Course, Objective, Module, Scene, KnowledgeCheck, Question, Option, Avatar, CourseAvatar

class ObjectiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Objective
        fields = ["id", "text", "selected", "order"]
        read_only_fields = ["id", "order"]

class CourseSerializer(serializers.ModelSerializer):
    objectives = ObjectiveSerializer(many=True, read_only=True)
    
    class Meta:
        model = Course
        fields = ["id", "name", "language", "target_audience", "content_style", "documents", "created_at", "updated_at", "objectives"]
        read_only_fields = ["id", "created_at", "updated_at", "objectives"]

class CourseCreateSerializer(serializers.ModelSerializer):
    # Use FileField for initial upload, but don't require it for subsequent updates
    documents = serializers.FileField(required=False, allow_null=True)
    
    class Meta:
        model = Course
        fields = ["name", "language", "target_audience", "content_style", "documents"]

class SceneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scene
        fields = ["id", "scene_number", "visual_description", "on_screen_text", "voiceover_text", "background_video_url", "voiceover_audio_file"]
        read_only_fields = ["id", "background_video_url", "voiceover_audio_file"]

class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ["id", "text", "is_correct", "order"]
        read_only_fields = ["id"]

class QuestionSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Question
        fields = ["id", "question_text", "explanation", "order", "options"]
        read_only_fields = ["id", "order", "options"]

class KnowledgeCheckSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    
    class Meta:
        model = KnowledgeCheck
        fields = ["id", "title", "questions"]
        read_only_fields = ["id", "questions"]

class ModuleSerializer(serializers.ModelSerializer):
    scenes = SceneSerializer(many=True, read_only=True)
    knowledge_check = KnowledgeCheckSerializer(read_only=True)
    objective = ObjectiveSerializer(read_only=True) # Show related objective details
    
    class Meta:
        model = Module
        fields = ["id", "title", "description", "order", "objective", "scenes", "knowledge_check"]
        read_only_fields = ["id", "order", "objective", "scenes", "knowledge_check"]

class AvatarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Avatar
        fields = ["id", "name", "image", "api_reference_id", "created_at"]
        read_only_fields = ["id", "api_reference_id", "created_at"]

class CourseAvatarSerializer(serializers.ModelSerializer):
    avatar = AvatarSerializer(read_only=True)
    avatar_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = CourseAvatar
        fields = ["course", "avatar", "use_avatar", "avatar_id"]
        read_only_fields = ["course", "avatar"]

    def update(self, instance, validated_data):
        avatar_id = validated_data.pop("avatar_id", None)
        instance.use_avatar = validated_data.get("use_avatar", instance.use_avatar)
        if avatar_id:
            try:
                avatar = Avatar.objects.get(id=avatar_id)
                instance.avatar = avatar
            except Avatar.DoesNotExist:
                raise serializers.ValidationError({"avatar_id": "Avatar not found."}) 
        elif instance.use_avatar: # If use_avatar is true, avatar_id must be provided or already set
             if not instance.avatar:
                 raise serializers.ValidationError({"avatar_id": "Avatar ID must be provided when use_avatar is true."}) 
        else: # If use_avatar is false, clear the avatar
            instance.avatar = None
            
        instance.save()
        return instance

