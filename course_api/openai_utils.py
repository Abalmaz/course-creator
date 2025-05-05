import os
from openai import OpenAI
from django.conf import settings
import logging
import json # Added json

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = None
if settings.OPENAI_API_KEY:
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
else:
    logger.warning("OPENAI_API_KEY not found in environment variables. OpenAI integration will not work.")

def generate_course_objectives(course_name: str, language: str, target_audience: str, content_style: str, documents=None) -> list[str]:
    """Generates learning objectives for a course using OpenAI."""
    if not client:
        logger.error("OpenAI client not initialized. Cannot generate objectives.")
        return ["Error: OpenAI client not initialized. Check API key configuration."]

    document_context = ""
    if documents:
        document_context = f"The following documents were provided as reference material: {documents}\n"
        
    prompt = (
        f"Generate 5 distinct learning objectives for an online video course titled 	'{course_name}	'. "
        f"The course is intended for 	'{target_audience}	' and should be presented in a 	'{content_style}	' style. "
        f"The course language is {language}. "
        f"{document_context}"
        f"Each objective should clearly state what the learner will be able to do after completing the relevant module(s). "
        f"Format the output as a numbered list, with each objective on a new line."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
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
        objectives = [obj.strip() for obj in content.split(	'\n	') if obj.strip() and obj.strip()[0].isdigit()]
        objectives = [obj.split(	'.	', 1)[-1].split(	')	', 1)[-1].strip() for obj in objectives]
        return objectives[:5]
    except Exception as e:
        logger.error(f"Error generating course objectives from OpenAI: {e}")
        return [f"Error generating objectives: {e}"]

def generate_module_description(objective: str, course_context: dict) -> str:
    """Generates a module description based on an objective."""
    if not client:
        logger.error("OpenAI client not initialized. Cannot generate module description.")
        return "Error: OpenAI client not initialized. Check API key configuration."

    course_name = course_context.get(	'name	', 	'the course	')
    language = course_context.get(	'language	', 	'English	')
    target_audience = course_context.get(	'target_audience	', 	'learners	')
    content_style = course_context.get(	'content_style	', 	'educational	')
    
    prompt = (
        f"Create a detailed module description for a course titled 	'{course_name}	' in {language}. "
        f"This module addresses the following learning objective: 	'{objective}	'. "
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
    """Generates a video script for a 3-minute video based on module description."""
    if not client:
        logger.error("OpenAI client not initialized. Cannot generate video script.")
        return {"error": "OpenAI client not initialized. Check API key configuration."}

    course_name = course_context.get(	'name	', 	'the course	')
    language = course_context.get(	'language	', 	'English	')
    target_audience = course_context.get(	'target_audience	', 	'learners	')
    content_style = course_context.get(	'content_style	', 	'educational	')
    
    prompt = (
        f"Create a script for a 3-minute educational video based on the following module description:\n\n"
        f"	'{module_description}	'\n\n"
        f"The video is part of the course 	'{course_name}	' in {language}, targeting {target_audience} "
        f"with a {content_style} style. "
        f"Structure the script as 5-7 distinct scenes. For each scene, provide:\n"
        f"1. Scene description (visual setting, background elements, mood)\n"
        f"2. On-screen text (concise key points that appear on screen)\n"
        f"3. Voiceover script (approx 15-30 seconds per scene)\n\n"
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
            max_tokens=1500, # Increased max_tokens for potentially longer scripts
            n=1,
            stop=None,
            temperature=0.7,
        )
        
        script_text = response.choices[0].message.content.strip()
        
        scenes = []
        current_scene = {}
        scene_buffer = []

        for line in script_text.split(	'\n	'):
            stripped_line = line.strip()
            if stripped_line.startswith(	'SCENE	'):
                if current_scene:
                    current_scene[	'voiceover	'] = "\n".join(scene_buffer).strip()
                    if 	'visual	' in current_scene and 	'text	' in current_scene and 	'voiceover	' in current_scene:
                         scenes.append(current_scene)
                    scene_buffer = []
                current_scene = {	'scene_number	': stripped_line.split(	':	')[0].strip()}
            elif stripped_line.startswith(	'VISUAL:	'):
                current_scene[	'visual	'] = stripped_line[7:].strip()
            elif stripped_line.startswith(	'TEXT:	'):
                current_scene[	'text	'] = stripped_line[5:].strip()
            elif stripped_line.startswith(	'VOICEOVER:	'):
                 # Start collecting voiceover lines
                 scene_buffer.append(stripped_line[10:].strip())
            elif current_scene and 	'voiceover	' not in current_scene and scene_buffer: # Continue collecting voiceover if VOICEOVER: was the previous line
                 scene_buffer.append(stripped_line)
            elif current_scene and 	'voiceover	' in current_scene: # Append to existing voiceover if already started
                 scene_buffer.append(stripped_line)

        # Add the last scene
        if current_scene:
            current_scene[	'voiceover	'] = "\n".join(scene_buffer).strip()
            if 	'visual	' in current_scene and 	'text	' in current_scene and 	'voiceover	' in current_scene:
                scenes.append(current_scene)
            
        return {"scenes": scenes}
    except Exception as e:
        logger.error(f"Error generating video script from OpenAI: {e}")
        return {"error": f"Error generating video script: {e}"}

def generate_voiceover_text(scene_text: str, language: str = "English") -> str:
    """Generates or optimizes voiceover text based on scene text."""
    # This function might be less necessary if the script generation prompt is good
    # Keeping it simple for now, just returning the text
    logger.info("generate_voiceover_text called, returning original text for now.")
    return scene_text
    # Previous implementation kept below for reference if needed later
    """
    if not client:
        logger.error("OpenAI client not initialized. Cannot generate voiceover text.")
        return scene_text  # Return original text as fallback

    prompt = (
        f"Optimize the following text for a natural-sounding voiceover in {language}:\n\n"
        f"	'{scene_text}	'\n\n"
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
            temperature=0.5,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error optimizing voiceover text from OpenAI: {e}")
        return scene_text
    """

def generate_knowledge_check(module_description: str, course_context: dict) -> str:
    """Generates a knowledge check quiz for a module. Returns JSON string."""
    if not client:
        logger.error("OpenAI client not initialized. Cannot generate knowledge check.")
        return json.dumps({"error": "OpenAI client not initialized. Check API key configuration."})
        
    prompt = (
        f"Create a knowledge check quiz for a module with the following description:\n\n"
        f"	'{module_description}	'\n\n"
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
                {"role": "system", "content": "You are an expert in educational assessment who creates effective knowledge check questions in JSON format."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000, # Increased tokens
            n=1,
            stop=None,
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        return response.choices[0].message.content # Returns JSON string directly
    except Exception as e:
        logger.error(f"Error generating knowledge check from OpenAI: {e}")
        return json.dumps({"error": f"Error generating knowledge check: {e}"})

def generate_search_query_for_visuals(scene_text: str, visual_description: str) -> str:
    """Generates a concise search query for stock video platforms based on scene content.
    
    Args:
        scene_text: The voiceover or on-screen text for the scene.
        visual_description: The desired visual setting/mood described in the script.
        
    Returns:
        A concise search query string (e.g., "data visualization abstract blue") or an error string.
    """
    if not client:
        logger.error("OpenAI client not initialized. Cannot generate search query.")
        return "Error: OpenAI client not initialized."

    prompt = (
        f"Based on the following scene content, generate a concise and effective search query (3-5 keywords) suitable for finding relevant background videos on stock platforms like Pexels or Pixabay.\n\n"
        f"Visual Description: 	'{visual_description}	'\n"
        f"Scene Text/Voiceover: 	'{scene_text}	'\n\n"
        f"Focus on the core visual elements and concepts. Avoid generic terms unless essential. Prioritize keywords from the visual description if available and relevant.\n"
        f"Output ONLY the search query keywords, separated by spaces."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o", # Or a faster/cheaper model if sufficient
            messages=[
                {"role": "system", "content": "You are an expert at generating concise search queries for stock video footage based on scene descriptions and text."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=20,
            n=1,
            stop=None,
            temperature=0.5,
        )
        query = response.choices[0].message.content.strip().replace(	'\"', 	'') # Remove quotes if any
        # Basic validation
        if not query or len(query.split()) > 7: # Limit length
             logger.warning(f"Generated query might be invalid: 	'{query}	'. Falling back to basic keywords.")
             # Fallback: Extract keywords from visual description or scene text directly (simple approach)
             fallback_query = visual_description.split()[:3] if visual_description else scene_text.split()[:3]
             return " ".join(fallback_query)
        return query
    except Exception as e:
        logger.error(f"Error generating search query from OpenAI: {e}")
        return f"Error generating search query: {e}"

