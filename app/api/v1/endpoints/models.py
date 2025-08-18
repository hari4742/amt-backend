"""
Models listing endpoint for available transcription models.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def list_models():
    """
    List available transcription models.

    Returns:
        Dictionary with list of models
    """
    models = [
        {"id": "maestro", "name": "Maestro", "description": "High quality piano AMT model"},
        {"id": "basic", "name": "Basic", "description": "Fast baseline transcription"},
        {"id": "advanced", "name": "Advanced",
            "description": "Balanced performance and speed"},
    ]

    return {"models": models}
