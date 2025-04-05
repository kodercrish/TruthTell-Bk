from fastapi import APIRouter, UploadFile, File
import google.generativeai as genai
import time
import os

video_router = APIRouter()

@video_router.post("/analyze-video")
async def analyze_video_endpoint(file: UploadFile = File(...)):
    temp_file_path = f"temp_{file.filename}"
    with open(temp_file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    video = genai.upload_file(temp_file_path, mime_type="video/mp4")
    
    while video.state != 2:
        time.sleep(0.36)
        video = genai.get_file(video.name)
    
    model = genai.GenerativeModel('gemini-2.0-flash')
    prompt = "Analyze the speech in this video and detect if it contains misinformation or bias. First state if the content is real or fake. Then give a short summary regarding the speech. Then Summarize key points."
    response = model.generate_content([prompt, video])
    
    os.remove(temp_file_path)  # Clean up temp file
    
    return {"analysis": response.text}

