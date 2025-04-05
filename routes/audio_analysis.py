# # from fastapi import APIRouter, UploadFile, File, HTTPException
# # from fastapi.responses import JSONResponse
# # import os
# # import tempfile
# # import whisper
# # from typing import Dict, Any
# # import time
# # from factcheck_instance import fact_checker_instance
# # audio_router = APIRouter()

# # # Initialize the whisper model
# # model = whisper.load_model("base")  # You can use "tiny", "base", "small", "medium", or "large"

# # # Initialize the fact checker with API keys from environment variables
# # fact_checker = fact_checker_instance

# # @audio_router.post("/analyze-audio")
# # async def analyze_audio_endpoint(file: UploadFile = File(...)):
# #     """
# #     Endpoint to transcribe audio and perform fact checking on the content.
    
# #     Parameters:
# #     - file: Audio file upload (supported formats: mp3, wav, ogg, flac, m4a)
    
# #     Returns:
# #     - JSON with transcription and fact check results
# #     """
# #     # Check file extension
# #     allowed_extensions = {'mp3', 'wav', 'ogg', 'flac', 'm4a'}
# #     file_extension = file.filename.split('.')[-1].lower()
    
# #     if file_extension not in allowed_extensions:
# #         raise HTTPException(
# #             status_code=400, 
# #             detail=f"Unsupported file format. Supported formats: {', '.join(allowed_extensions)}"
# #         )
    
# #     # Create a temporary file
# #     with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as temp_file:
# #         temp_file_path = temp_file.name
# #         content = await file.read()
# #         temp_file.write(content)
    
# #     try:
# #         # Transcribe the audio
# #         transcription = transcribe_audio(temp_file_path)
        
# #         if "error" in transcription:
# #             raise HTTPException(status_code=500, detail=f"Transcription error: {transcription['error']}")
        
# #         # Check facts in the transcribed text
# #         fact_check_result = check_facts(transcription['text'])
        
# #         # Return results
# #         return {
# #             "transcription": transcription,
# #             "fact_check": fact_check_result
# #         }
    
# #     except Exception as e:
# #         raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    
# #     finally:
# #         # Clean up the temporary file
# #         if os.path.exists(temp_file_path):
# #             os.remove(temp_file_path)

# # def transcribe_audio(file_path: str) -> Dict[str, Any]:
# #     """Transcribe the audio file using Whisper."""
# #     try:
# #         # Load audio and pad/trim it
# #         audio = whisper.load_audio(file_path)
# #         audio = whisper.pad_or_trim(audio)
        
# #         # Make log-Mel spectrogram and move to the same device as the model
# #         mel = whisper.log_mel_spectrogram(audio).to(model.device)
        
# #         # Detect the spoken language
# #         _, probs = model.detect_language(mel)
# #         detected_language = max(probs, key=probs.get)
        
# #         # Decode the audio
# #         options = whisper.DecodingOptions()
# #         result = whisper.decode(model, mel, options)
        
# #         return {
# #             'text': result.text,
# #             'language': detected_language,
# #             'segments': [{'start': segment.start, 'end': segment.end, 'text': segment.text} 
# #                          for segment in result.segments]
# #         }
# #     except Exception as e:
# #         return {'error': str(e)}

# # def check_facts(text: str) -> Dict[str, Any]:
# #     """Pass the transcribed text to the fact checker."""
# #     try:
# #         # Use the fact checker to generate a report
# #         report = fact_checker.generate_report(text)
# #         return report
# #     except Exception as e:
# #         return {'error': str(e)}

# import time
# from fastapi import APIRouter, UploadFile, File
# import google.generativeai as genai
# import os

# audio_router = APIRouter()

# @audio_router.post("/analyze-audio")
# async def analyze_audio_endpoint(file: UploadFile = File(...)):
#     temp_file_path = f"temp_{file.filename}"
#     with open(temp_file_path, "wb") as buffer:
#         content = await file.read()
#         buffer.write(content)
    
#     genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
#     audio = genai.upload_file(temp_file_path, mime_type="audio/mp3")
    
#     while audio.state != 2:
#         time.sleep(0.36)
#         audio = genai.get_file(audio.name)
    
#     model = genai.GenerativeModel('gemini-2.0-flash')
    
#     # Prepare prompt
#     prompt = "Analyze the speech in this audio file and detect if it contains misinformation or bias. First state if the content is real or fake. Then give a short summary regarding the speech. Then Summarize key points."
    
#     response = model.generate_content([prompt, audio])
    
#     os.remove(temp_file_path)  # Clean up temp file
    
#     return {"analysis": response.text}
import time
from fastapi import APIRouter, UploadFile, File, HTTPException
import google.generativeai as genai
import os

audio_router = APIRouter()

@audio_router.post("/analyze-audio")
async def analyze_audio_endpoint(file: UploadFile = File(...)):
    # Check file extension
    allowed_extensions = {'mp3', 'wav', 'ogg', 'flac', 'm4a'}
    file_extension = file.filename.split('.')[-1].lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file format. Supported formats: {', '.join(allowed_extensions)}"
        )
    
    # Map file extensions to MIME types
    mime_types = {
        'mp3': 'audio/mpeg',
        'wav': 'audio/wav',
        'ogg': 'audio/ogg',
        'flac': 'audio/flac',
        'm4a': 'audio/mp4'
    }
    
    mime_type = mime_types.get(file_extension, 'audio/mpeg')
    
    temp_file_path = f"temp_{int(time.time())}_{file.filename}"
    try:
        with open(temp_file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")
            
        genai.configure(api_key=api_key)
        
        # Upload with correct MIME type
        audio = genai.upload_file(temp_file_path, mime_type=mime_type)
        
        # Wait for processing with timeout
        max_attempts = 30
        attempts = 0
        while audio.state != 2 and attempts < max_attempts:
            time.sleep(0.36)
            audio = genai.get_file(audio.name)
            attempts += 1
        
        if audio.state != 2:
            raise HTTPException(status_code=500, detail="Audio processing timed out")
        
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # More specific and structured prompt
        prompt = """
        You are an expert fact-checker analyzing an audio recording. Please:
        
        1. TRUTHFULNESS ASSESSMENT: Determine if the content contains misinformation. Clearly state if it's "REAL" or "FAKE" information.
        
        2. SUMMARY: Provide a concise summary of what the speaker is discussing.
        
        3. KEY POINTS: List the 3-5 main claims or arguments made in the recording.
        
        4. EVIDENCE: If you detect any factual claims, note whether they appear accurate or questionable based on your knowledge.
        
        Format your response with clear section headings.
        """
        
        response = model.generate_content([prompt, audio])
        
        return {"analysis": response.text}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing audio: {str(e)}")
        
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
