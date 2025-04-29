from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sys
import os
from typing import Dict, Any
import io
import base64
from PIL import Image
import plotly.io as pio
import matplotlib.pyplot as plt
import networkx as nx

# Add the nlp_model directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import NLP model functions
from nlp_model.final import (
    load_models,
    load_knowledge_graph,
    predict_with_model,
    predict_with_knowledge_graph,
    extract_entities,
    update_knowledge_graph,
    setup_gemini,
    analyze_content_gemini,
    KnowledgeGraphBuilder
)
import time
import random
import networkx as nx
import plotly.graph_objects as go

# Create router
nlp_router = APIRouter()

# Initialize models
nlp = None
tokenizer = None
model = None
knowledge_graph = None

# Input model
class NewsInput(BaseModel):
    text: str

# Response models
class PredictionResponse(BaseModel):
    ml_prediction: str
    ml_confidence: float
    kg_prediction: str
    kg_confidence: float
    gemini_prediction: str
    gemini_confidence: str
    detailed_analysis: Dict[str, Any]

# Initialize models on first request
@nlp_router.on_event("startup")
async def initialize_models():
    global nlp, tokenizer, model, knowledge_graph
    
    try:
        # Load models
        nlp, tokenizer, model = load_models()
        knowledge_graph = load_knowledge_graph()
        print("All NLP models loaded successfully")
    except Exception as e:
        print(f"Error loading NLP models: {str(e)}")
        # We'll initialize on first request if this fails

def generate_knowledge_graph_viz(text):
    global nlp, tokenizer, model
    
    # Initialize models if not already done
    if nlp is None or tokenizer is None or model is None:
        try:
            nlp, tokenizer, model = load_models()
        except Exception as e:
            print(f"Error loading models: {str(e)}")
            return {"error": f"Failed to load models: {str(e)}"}
    
    try:
        kg_builder = KnowledgeGraphBuilder()
        
        # Get prediction
        prediction, _ = predict_with_model(text, tokenizer, model)
        is_fake = prediction == "FAKE"
        
        # Update knowledge graph
        kg_builder.update_knowledge_graph(text, not is_fake, nlp)

        # Create a simple directed graph visualization
        G = kg_builder.knowledge_graph
        
        # If graph is empty, create a simple placeholder graph
        if len(G.nodes()) == 0:
            G.add_node("No entities found", type="PLACEHOLDER")
        
        # Create a matplotlib figure
        plt.figure(figsize=(10, 8))
        
        # Use spring layout for node positioning
        pos = nx.spring_layout(G)
        
        # Draw nodes with different colors based on entity type
        node_colors = []
        for node in G.nodes():
            node_type = G.nodes[node].get('type', 'UNKNOWN')
            if node_type == 'PERSON':
                node_colors.append('lightblue')
            elif node_type == 'ORG':
                node_colors.append('lightgreen')
            elif node_type == 'GPE':
                node_colors.append('orange')
            elif node_type == 'DATE':
                node_colors.append('yellow')
            else:
                node_colors.append('gray')
        
        # Draw the graph
        nx.draw(G, pos, with_labels=True, node_color=node_colors, 
                node_size=1500, font_size=10, font_weight='bold', 
                edge_color='gray', width=1, alpha=0.7)
        
        # Add a title
        plt.title(f"Knowledge Graph - {'FAKE' if is_fake else 'REAL'} News Analysis", 
                  fontsize=16, fontweight='bold')
        
        # Save the figure to a bytes buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        plt.close()
        
        # Encode the image as base64
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        
        # Return just the base64 encoded image
        return {"image": img_str}
        
    except Exception as e:
        error_msg = f"Error generating knowledge graph visualization: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        # Return an error message
        return {"error": error_msg}


@nlp_router.post("/analyze", response_model=PredictionResponse)
async def analyze_news(news_input: NewsInput):
    global nlp, tokenizer, model, knowledge_graph
    
    if not news_input.text:
        raise HTTPException(status_code=400, detail="News text cannot be empty")
    
    # Initialize models if not already done
    if nlp is None or tokenizer is None or model is None or knowledge_graph is None:
        try:
            nlp, tokenizer, model = load_models()
            knowledge_graph = load_knowledge_graph()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error loading models: {str(e)}")
    
    # Get predictions from all models
    ml_prediction, ml_confidence = predict_with_model(news_input.text, tokenizer, model)
    kg_prediction, kg_confidence = predict_with_knowledge_graph(news_input.text, knowledge_graph, nlp)
    
    # Update knowledge graph
    update_knowledge_graph(news_input.text, ml_prediction == "REAL", knowledge_graph, nlp, save=True, push_to_hf=False)
    
    # Get Gemini analysis with retries
    max_retries = 10
    retry_count = 0
    gemini_result = None

    while retry_count < max_retries:
        try:
            gemini_model = setup_gemini()
            gemini_result = analyze_content_gemini(gemini_model, news_input.text)
            
            # Check if we got valid results
            if gemini_result and gemini_result.get('gemini_analysis'):
                break
                
        except Exception as e:
            print(f"Gemini error: {str(e)}")
            
        retry_count += 1
        time.sleep(1)  # Add a 1-second delay between retries
        
    # Use default values if all retries failed
    if not gemini_result:
        gemini_result = {
            "gemini_analysis": {
                "predicted_classification": "UNCERTAIN",
                "confidence_score": "50",
                "reasoning": ["Analysis temporarily unavailable"]
            }
        }
    
    # Extract entities
    entities = extract_entities(news_input.text, nlp)
    entities_list = [{"entity": entity, "type": entity_type} for entity, entity_type in entities]
    
    # Generate knowledge graph visualization with error handling
    try:
        kg_viz = generate_knowledge_graph_viz(news_input.text)
    except Exception as e:
        print(f"Error generating knowledge graph: {str(e)}")
        kg_viz = {}  # Use empty dict if visualization fails
    
    # Prepare detailed analysis
    detailed_analysis = {
        "entities": entities_list,
        "knowledge_graph": kg_viz,
        "gemini_analysis": gemini_result
    }
    
    return {
        "ml_prediction": ml_prediction,
        "ml_confidence": ml_confidence,
        "kg_prediction": kg_prediction,
        "kg_confidence": kg_confidence,
        "gemini_prediction": gemini_result["gemini_analysis"]["predicted_classification"],
        "gemini_confidence": gemini_result["gemini_analysis"]["confidence_score"],
        "detailed_analysis": detailed_analysis
    }

@nlp_router.get("/health")
async def health_check():
    global nlp, tokenizer, model, knowledge_graph
    return {
        "status": "healthy", 
        "models_loaded": nlp is not None and model is not None and tokenizer is not None and knowledge_graph is not None
    }
