from rest_framework import viewsets, status, generics
from rest_framework.decorators import action, api_view, parser_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
import json
import logging

from .models import Course, Objective, Module, Scene, KnowledgeCheck, Question, Option, Avatar, CourseAvatar
from .serializers import (
    CourseSerializer, CourseCreateSerializer, ObjectiveSerializer, 
    ModuleSerializer, SceneSerializer, KnowledgeCheckSerializer, 
    QuestionSerializer, OptionSerializer, AvatarSerializer, CourseAvatarSerializer
)
from .openai_utils import (
    generate_course_objectives, generate_module_description, 
    generate_video_script, generate_knowledge_check, generate_search_query_for_visuals
)
# Import the updated search function that handles used URLs
from .video_utils import search_and_evaluate_pexels_videos 
from .tts_utils import generate_tts_for_scene

logger = logging.getLogger(__name__)

class CourseViewSet(viewsets.ModelViewSet):
    """ViewSet for managing Courses"""
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_serializer_class(self):
        if self.action == "create":
            return CourseCreateSerializer
        return CourseSerializer

    def perform_create(self, serializer):
        """Handle Step 1: Create Course and Generate Objectives"""
        course = serializer.save()
        document_content = None
        if course.documents:
            try:
                # TODO: Handle different file types properly
                with course.documents.open("r") as f:
                    document_content = f.read()
            except Exception as e:
                logger.error(f"Error reading document {course.documents.name}: {e}")

        objectives_text = generate_course_objectives(
            course_name=course.name,
            language=course.language,
            target_audience=course.target_audience,
            content_style=course.content_style,
            documents=document_content
        )

        for i, text in enumerate(objectives_text):
            if not text.startswith("Error:"):
                Objective.objects.create(course=course, text=text, order=i)
            else:
                logger.error(f"Error generating objective {i+1} for course {course.id}: {text}")

        self.instance = Course.objects.get(pk=course.pk)
        serializer = self.get_serializer(self.instance)
        self.headers = self.get_success_headers(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        updated_serializer = self.get_serializer(self.instance)
        headers = self.get_success_headers(updated_serializer.data)
        return Response(updated_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=["post"], url_path="generate-modules")
    def generate_modules(self, request, pk=None):
        """Handle Step 2: Generate Modules, Video Content, Find Unique Visuals, and Generate TTS"""
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

        # Process each selected objective to create a module
        for i, objective in enumerate(selected_objectives):
            module_description = generate_module_description(objective.text, course_context)
            if module_description.startswith("Error:"):
                logger.error(f"Error generating description for objective {objective.id}: {module_description}")
                continue # Skip this module if description fails
            
            module, created = Module.objects.update_or_create(
                objective=objective,
                defaults={
                    "course": course,
                    "title": f"Module {i+1}: {objective.text[:50]}...",
                    "description": module_description,
                    "order": i
                }
            )

            script_data = generate_video_script(module.description, course_context)
            if "error" in script_data:
                logger.error(f"Error generating script for module {module.id}: {script_data["error"]}")
                continue # Skip scene generation if script fails
            
            # Clear existing scenes before adding new ones
            module.scenes.all().delete()
            
            # --- Track used background video URLs for this specific module --- 
            used_background_urls_for_module = set()
            
            # Process each scene within the module
            for scene_data in script_data.get("scenes", []):
                scene_text_for_context = scene_data.get("voiceover", "") or scene_data.get("text", "")
                visual_description = scene_data.get("visual", "")
                scene_number_str = scene_data.get("scene_number", "SCENE 0").split(" ")[-1]
                try:
                    scene_number = int(scene_number_str)
                except ValueError:
                    logger.warning(f"Could not parse scene number 	'{scene_number_str}	'. Defaulting to 0.")
                    scene_number = 0

                # Generate search query for visuals
                search_query = generate_search_query_for_visuals(scene_text_for_context, visual_description)
                logger.info(f"Generated search query 	'{search_query}	' for Module {module.order+1}, Scene {scene_number}")
                
                # Search and evaluate background video, avoiding used URLs
                best_video_url = None
                if search_query and not search_query.startswith("Error:"):
                    best_video_url = search_and_evaluate_pexels_videos(
                        query=search_query,
                        scene_text=scene_text_for_context,
                        used_urls=used_background_urls_for_module # Pass the set of used URLs
                        # Default candidate/page limits from video_utils will be used
                    )
                else:
                    logger.warning(f"Skipping visual search for Module {module.order+1}, Scene {scene_number} due to invalid search query.")

                # Create Scene object
                scene = Scene.objects.create(
                    module=module,
                    scene_number=scene_number,
                    visual_description=visual_description,
                    on_screen_text=scene_data.get("text", ""),
                    voiceover_text=scene_data.get("voiceover", ""),
                    background_video_url=best_video_url # Store the selected (potentially unique) video URL
                )
                
                # --- Add the selected URL to the set for this module if found --- 
                if best_video_url:
                    used_background_urls_for_module.add(best_video_url)
                    logger.info(f"Added {best_video_url} to used URLs for Module {module.order+1}")
                else:
                    logger.warning(f"No unique background video found for Module {module.order+1}, Scene {scene_number}. Background will be empty.")

                # Generate TTS for the scene (consider making this asynchronous)
                try:
                    # Assuming generate_tts_for_scene is updated or works correctly
                    tts_result = generate_tts_for_scene(scene.id)
                    if not tts_result.get("success"):
                        logger.error(f"TTS generation failed for scene {scene.id}: {tts_result.get("error")}")
                    else:
                        logger.info(f"TTS generated successfully for scene {scene.id}")
                except Exception as tts_err:
                     logger.error(f"Error calling TTS generation for scene {scene.id}: {tts_err}")

        # End of loop for scenes in a module
        # End of loop for objectives/modules

        serializer = self.get_serializer(course) # Return the updated course data
        return Response(serializer.data)

    @action(detail=True, methods=["patch"], serializer_class=ObjectiveSerializer, url_path="select-objectives")
    def select_objectives(self, request, pk=None):
        course = self.get_object()
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
    queryset = Module.objects.all()
    serializer_class = ModuleSerializer

    @action(detail=True, methods=["post"], url_path="generate-knowledge-check")
    def generate_knowledge_check(self, request, pk=None):
        module = self.get_object()
        course = module.course
        course_context = {
            "name": course.name,
            "language": course.language,
            "target_audience": course.target_audience,
            "content_style": course.content_style
        }

        if hasattr(module, "knowledge_check"):
            return Response({"error": "Knowledge check already exists for this module."}, status=status.HTTP_400_BAD_REQUEST)

        quiz_data_str = generate_knowledge_check(module.description, course_context)
        
        try:
            quiz_data = json.loads(quiz_data_str)
        except json.JSONDecodeError:
             return Response({"error": "Failed to parse knowledge check data from AI.", "raw_output": quiz_data_str}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if "error" in quiz_data:
            return Response({"error": f"Failed to generate knowledge check: {quiz_data['error']}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        knowledge_check = KnowledgeCheck.objects.create(
            module=module,
            title=f"Knowledge Check for {module.title}"
        )

        for i, q_data in enumerate(quiz_data.get("questions", [])):
            question = Question.objects.create(
                knowledge_check=knowledge_check,
                question_text=q_data.get("question", ""),
                explanation=q_data.get("explanation", ""),
                order=i
            )
            correct_answer_letter = q_data.get("correct_answer", "A").upper()
            for j, opt_text in enumerate(q_data.get("options", [])):
                letter = chr(ord("A") + j)
                text_only = opt_text.split(".", 1)[-1].strip() if len(opt_text) > 2 and opt_text[1] == "." else opt_text
                Option.objects.create(
                    question=question,
                    text=text_only,
                    is_correct=(letter == correct_answer_letter),
                    order=j
                )

        serializer = ModuleSerializer(module)
        return Response(serializer.data)

class AvatarViewSet(viewsets.ModelViewSet):
    queryset = Avatar.objects.all()
    serializer_class = AvatarSerializer
    parser_classes = (MultiPartParser, FormParser)

class CourseAvatarView(generics.RetrieveUpdateAPIView):
    serializer_class = CourseAvatarSerializer
    queryset = CourseAvatar.objects.all()
    lookup_field = "course_id"
    lookup_url_kwarg = "course_pk"

    def get_object(self):
        course_id = self.kwargs[self.lookup_url_kwarg]
        course = get_object_or_404(Course, pk=course_id)
        obj, created = CourseAvatar.objects.get_or_create(course=course)
        return obj

