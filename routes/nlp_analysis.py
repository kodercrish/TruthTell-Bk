from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sys
import os
from typing import Dict, Any
import io
import base64
from PIL import Image
import plotly.io as pio

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
            return {}
    
    try:
        kg_builder = KnowledgeGraphBuilder()
        
        # Get prediction
        prediction, _ = predict_with_model(text, tokenizer, model)
        is_fake = prediction == "FAKE"
        
        # Update knowledge graph
        kg_builder.update_knowledge_graph(text, not is_fake, nlp)

        # Get all edges from the knowledge graph
        all_edges = list(kg_builder.knowledge_graph.edges())
        total_edges = len(all_edges)
        
        # Select only 60% of edges to display (0.3 + 0.15 + 0.15)
        display_edge_count = int(total_edges * 0.6)
        display_edges = random.sample(all_edges, k=min(display_edge_count, total_edges))
        
        # Determine edge counts for each color
        primary_color_count = int(total_edges * 0.3)  # 30% primary color (green for real, red for fake)
        opposite_color_count = int(total_edges * 0.15)  # 15% opposite color
        orange_color_count = int(total_edges * 0.15)  # 15% orange
        
        # Ensure we don't exceed the number of display edges
        total_colored = primary_color_count + opposite_color_count + orange_color_count
        if total_colored > len(display_edges):
            ratio = len(display_edges) / total_colored
            primary_color_count = int(primary_color_count * ratio)
            opposite_color_count = int(opposite_color_count * ratio)
            orange_color_count = int(orange_color_count * ratio)
        
        # Shuffle display edges to ensure random distribution
        random.shuffle(display_edges)
        
        # Assign colors to edges
        primary_color_edges = set(display_edges[:primary_color_count])
        opposite_color_edges = set(display_edges[primary_color_count:primary_color_count+opposite_color_count])
        orange_color_edges = set(display_edges[primary_color_count+opposite_color_count:
                                              primary_color_count+opposite_color_count+orange_color_count])
        
        # Create a new graph with selected edges
        selected_graph = nx.DiGraph()
        selected_graph.add_nodes_from(kg_builder.knowledge_graph.nodes(data=True))
        selected_graph.add_edges_from(display_edges)
        
        pos = nx.spring_layout(selected_graph)
        
        # Create three edge traces - primary, opposite, and orange
        primary_edge_trace = go.Scatter(
            x=[], y=[],
            line=dict(
                width=2, 
                color='rgba(255,0,0,0.7)' if is_fake else 'rgba(0,255,0,0.7)'  # Red if fake, green if real
            ),
            hoverinfo='none',
            mode='lines'
        )
        
        opposite_edge_trace = go.Scatter(
            x=[], y=[],
            line=dict(
                width=2, 
                color='rgba(0,255,0,0.7)' if is_fake else 'rgba(255,0,0,0.7)'  # Green if fake, red if real
            ),
            hoverinfo='none',
            mode='lines'
        )
        
        orange_edge_trace = go.Scatter(
            x=[], y=[],
            line=dict(
                width=2, 
                color='rgba(255,165,0,0.7)'  # Orange
            ),
            hoverinfo='none',
            mode='lines'
        )
        
        node_trace = go.Scatter(
            x=[], y=[],
            mode='markers+text',
            hoverinfo='text',
            textposition='top center',
            marker=dict(
                size=15,
                color='white',
                line=dict(width=2, color='black')
            ),
            text=[]
        )
        
        # Add edges with appropriate colors
        for edge in display_edges:
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            
            if edge in primary_color_edges:
                primary_edge_trace['x'] += (x0, x1, None)
                primary_edge_trace['y'] += (y0, y1, None)
            elif edge in opposite_color_edges:
                opposite_edge_trace['x'] += (x0, x1, None)
                opposite_edge_trace['y'] += (y0, y1, None)
            elif edge in orange_color_edges:
                orange_edge_trace['x'] += (x0, x1, None)
                orange_edge_trace['y'] += (y0, y1, None)
        
        # Add nodes
        for node in selected_graph.nodes():
            x, y = pos[node]
            node_trace['x'] += (x,)
            node_trace['y'] += (y,)
            node_trace['text'] += (node,)
        
        fig = go.Figure(
            data=[primary_edge_trace, opposite_edge_trace, orange_edge_trace, node_trace],
            layout=go.Layout(
                showlegend=False,
                hovermode='closest',
                margin=dict(b=0,l=0,r=0,t=0),
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
        )
        
        # Return the figure as a dictionary without trying to convert to image
        return fig.to_dict()
        
    except Exception as e:
        print(f"Error generating knowledge graph visualization: {str(e)}")
        # Return an empty dict if there's an error
        return {}


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
