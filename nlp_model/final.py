import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, DebertaV2Tokenizer
import networkx as nx
import spacy
import pickle
import google.generativeai as genai
import json
import os
import dotenv
import plotly.graph_objects as go

# Load environment variables
dotenv.load_dotenv()

def load_models():
    """Load all required ML models"""
    nlp = spacy.load("en_core_web_sm")
    
    # Use absolute path for the model
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(current_dir, "checkpoint-753")
    
    # Check if directory exists
    if not os.path.exists(model_path):
        # Try parent directory
        parent_dir = os.path.dirname(current_dir)
        model_path = os.path.join(parent_dir, "checkpoint-753")
    
    tokenizer = DebertaV2Tokenizer.from_pretrained('microsoft/deberta-v3-small')
    model = AutoModelForSequenceClassification.from_pretrained(model_path)
    model.eval()
    return nlp, tokenizer, model


def load_knowledge_graph():
    """Load and initialize knowledge graph"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    graph_path = os.path.join(current_dir, "knowledge_graph_final.pkl")
    
    try:
        with open(graph_path, 'rb') as f:
            graph_data = pickle.load(f)
        knowledge_graph = nx.DiGraph()
        knowledge_graph.add_nodes_from(graph_data['nodes'].items())
        for u, edges in graph_data['edges'].items():
            for v, data in edges.items():
                knowledge_graph.add_edge(u, v, **data)
        return knowledge_graph
    except Exception as e:
        print(f"Error loading knowledge graph: {str(e)}")
        # Return an empty graph as fallback
        return nx.DiGraph()



class KnowledgeGraphBuilder:
    def __init__(self):
        self.knowledge_graph = nx.DiGraph()
        
    def update_knowledge_graph(self, text, is_real, nlp):
        entities = extract_entities(text, nlp)
        for entity, entity_type in entities:
            if not self.knowledge_graph.has_node(entity):
                self.knowledge_graph.add_node(
                    entity,
                    type=entity_type,
                    real_count=1 if is_real else 0,
                    fake_count=0 if is_real else 1
                )
            else:
                if is_real:
                    self.knowledge_graph.nodes[entity]['real_count'] += 1
                else:
                    self.knowledge_graph.nodes[entity]['fake_count'] += 1

        for i, (entity1, _) in enumerate(entities):
            for entity2, _ in entities[i+1:]:
                if not self.knowledge_graph.has_edge(entity1, entity2):
                    self.knowledge_graph.add_edge(
                        entity1,
                        entity2,
                        weight=1,
                        is_real=is_real
                    )
                else:
                    self.knowledge_graph[entity1][entity2]['weight'] += 1


def setup_gemini():
    """Initialize Gemini model"""
    genai.configure(api_key=os.getenv("GEMINI_API"))
    model = genai.GenerativeModel('models/gemini-1.5-flash')
    return model

def predict_with_model(text, tokenizer, model):
    """Make predictions using the ML model"""
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
    probabilities = torch.nn.functional.softmax(outputs.logits, dim=-1)
    predicted_label = torch.argmax(probabilities, dim=-1).item()
    confidence = probabilities[0][predicted_label].item() * 100
    return "FAKE" if predicted_label == 1 else "REAL", confidence

def extract_entities(text, nlp):
    """Extract named entities from text"""
    doc = nlp(text)
    entities = [(ent.text, ent.label_) for ent in doc.ents]
    return entities

# def update_knowledge_graph(text, is_real, knowledge_graph, nlp, save=True, push_to_hf=True):
#     """Update knowledge graph with new information"""
#     entities = extract_entities(text, nlp)
#     for entity, entity_type in entities:
#         if not knowledge_graph.has_node(entity):
#             knowledge_graph.add_node(
#                 entity,
#                 type=entity_type,
#                 real_count=1 if is_real else 0,
#                 fake_count=0 if is_real else 1
#             )
#         else:
#             if is_real:
#                 knowledge_graph.nodes[entity]['real_count'] += 1
#             else:
#                 knowledge_graph.nodes[entity]['fake_count'] += 1

#     for i, (entity1, _) in enumerate(entities):
#         for entity2, _ in entities[i+1:]:
#             if not knowledge_graph.has_edge(entity1, entity2):
#                 knowledge_graph.add_edge(
#                     entity1,
#                     entity2,
#                     weight=1,
#                     is_real=is_real
#                 )
#             else:
#                 knowledge_graph[entity1][entity2]['weight'] += 1
#     if save:
#         from save_model import save_knowledge_graph, push_to_huggingface
#         filepath = save_knowledge_graph(knowledge_graph)
        
#         # Push to Hugging Face if requested
#         if push_to_hf:
#             repo_id = os.getenv("HF_REPO_ID", "HeheBoi0769/Nexus_NLP_model")
#             push_to_huggingface(filepath, repo_id)
    
#     return knowledge_graph

def update_knowledge_graph(text, is_real, knowledge_graph, nlp, save=True, push_to_hf=False):
    """Update knowledge graph with new information"""
    entities = extract_entities(text, nlp)
    for entity, entity_type in entities:
        if not knowledge_graph.has_node(entity):
            knowledge_graph.add_node(
                entity,
                type=entity_type,
                real_count=1 if is_real else 0,
                fake_count=0 if is_real else 1
            )
        else:
            if is_real:
                knowledge_graph.nodes[entity]['real_count'] += 1
            else:
                knowledge_graph.nodes[entity]['fake_count'] += 1

    for i, (entity1, _) in enumerate(entities):
        for entity2, _ in entities[i+1:]:
            if not knowledge_graph.has_edge(entity1, entity2):
                knowledge_graph.add_edge(
                    entity1,
                    entity2,
                    weight=1,
                    is_real=is_real
                )
            else:
                knowledge_graph[entity1][entity2]['weight'] += 1
    
    if save:
        from save_model import save_knowledge_graph
        filepath = save_knowledge_graph(knowledge_graph)
        
        # Push to Hugging Face only if explicitly requested
        if push_to_hf:
            from save_model import push_to_huggingface
            repo_id = os.getenv("HF_REPO_ID", "HeheBoi0769/Nexus_NLP_model")
            push_to_huggingface(filepath, repo_id)
    
    return knowledge_graph


def predict_with_knowledge_graph(text, knowledge_graph, nlp):
    """Make predictions using the knowledge graph"""
    entities = extract_entities(text, nlp)
    real_score = 0
    fake_score = 0

    for entity, _ in entities:
        if knowledge_graph.has_node(entity):
            real_count = knowledge_graph.nodes[entity].get('real_count', 0)
            fake_count = knowledge_graph.nodes[entity].get('fake_count', 0)
            total = real_count + fake_count
            if total > 0:
                real_score += real_count / total
                fake_score += fake_count / total

    total_score = real_score + fake_score
    if total_score == 0:
        return "UNCERTAIN", 50.0
    
    if real_score > fake_score:
        confidence = (real_score / total_score) * 100
        return "REAL", confidence
    else:
        confidence = (fake_score / total_score) * 100
        return "FAKE", confidence

def analyze_content_gemini(model, text):
    """Analyze content using Gemini model"""
    prompt = f"""Analyze this news text and return a JSON object with the following exact structure:
    {{
        "gemini_analysis": {{
            "predicted_classification": "Real or Fake",
            "confidence_score": "0-100",
            "reasoning": ["point1", "point2"]
        }},
        "text_classification": {{
            "category": "",
            "writing_style": "Formal/Informal/Clickbait",
            "target_audience": "",
            "content_type": "news/opinion/editorial"
        }},
        "sentiment_analysis": {{
            "primary_emotion": "",
            "emotional_intensity": "1-10",
            "sensationalism_level": "High/Medium/Low",
            "bias_indicators": ["bias1", "bias2"],
            "tone": {{"formality": "formal/informal", "style": "Professional/Emotional/Neutral"}},
            "emotional_triggers": ["trigger1", "trigger2"]
        }},
        "entity_recognition": {{
            "source_credibility": "High/Medium/Low",
            "people": ["person1", "person2"],
            "organizations": ["org1", "org2"],
            "locations": ["location1", "location2"],
            "dates": ["date1", "date2"],
            "statistics": ["stat1", "stat2"]
        }},
        "context": {{
            "main_narrative": "",
            "supporting_elements": ["element1", "element2"],
            "key_claims": ["claim1", "claim2"],
            "narrative_structure": ""
        }},
        "fact_checking": {{
            "verifiable_claims": ["claim1", "claim2"],
            "evidence_present": "Yes/No",
            "fact_check_score": "0-100"
        }}
    }}

    Analyze this text and return only the JSON response: {text}"""
    
    response = model.generate_content(prompt)
    try:
        cleaned_text = response.text.strip()
        if cleaned_text.startswith('```json'):
            cleaned_text = cleaned_text[7:-3]
        return json.loads(cleaned_text)
    except json.JSONDecodeError:
        return {
            "gemini_analysis": {
                "predicted_classification": "UNCERTAIN",
                "confidence_score": "50",
                "reasoning": ["Analysis failed to generate valid JSON"]
            }
        }
    