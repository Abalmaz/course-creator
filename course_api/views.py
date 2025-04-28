from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
import json

from .models import Course, Objective, Module, Scene, KnowledgeCheck, Question, Option, Avatar, CourseAvatar
from .serializers import (
    CourseSerializer, CourseCreateSerializer, ObjectiveSerializer, 
    ModuleSerializer, SceneSerializer, KnowledgeCheckSerializer, 
    QuestionSerializer, OptionSerializer, AvatarSerializer, CourseAvatarSerializer
)
from .openai_utils import (
    generate_course_objectives, generate_module_description, 
    generate_video_script, generate_knowledge_check
)

class CourseViewSet(viewsets.ModelViewSet):
    """ViewSet for managing Courses"""
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    parser_classes = (MultiPartParser, FormParser) # To handle file uploads

    def get_serializer_class(self):
        if self.action == 'create':
            return CourseCreateSerializer
        return CourseSerializer

    def perform_create(self, serializer):
        """Handle Step 1: Create Course and Generate Objectives"""
        # Save the initial course data
        course = serializer.save()
        
        # Read document content if provided
        document_content = None
        if course.documents:
            try:
                with course.documents.open("r") as f:
                    # TODO: Handle different file types (pdf, docx etc.) - currently assumes text
                    document_content = f.read()
            except Exception as e:
                # Log error, but continue without document content
                print(f"Error reading document {course.documents.name}: {e}")

        # Generate objectives using OpenAI
        objectives_text = generate_course_objectives(
            course_name=course.name,
            language=course.language,
            target_audience=course.target_audience,
            content_style=course.content_style,
            documents=document_content
        )

        # Create Objective instances
        for i, text in enumerate(objectives_text):
            if not text.startswith("Error:"):
                Objective.objects.create(course=course, text=text, order=i)
            else:
                # Handle potential error during objective generation (e.g., log it)
                print(f"Error generating objective {i+1} for course {course.id}: {text}")
                # Optionally, create a placeholder objective or raise an error

        # Associate the generated objectives back to the serializer instance for the response
        # We need to re-fetch the course to include the objectives in the response
        self.instance = Course.objects.get(pk=course.pk)
        serializer = self.get_serializer(self.instance)
        # Override the response data with the full CourseSerializer including objectives
        self.headers = self.get_success_headers(serializer.data)
        # Manually set the response data because perform_create doesn't return it directly
        # This is a bit hacky, might need refinement depending on DRF version/patterns
        # A better way might be to override the create method entirely.

    # Override create to return the full CourseSerializer data
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        # Use the serializer instance updated in perform_create
        updated_serializer = self.get_serializer(self.instance)
        headers = self.get_success_headers(updated_serializer.data)
        return Response(updated_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=["post"], url_path=\"generate-modules\")
    def generate_modules(self, request, pk=None):
        """Handle Step 2: Generate Modules and Video Content based on selected Objectives"""
        course = self.get_object()
        selected_objectives = course.objectives.filter(selected=True).order_by("order")

        if not selected_objectives.exists():
            return Response({"error": "No objectives selected for module generation."}, status=status.HTTP_400_BAD_REQUEST)

        course_context = {
            "name": course.name,
            "language": course.language,
            "target_audience": course.target_audience,
            "content_style": course.content_style
        }

        for i, objective in enumerate(selected_objectives):
            # Generate Module Description
            module_description = generate_module_description(objective.text, course_context)
            if module_description.startswith("Error:"):
                # Handle error
                print(f"Error generating description for objective {objective.id}: {module_description}")
                continue # Skip this module
            
            module, created = Module.objects.update_or_create(
                objective=objective,
                defaults={
                    "course": course,
                    "title": f"Module {i+1}: {objective.text[:50]}...", # Generate a better title?
                    "description": module_description,
                    "order": i
                }
            )

            # Generate Video Script and Scenes
            script_data = generate_video_script(module.description, course_context)
            if "error" in script_data:
                # Handle error
                print(f"Error generating script for module {module.id}: {script_data["error"]}")
                continue # Skip scenes for this module
            
            # Clear existing scenes before adding new ones
            module.scenes.all().delete()
            
            for scene_data in script_data.get("scenes", []):
                Scene.objects.create(
                    module=module,
                    scene_number=int(scene_data.get("scene_number", "SCENE 0").split(" ")[-1]),
                    visual_description=scene_data.get("visual", ""),
                    on_screen_text=scene_data.get("text", ""),
                    voiceover_text=scene_data.get("voiceover", "")
                    # background_video_url and voiceover_audio_file will be populated later
                )

        serializer = self.get_serializer(course)
        return Response(serializer.data)

    @action(detail=True, methods=["patch"], serializer_class=ObjectiveSerializer, url_path=\"select-objectives\")
    def select_objectives(self, request, pk=None):
        """Allows updating the 'selected' status of objectives for a course."""
        course = self.get_object()
        # Expecting data like: [{ "id": "uuid", "selected": true }, ...]
        objective_updates = request.data
        if not isinstance(objective_updates, list):
            return Response({"error": "Expected a list of objective updates."}, status=status.HTTP_400_BAD_REQUEST)

        updated_ids = []
        errors = {}
        for update_data in objective_updates:
            obj_id = update_data.get("id")
            selected_status = update_data.get("selected")
            if obj_id is None or selected_status is None:
                return Response({"error": "Each update must contain 'id' and 'selected' fields."}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                objective = Objective.objects.get(id=obj_id, course=course)
                objective.selected = bool(selected_status)
                objective.save(update_fields=["selected"])
                updated_ids.append(obj_id)
            except Objective.DoesNotExist:
                errors[obj_id] = "Objective not found for this course."
            except Exception as e:
                errors[obj_id] = str(e)

        if errors:
            return Response({"error": "Some objectives could not be updated.", "details": errors}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = self.get_serializer(course)
        return Response(serializer.data)

class ModuleViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ViewSet for Modules (retrieved via Course)"""
    queryset = Module.objects.all()
    serializer_class = ModuleSerializer

    @action(detail=True, methods=["post"], url_path=\"generate-knowledge-check\")
    def generate_knowledge_check(self, request, pk=None):
        """Generate a knowledge check for a specific module"""
        module = self.get_object()
        course = module.course
        course_context = {
            "name": course.name,
            "language": course.language,
            "target_audience": course.target_audience,
            "content_style": course.content_style
        }

        # Check if knowledge check already exists
        if hasattr(module, 'knowledge_check'):
            return Response({"error": "Knowledge check already exists for this module."}, status=status.HTTP_400_BAD_REQUEST)

        quiz_data_str = generate_knowledge_check(module.description, course_context)
        
        try:
            quiz_data = json.loads(quiz_data_str) # OpenAI should return JSON
        except json.JSONDecodeError:
             # Handle case where OpenAI didn't return valid JSON
             return Response({"error": "Failed to parse knowledge check data from AI.", "raw_output": quiz_data_str}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if "error" in quiz_data:
            return Response({"error": f"Failed to generate knowledge check: {quiz_data['error']}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Create KnowledgeCheck
        knowledge_check = KnowledgeCheck.objects.create(
            module=module,
            title=f"Knowledge Check for {module.title}"
        )

        # Create Questions and Options
        for i, q_data in enumerate(quiz_data.get("questions", [])):
            question = Question.objects.create(
                knowledge_check=knowledge_check,
                question_text=q_data.get("question", ""),
                explanation=q_data.get("explanation", ""),
                order=i
            )
            correct_answer_letter = q_data.get("correct_answer", "A").upper()
            for j, opt_text in enumerate(q_data.get("options", [])):
                # Option text might be like "A. Answer text"
                letter = chr(ord("A") + j)
                text_only = opt_text.split(".", 1)[-1].strip() if len(opt_text) > 2 and opt_text[1] == "." else opt_text
                Option.objects.create(
                    question=question,
                    text=text_only,
                    is_correct=(letter == correct_answer_letter),
                    order=j
                )

        serializer = ModuleSerializer(module) # Return the updated module
        return Response(serializer.data)

class AvatarViewSet(viewsets.ModelViewSet):
    """ViewSet for managing Avatars"""
    queryset = Avatar.objects.all()
    serializer_class = AvatarSerializer
    parser_classes = (MultiPartParser, FormParser)
    # Add permissions later (e.g., IsAuthenticated)

class CourseAvatarView(generics.RetrieveUpdateAPIView):
    """API View for setting/getting the avatar for a specific course"""
    serializer_class = CourseAvatarSerializer
    queryset = CourseAvatar.objects.all()
    lookup_field = 'course_id'
    lookup_url_kwarg = 'course_pk' # Match the URL pattern

    def get_object(self):
        """Get or create the CourseAvatar instance for the given course_id"""
        course_id = self.kwargs[self.lookup_url_kwarg]
        course = get_object_or_404(Course, pk=course_id)
        obj, created = CourseAvatar.objects.get_or_create(course=course)
        return obj

