import os
from openai import OpenAI
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Initialize OpenAI client
# Ensure OPENAI_API_KEY is set as an environment variable
# or configure it directly if needed for testing (not recommended for production)
client = None
if settings.OPENAI_API_KEY:
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
else:
    logger.warning("OPENAI_API_KEY not found in environment variables. OpenAI integration will not work.")

def generate_course_objectives(course_name: str, language: str, target_audience: str, content_style: str, documents=None) -> list[str]:
    """Generates learning objectives for a course using OpenAI.
    
    Args:
        course_name: The title of the course
        language: The language for the course content
        target_audience: The intended audience for the course
        content_style: The style of content presentation
        documents: Optional text from documents provided by the user
        
    Returns:
        A list of 5 learning objectives
    """
    if not client:
        logger.error("OpenAI client not initialized. Cannot generate objectives.")
        return ["Error: OpenAI client not initialized. Check API key configuration."]

    document_context = ""
    if documents:
        document_context = f"The following documents were provided as reference material: {documents}\n"
        
    prompt = (
        f"Generate 5 distinct learning objectives for an online video course titled '{course_name}'. "
        f"The course is intended for '{target_audience}' and should be presented in a '{content_style}' style. "
        f"The course language is {language}. "
        f"{document_context}"
        f"Each objective should clearly state what the learner will be able to do after completing the relevant module(s). "
        f"Format the output as a numbered list, with each objective on a new line."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Or another suitable model
            messages=[
                {"role": "system", "content": "You are an expert instructional designer tasked with creating clear and actionable learning objectives for online courses."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            n=1,
            stop=None,
            temperature=0.7,
        )
        content = response.choices[0].message.content.strip()
        # Parse the numbered list response into a list of strings
        objectives = [obj.strip() for obj in content.split('\n') if obj.strip() and obj.strip()[0].isdigit()]
        # Remove the leading number and period/parenthesis
        objectives = [obj.split('.', 1)[-1].split(')', 1)[-1].strip() for obj in objectives]
        return objectives[:5] # Ensure only 5 objectives are returned
    except Exception as e:
        logger.error(f"Error generating course objectives from OpenAI: {e}")
        return [f"Error generating objectives: {e}"]

def generate_module_description(objective: str, course_context: dict) -> str:
    """Generates a module description based on an objective.
    
    Args:
        objective: The learning objective for this module
        course_context: Dictionary containing course details (name, language, audience, style)
        
    Returns:
        A detailed module description
    """
    if not client:
        logger.error("OpenAI client not initialized. Cannot generate module description.")
        return "Error: OpenAI client not initialized. Check API key configuration."

    course_name = course_context.get('name', 'the course')
    language = course_context.get('language', 'English')
    target_audience = course_context.get('target_audience', 'learners')
    content_style = course_context.get('content_style', 'educational')
    
    prompt = (
        f"Create a detailed module description for a course titled '{course_name}' in {language}. "
        f"This module addresses the following learning objective: '{objective}'. "
        f"The target audience is {target_audience} and the content style should be {content_style}. "
        f"The description should be 150-200 words and include: "
        f"1. An engaging introduction to the topic "
        f"2. Key concepts that will be covered "
        f"3. Why this module is important for the learner "
        f"4. How it connects to the overall course objective"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert curriculum designer who creates engaging and informative module descriptions for online courses."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            n=1,
            stop=None,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error generating module description from OpenAI: {e}")
        return f"Error generating module description: {e}"

def generate_video_script(module_description: str, course_context: dict) -> dict:
    """Generates a video script for a 3-minute video based on module description.
    
    Args:
        module_description: The description of the module
        course_context: Dictionary containing course details
        
    Returns:
        A dictionary containing scenes, each with text content and scene description
    """
    if not client:
        logger.error("OpenAI client not initialized. Cannot generate video script.")
        return {"error": "OpenAI client not initialized. Check API key configuration."}

    course_name = course_context.get('name', 'the course')
    language = course_context.get('language', 'English')
    target_audience = course_context.get('target_audience', 'learners')
    content_style = course_context.get('content_style', 'educational')
    
    prompt = (
        f"Create a script for a 3-minute educational video based on the following module description:\n\n"
        f"'{module_description}'\n\n"
        f"The video is part of the course '{course_name}' in {language}, targeting {target_audience} "
        f"with a {content_style} style. "
        f"Structure the script as 5-7 distinct scenes. For each scene, provide:\n"
        f"1. Scene description (visual setting, background elements, mood)\n"
        f"2. On-screen text (concise key points that appear on screen)\n"
        f"3. Voiceover script (150-200 words per scene)\n\n"
        f"Format each scene as:\n"
        f"SCENE X:\n"
        f"VISUAL: [scene description]\n"
        f"TEXT: [on-screen text]\n"
        f"VOICEOVER: [voiceover script]\n\n"
        f"Ensure the entire video script can be delivered in approximately 3 minutes."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert video scriptwriter who creates engaging educational content."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            n=1,
            stop=None,
            temperature=0.7,
        )
        
        script_text = response.choices[0].message.content.strip()
        
        # Parse the script into scenes
        scenes = []
        current_scene = {}
        
        for line in script_text.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('SCENE'):
                if current_scene and 'visual' in current_scene and 'text' in current_scene and 'voiceover' in current_scene:
                    scenes.append(current_scene)
                current_scene = {'scene_number': line.split(':')[0].strip()}
            elif line.startswith('VISUAL:'):
                current_scene['visual'] = line[7:].strip()
            elif line.startswith('TEXT:'):
                current_scene['text'] = line[5:].strip()
            elif line.startswith('VOICEOVER:'):
                current_scene['voiceover'] = line[10:].strip()
        
        # Add the last scene
        if current_scene and 'visual' in current_scene and 'text' in current_scene and 'voiceover' in current_scene:
            scenes.append(current_scene)
            
        return {"scenes": scenes}
    except Exception as e:
        logger.error(f"Error generating video script from OpenAI: {e}")
        return {"error": f"Error generating video script: {e}"}

def generate_voiceover_text(scene_text: str, language: str = "English") -> str:
    """Generates or optimizes voiceover text based on scene text.
    
    Args:
        scene_text: The text content for the scene
        language: The language for the voiceover
        
    Returns:
        Optimized text for text-to-speech voiceover
    """
    if not client:
        logger.error("OpenAI client not initialized. Cannot generate voiceover text.")
        return scene_text  # Return original text as fallback

    prompt = (
        f"Optimize the following text for a natural-sounding voiceover in {language}:\n\n"
        f"'{scene_text}'\n\n"
        f"Make it conversational, easy to speak, and maintain the same information. "
        f"Add appropriate pauses (with commas and periods) and emphasis where needed. "
        f"Avoid complex words that might be difficult to pronounce."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert in creating natural-sounding voiceover scripts."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            n=1,
            stop=None,
            temperature=0.5,  # Lower temperature for more consistent output
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error optimizing voiceover text from OpenAI: {e}")
        return scene_text  # Return original text as fallback

def generate_knowledge_check(module_description: str, course_context: dict) -> dict:
    """Generates a knowledge check quiz for a module.
    
    Args:
        module_description: The description of the module
        course_context: Dictionary containing course details
        
    Returns:
        A dictionary containing quiz questions and answers
    """
    if not client:
        logger.error("OpenAI client not initialized. Cannot generate knowledge check.")
        return {"error": "OpenAI client not initialized. Check API key configuration."}
        
    prompt = (
        f"Create a knowledge check quiz for a module with the following description:\n\n"
        f"'{module_description}'\n\n"
        f"Generate 5 multiple-choice questions that test understanding of key concepts from this module. "
        f"For each question, provide:\n"
        f"1. The question text\n"
        f"2. Four possible answers (A, B, C, D)\n"
        f"3. The correct answer letter\n"
        f"4. A brief explanation of why the answer is correct\n\n"
        f"Format as JSON with the structure: "
        f"{{\"questions\": [{{\"question\": \"...\", \"options\": [\"A. ...\", \"B. ...\", \"C. ...\", \"D. ...\"], "
        f"\"correct_answer\": \"A\", \"explanation\": \"...\"}}]}}"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert in educational assessment who creates effective knowledge check questions."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            n=1,
            stop=None,
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating knowledge check from OpenAI: {e}")
        return {"error": f"Error generating knowledge check: {e}"}
