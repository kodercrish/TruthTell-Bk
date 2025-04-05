from fastapi import APIRouter, UploadFile, File
import google.generativeai as genai
import PIL.Image
import io
import os

image_router = APIRouter()

@image_router.post("/analyze-image")
async def analyze_image_endpoint(file: UploadFile = File(...)):
    # Read image content
    content = await file.read()
    image = PIL.Image.open(io.BytesIO(content))
    
    # Configure Gemini
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    # Prepare prompt
    prompt = "Analyze the content in this image and detect if it contains misinformation or bias. First state if the content is real or fake. Then give a short summary regarding the content. Then Summarize key points."

    response = model.generate_content([prompt, image])
    
    return {"analysis": response.text}
