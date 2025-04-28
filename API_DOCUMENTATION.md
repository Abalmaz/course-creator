# AI Course Creator API Documentation

## Overview

The AI Course Creator API is a Django REST API application that enables users to create video courses powered by AI. The system uses OpenAI for content generation, Pexels/Pixabay for background videos, and HeyGen for avatar creation.

## Authentication

Currently, the API uses Django's built-in authentication system. For production use, you should implement token-based authentication or JWT.

## Base URL

All API endpoints are prefixed with `/api/`.

## Endpoints

### Courses

#### Create a Course (Step 1)

```
POST /api/courses/
```

Creates a new course and generates objectives using AI.

**Request Body:**

```json
{
  "name": "Introduction to Machine Learning",
  "language": "en",
  "target_audience": "Beginners",
  "content_style": "Educational",
  "documents": [optional file upload]
}
```

**Response:**

```json
{
  "id": "uuid",
  "name": "Introduction to Machine Learning",
  "language": "en",
  "target_audience": "Beginners",
  "content_style": "Educational",
  "created_at": "2025-04-28T15:00:00Z",
  "objectives": [
    {
      "id": "uuid",
      "text": "Understand the basics of machine learning algorithms",
      "order": 0,
      "selected": false
    },
    ...
  ]
}
```

#### List Courses

```
GET /api/courses/
```

Returns a list of all courses.

#### Get Course Details

```
GET /api/courses/{course_id}/
```

Returns details of a specific course.

#### Select Objectives (Step 1.5)

```
PATCH /api/courses/{course_id}/select-objectives/
```

Selects which objectives to include in the course.

**Request Body:**

```json
[
  {
    "id": "uuid",
    "selected": true
  },
  ...
]
```

#### Generate Modules (Step 2)

```
POST /api/courses/{course_id}/generate-modules/
```

Generates modules and video content based on selected objectives.

**Response:**

```json
{
  "id": "uuid",
  "name": "Introduction to Machine Learning",
  "modules": [
    {
      "id": "uuid",
      "title": "Module 1: Machine Learning Basics",
      "description": "...",
      "scenes": [
        {
          "id": "uuid",
          "scene_number": 1,
          "visual_description": "...",
          "on_screen_text": "...",
          "voiceover_text": "..."
        },
        ...
      ]
    },
    ...
  ]
}
```

### Modules

#### Generate Knowledge Check

```
POST /api/modules/{module_id}/generate-knowledge-check/
```

Generates a knowledge check quiz for a specific module.

### Avatars

#### List Avatars

```
GET /api/avatars/list/
```

Lists all available avatars, both local and from HeyGen API.

#### Create Avatar

```
POST /api/avatars/create/
```

Creates a new custom avatar using HeyGen API.

**Request Body:**

Form data with:
- `avatar_image`: Image file
- `name`: Avatar name

#### Check Avatar Training Status

```
GET /api/avatars/training/{avatar_id}/
```

Checks the training status of an avatar.

#### Set Course Avatar

```
PATCH /api/courses/{course_id}/avatar/
```

Sets the avatar for a specific course.

**Request Body:**

```json
{
  "avatar": "avatar_id"
}
```

### Video Rendering

#### Render Scene

```
POST /api/scenes/{scene_id}/render/
```

Triggers asynchronous rendering of a scene video.

**Response:**

```json
{
  "task_id": "celery_task_id",
  "status": "rendering",
  "scene_id": "uuid"
}
```

#### Render Module

```
POST /api/modules/{module_id}/render/
```

Triggers asynchronous rendering of a complete module video by concatenating scene videos.

**Response:**

```json
{
  "task_id": "celery_task_id",
  "status": "rendering",
  "module_id": "uuid",
  "scene_count": 5
}
```

#### Check Render Status

```
GET /api/render/status/{task_id}/
```

Checks the status of a rendering task.

**Response:**

```json
{
  "task_id": "celery_task_id",
  "status": "SUCCESS",
  "result": {
    "success": true,
    "output_path": "/path/to/video.mp4"
  }
}
```

## Workflow

1. Create a course (POST `/api/courses/`)
2. Select objectives (PATCH `/api/courses/{course_id}/select-objectives/`)
3. Generate modules (POST `/api/courses/{course_id}/generate-modules/`)
4. (Optional) Create and set avatar (POST `/api/avatars/create/`, PATCH `/api/courses/{course_id}/avatar/`)
5. (Optional) Generate knowledge checks (POST `/api/modules/{module_id}/generate-knowledge-check/`)
6. Render scene videos (POST `/api/scenes/{scene_id}/render/`)
7. Render module videos (POST `/api/modules/{module_id}/render/`)

## Error Handling

The API returns standard HTTP status codes:

- 200: Success
- 201: Created
- 400: Bad Request
- 404: Not Found
- 500: Internal Server Error

Error responses include a descriptive message:

```json
{
  "error": "Detailed error message"
}
```

## Dependencies

- Django & Django REST Framework
- OpenAI API
- Pexels/Pixabay API
- HeyGen API
- MoviePy
- Celery & Redis
- Gunicorn & Whitenoise

## Deployment

Use the provided `deploy.sh` script to deploy the application. Make sure to set up the environment variables in the `.env` file first.
