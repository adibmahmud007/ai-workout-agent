from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from dotenv import load_dotenv
import os
import json
import re
from fastapi.responses import Response
import asyncio
# Add this at the top with other imports
import tempfile
import uuid
  
# Force enable edge_tts and handle installation
try:
    import edge_tts
    from io import BytesIO
    EDGE_TTS_AVAILABLE = True
except ImportError:
    # Attempt to install edge_tts if not available
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "edge-tts"])
    import edge_tts
    from io import BytesIO
    EDGE_TTS_AVAILABLE = True

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Initialize FastAPI app
app = FastAPI()

# Define input schema
class UserProfile(BaseModel):
    mission: str
    time_commitment: str
    gear: str
    squad: str

# Enhanced voice mapping with more expressive voices
VOICE_MAPPING = {
    "Lone Wolf": "en-US-JennyNeural",
    "Guardian": "en-US-JennyNeural",
    "Warrior": "en-US-JennyNeural",  # More authoritative voice
    "Rebuilder": "en-US-JennyNeural"  # More encouraging tone
}


def format_workout_text(workout_plan: list, motivational_text: str, time_commitment: str, mission: str) -> str:
    """Enhanced formatting for natural speech delivery"""
    formatted_steps = []
    for i, step in enumerate(workout_plan):
        # Clean and enhance each step
        clean_step = re.sub(r'^Step \d+:\s*', '', step)
        
        # Add natural transitions with pacing
        if i == 0:
            formatted_steps.append(f"First, we'll {clean_step.lower()}")
        elif i == len(workout_plan) - 1:
            formatted_steps.append(f"To finish, {clean_step.lower()}")
        else:
            formatted_steps.append(f"Then, {clean_step.lower()}")
    
    return "\n\n".join([
        f"Your {time_commitment} {mission.replace('-', ' ')} workout:",
        "",
        *formatted_steps,
        "",
        "Motivation for today:",
        motivational_text
    ])

async def generate_audio_coaching(text: str, voice: str) -> bytes:
    """Enhanced audio generation with multiple fallback methods"""
    temp_file = None
    try:
        # Method 1: Try with streaming approach first
        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate="+8%",
            volume="+5%"
        )
        
        # Use BytesIO for streaming
        audio_stream = BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_stream.write(chunk["data"])
        
        # Check if we got audio data
        audio_stream.seek(0)
        audio_bytes = audio_stream.getvalue()
        
        if len(audio_bytes) > 0:
            return audio_bytes
            
        # Method 2: Fallback to file-based approach
        import tempfile
        import uuid
        
        temp_file = f"temp_audio_{uuid.uuid4().hex}.mp3"
        
        # Try alternative voice if the original fails
        voices_to_try = [voice, "en-US-JennyNeural", "en-US-AriaNeural"]
        
        for attempt_voice in voices_to_try:
            try:
                communicate = edge_tts.Communicate(
                    text=text,
                    voice=attempt_voice,
                    rate="+5%",
                    volume="+0%"
                )
                
                await communicate.save(temp_file)
                
                # Verify file exists and has content
                if os.path.exists(temp_file) and os.path.getsize(temp_file) > 0:
                    with open(temp_file, "rb") as f:
                        audio_bytes = f.read()
                    
                    if len(audio_bytes) > 0:
                        return audio_bytes
                        
            except Exception as voice_error:
                print(f"Voice {attempt_voice} failed: {voice_error}")
                continue
        
        # If all methods fail
        raise Exception("All audio generation methods failed")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audio generation failed: {str(e)}")
    
    finally:
        # Clean up temp file if it exists
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass

