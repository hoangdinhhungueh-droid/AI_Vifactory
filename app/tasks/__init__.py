"""
VF Pipeline - Celery Tasks Package
Pattern 2: Task Queue Abstraction

This package contains Celery task wrappers for B2-B9 pipeline stages.
Each task wrapper provides:
- Automatic retry with exponential backoff
- Timeout enforcement
- Structured logging
- Output verification
- Observability via Flower dashboard

Task naming convention: vf.{stage}.{operation}
Example: vf.b2.story_generation
"""

from .story_tasks import run_b2_story_generation
from .director_tasks import run_b3_director_plan
from .prompt_tasks import run_b3_5_prompt_forge
from .audio_tasks import run_b6_audio_generation
from .subtitle_tasks import run_b7_subtitle_generation
from .render_tasks import run_b8_video_render
from .quality_tasks import run_b9_quality_probe

__version__ = '1.0.0'
__all__ = [
    'run_b2_story_generation',
    'run_b3_director_plan',
    'run_b3_5_prompt_forge',
    'run_b6_audio_generation',
    'run_b7_subtitle_generation',
    'run_b8_video_render',
    'run_b9_quality_probe',
]

# Task metadata for documentation
TASK_REGISTRY = {
    'vf.b2.story_generation': {
        'stage': 'B2',
        'description': 'Story generation from Notion episode data',
        'timeout': '30 min',
        'retries': 3,
        'input': 'Episode ID',
        'output': 'story.json',
    },
    'vf.b3.director_plan': {
        'stage': 'B3',
        'description': 'Director and DP planning from story',
        'timeout': '45 min',
        'retries': 3,
        'input': 'story.json',
        'output': 'director_plan.json + dp_plan.json',
    },
    'vf.b3_5.prompt_forge': {
        'stage': 'B3.5',
        'description': 'Image generation prompts from director plan',
        'timeout': '60 min',
        'retries': 3,
        'input': 'director_plan.json + dp_plan.json',
        'output': 'prompts_forge.json',
    },
    'vf.b6.audio_generation': {
        'stage': 'B6',
        'description': 'TTS and background music generation',
        'timeout': '90 min',
        'retries': 3,
        'input': 'script.json',
        'output': 'audio/*.wav files',
    },
    'vf.b7.subtitle_generation': {
        'stage': 'B7',
        'description': 'Subtitle/caption generation from audio',
        'timeout': '30 min',
        'retries': 3,
        'input': 'audio files + timing data',
        'output': '*.srt, *.vtt files',
    },
    'vf.b8.video_render': {
        'stage': 'B8',
        'description': 'Final video rendering via Remotion',
        'timeout': '120 min',
        'retries': 2,
        'input': 'All assets (images, audio, subtitles)',
        'output': 'final_video.mp4',
    },
    'vf.b9.quality_probe': {
        'stage': 'B9',
        'description': 'Video quality verification',
        'timeout': '20 min',
        'retries': 3,
        'input': 'final_video.mp4',
        'output': 'quality_report.json',
    },
}
