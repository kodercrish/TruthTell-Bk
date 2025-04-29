import pickle
import os
from huggingface_hub import HfApi, login
import networkx as nx

def save_knowledge_graph(knowledge_graph, filepath=None):
    """Save the knowledge graph to a local file"""
    if filepath is None:
        # Use absolute path for default location
        current_dir = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(current_dir, "knowledge_graph_final.pkl")
    
    # Convert the graph to a serializable format
    graph_data = {
        'nodes': {node: data for node, data in knowledge_graph.nodes(data=True)},
        'edges': {u: {v: data for v, data in knowledge_graph[u].items()} 
                 for u in knowledge_graph.nodes()}
    }
    
    # Save to file
    with open(filepath, 'wb') as f:
        pickle.dump(graph_data, f)
    
    print(f"Knowledge graph saved to {filepath}")
    return filepath


def push_to_huggingface(filepath, repo_id, token=None):
    """Push the saved knowledge graph to Hugging Face Hub"""
    if token is None:
        token = os.getenv("HF_TOKEN")
        if not token:
            raise ValueError("No Hugging Face token provided. Set HF_TOKEN environment variable or pass token parameter.")
    
    # Login to Hugging Face
    login(token=token)
    
    # Initialize the Hugging Face API
    api = HfApi()
    
    # Upload the file
    api.upload_file(
        path_or_fileobj=filepath,
        path_in_repo="knowledge_graph_final.pkl",
        repo_id=repo_id,
        repo_type="space"
    )
    
    print(f"Knowledge graph pushed to Hugging Face Hub: {repo_id}")