@app.post("/generate-plan")
async def generate_plan(profile: UserProfile):
    """Enhanced workout plan generator with JSON response and download link"""
    # Enhanced prompt for better audio-ready output
    prompt = f"""
You are a professional virtual trainer creating a {profile.time_commitment} workout for audio delivery.

User Profile:
- Goal: {profile.mission}
- Time: {profile.time_commitment}
- Equipment: {profile.gear}
- Personality: {profile.squad}

Generate:
1. A 3-5 step workout plan with:
   - Clear, concise instructions
   - Natural language for speech delivery
   - Proper exercise sequencing
2. A {profile.squad}-specific motivational message

Format exactly as:
{{
  "workout_plan": [
    "Step 1: [instruction with rep/set details]",
    "Step 2: [instruction with rep/set details]",
    ...
  ],
  "motivational_text": "[personalized encouragement]"
}}
"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "system", "content": "You are an expert fitness coach specializing in audio workout programs."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 600
    }

    try:
        # Get workout plan from LLM
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        reply = response.json()["choices"][0]["message"]["content"]

        # Parse response
        match = re.search(r"\{[\s\S]*\}", reply)
        if not match:
            raise HTTPException(status_code=500, detail="Invalid workout plan format")
        
        parsed_output = json.loads(match.group(0))
        
        # Format for audio
        formatted_text = format_workout_text(
            parsed_output["workout_plan"],
            parsed_output["motivational_text"],
            profile.time_commitment,
            profile.mission
        )
        
        # Generate audio automatically
        voice = VOICE_MAPPING.get(profile.squad, "en-US-JennyNeural")
        audio_bytes = await generate_audio_coaching(formatted_text, voice)
        
        # Save audio to temporary file for download
        audio_filename = f"workout_{profile.mission}_{profile.time_commitment}_{uuid.uuid4().hex[:8]}.mp3"
        temp_audio_path = f"temp_downloads/{audio_filename}"
        
        # Create temp directory if it doesn't exist
        os.makedirs("temp_downloads", exist_ok=True)
        
        # Save audio file
        with open(temp_audio_path, "wb") as f:
            f.write(audio_bytes)
        
        # Return JSON response with workout plan and download info
        return {
            "status": "success",
            "workout_plan": parsed_output["workout_plan"],
            "motivational_text": parsed_output["motivational_text"],
            # "user_profile": {
            #     "mission": profile.mission,
            #     "time_commitment": profile.time_commitment,
            #     "gear": profile.gear,
            #     "squad": profile.squad,
            #     "voice_used": voice
            # },
            "audio_info": {
                "filename": audio_filename,
                "size_bytes": len(audio_bytes),
                "download_url": f"/download-audio/{audio_filename}",
                "play_url": f"/play-audio/{audio_filename}"
            },
            "formatted_text": formatted_text
        }

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"API request failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Keep the separate generate-audio endpoint as backup/alternative
class AudioRequest(BaseModel):
    workout_plan: list[str]
    motivational_text: str
    time_commitment: str
    mission: str
    squad: str

# @app.post("/generate-audio")
# async def generate_audio_from_plan(request: AudioRequest):
#     """Robust audio generation endpoint (backup method)"""
#     try:
#         # Convert to dict for easier handling
#         plan = request.dict()
        
#         # Format the workout text
#         formatted_text = format_workout_text(
#             plan["workout_plan"],
#             plan["motivational_text"],
#             plan["time_commitment"],
#             plan["mission"]
#         )
        
#         # Get the appropriate voice
#         voice = VOICE_MAPPING.get(plan["squad"], "en-US-JennyNeural")
        
#         # Generate to temporary file
#         temp_file = "temp_audio.mp3"
#         try:
#             communicate = edge_tts.Communicate(
#                 text=formatted_text,
#                 voice=voice,
#                 rate="+8%",
#                 volume="+5%"
#             )
            
#             await communicate.save(temp_file)
            
#             # Verify the file was created
#             if not os.path.exists(temp_file):
#                 raise HTTPException(status_code=500, detail="Audio file was not created")
                
#             # Read the file content
#             with open(temp_file, "rb") as f:
#                 audio_bytes = f.read()
                
#             if len(audio_bytes) == 0:
#                 raise HTTPException(status_code=500, detail="Generated empty audio file")
                
#             return Response(
#                 content=audio_bytes,
#                 media_type="audio/mpeg",
#                 headers={
#                     "Content-Disposition": "attachment; filename=workout.mp3",
#                     "Content-Length": str(len(audio_bytes))
#                 }
#             )
            
#         finally:
#             # Clean up the temp file
#             if os.path.exists(temp_file):
#                 os.remove(temp_file)
                
#     except HTTPException:
#         raise
#     except json.JSONDecodeError:
#         raise HTTPException(status_code=422, detail="Invalid JSON format")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Audio generation failed: {str(e)}")

@app.get("/download-audio/{filename}")
async def download_audio(filename: str):
    """Download audio file"""
    file_path = f"temp_downloads/{filename}"
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    with open(file_path, "rb") as f:
        audio_bytes = f.read()
    
    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Length": str(len(audio_bytes))
        }
    )

@app.get("/play-audio/{filename}")
async def play_audio(filename: str):
    """Play audio file in browser (for Swagger audio player)"""
    file_path = f"temp_downloads/{filename}"
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    with open(file_path, "rb") as f:
        audio_bytes = f.read()
    
    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={
            "Content-Length": str(len(audio_bytes)),
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-cache"
        }
    )

@app.get("/cleanup-temp-files")
async def cleanup_temp_files():
    """Clean up temporary audio files (optional maintenance endpoint)"""
    temp_dir = "temp_downloads"
    if not os.path.exists(temp_dir):
        return {"status": "No temp directory found"}
    
    files_deleted = 0
    for filename in os.listdir(temp_dir):
        file_path = os.path.join(temp_dir, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
            files_deleted += 1
    
    return {"status": f"Deleted {files_deleted} temporary files"}
async def test_audio_generation():
    """Test endpoint to debug audio generation"""
    try:
        # Simple test text
        test_text = "Hello! This is a test audio message."
        
        # Test with different voices
        for voice_name, voice in VOICE_MAPPING.items():
            try:
                audio_bytes = await generate_audio_coaching(test_text, voice)
                return {
                    "status": "SUCCESS",
                    "voice_tested": voice_name,
                    "voice_code": voice,
                    "audio_size": len(audio_bytes)
                }
            except Exception as e:
                print(f"Voice {voice_name} failed: {e}")
                continue
        
        return {"status": "FAILED", "message": "All voices failed"}
    
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}
@app.get("/play-demo")
async def play_demo():
    """Demo endpoint to test audio generation with playable response"""
    demo_plan = {
        "workout_plan": [
            "Step 1: Do 3 sets of 10 push-ups",
            "Step 2: Perform 3 sets of 15 squats", 
            "Step 3: Finish with a 1-minute plank"
        ],
        "motivational_text": "Great job! You're getting stronger every day!",
        "time_commitment": "15 minute",
        "mission": "Build-Strength",
        "squad": "Warrior"
    }
    
    formatted_text = format_workout_text(
        demo_plan["workout_plan"],
        demo_plan["motivational_text"],
        demo_plan["time_commitment"],
        demo_plan["mission"]
    )
    
    audio_bytes = await generate_audio_coaching(formatted_text, VOICE_MAPPING["Warrior"])
    
    # Return playable audio response
    return Response(
        content=audio_bytes, 
        media_type="audio/mpeg",
        headers={
            "Content-Length": str(len(audio_bytes)),
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-cache"
        }
    )

@app.get("/health")
async def health_check():
    """Enhanced health check"""
    return {
        "status": "READY",
        "services": {
            "edge_tts": "OPERATIONAL" if EDGE_TTS_AVAILABLE else "UNAVAILABLE",
            "groq_api": "CONFIGURED" if GROQ_API_KEY else "MISSING_API_KEY"
        },
        "voices": VOICE_MAPPING
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000, reload=True)