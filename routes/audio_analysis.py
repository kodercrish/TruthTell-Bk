# from fastapi import APIRouter, UploadFile, File, HTTPException
# from fastapi.responses import JSONResponse
# import os
# import tempfile
# import whisper
# from typing import Dict, Any
# import time
# from fact_checker import FactChecker

# audio_router = APIRouter()

# # Initialize the whisper model
# model = whisper.load_model("base")  # You can use "tiny", "base", "small", "medium", or "large"

# # Initialize the fact checker with API keys from environment variables
# fact_checker = FactChecker(
#     groq_api_key=os.getenv("GROQ_API_KEY"),
#     serper_api_key=os.getenv("SERPER_API_KEY")
# )

# @audio_router.post("/analyze-audio")
# async def analyze_audio_endpoint(file: UploadFile = File(...)):
#     """
#     Endpoint to transcribe audio and perform fact checking on the content.
    
#     Parameters:
#     - file: Audio file upload (supported formats: mp3, wav, ogg, flac, m4a)
    
#     Returns:
#     - JSON with transcription and fact check results
#     """
#     # Check file extension
#     allowed_extensions = {'mp3', 'wav', 'ogg', 'flac', 'm4a'}
#     file_extension = file.filename.split('.')[-1].lower()
    
#     if file_extension not in allowed_extensions:
#         raise HTTPException(
#             status_code=400, 
#             detail=f"Unsupported file format. Supported formats: {', '.join(allowed_extensions)}"
#         )
    
#     # Create a temporary file
#     with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as temp_file:
#         temp_file_path = temp_file.name
#         content = await file.read()
#         temp_file.write(content)
    
#     try:
#         # Transcribe the audio
#         transcription = transcribe_audio(temp_file_path)
        
#         if "error" in transcription:
#             raise HTTPException(status_code=500, detail=f"Transcription error: {transcription['error']}")
        
#         # Check facts in the transcribed text
#         fact_check_result = check_facts(transcription['text'])
        
#         # Return results
#         return {
#             "transcription": transcription,
#             "fact_check": fact_check_result
#         }
    
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    
#     finally:
#         # Clean up the temporary file
#         if os.path.exists(temp_file_path):
#             os.remove(temp_file_path)

# def transcribe_audio(file_path: str) -> Dict[str, Any]:
#     """Transcribe the audio file using Whisper."""
#     try:
#         # Load audio and pad/trim it
#         audio = whisper.load_audio(file_path)
#         audio = whisper.pad_or_trim(audio)
        
#         # Make log-Mel spectrogram and move to the same device as the model
#         mel = whisper.log_mel_spectrogram(audio).to(model.device)
        
#         # Detect the spoken language
#         _, probs = model.detect_language(mel)
#         detected_language = max(probs, key=probs.get)
        
#         # Decode the audio
#         options = whisper.DecodingOptions()
#         result = whisper.decode(model, mel, options)
        
#         return {
#             'text': result.text,
#             'language': detected_language,
#             'segments': [{'start': segment.start, 'end': segment.end, 'text': segment.text} 
#                          for segment in result.segments]
#         }
#     except Exception as e:
#         return {'error': str(e)}

# def check_facts(text: str) -> Dict[str, Any]:
#     """Pass the transcribed text to the fact checker."""
#     try:
#         # Use the fact checker to generate a report
#         report = fact_checker.generate_report(text)
#         return report
#     except Exception as e:
#         return {'error': str(e)}

import time
from fastapi import APIRouter, UploadFile, File
import google.generativeai as genai
import os

audio_router = APIRouter()

@audio_router.post("/analyze-audio")
async def analyze_audio_endpoint(file: UploadFile = File(...)):
    temp_file_path = f"temp_{file.filename}"
    with open(temp_file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    audio = genai.upload_file(temp_file_path, mime_type="audio/mp3")
    
    while audio.state != 2:
        time.sleep(0.36)
        audio = genai.get_file(audio.name)
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Prepare prompt
    prompt = "Analyze the speech in this audio file and detect if it contains misinformation or bias. First state if the content is real or fake. Then give a short summary regarding the speech. Then Summarize key points."
    
    response = model.generate_content([prompt, audio])
    
    os.remove(temp_file_path)  # Clean up temp file
    
    return {"analysis": response.text}