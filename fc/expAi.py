import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types import content
import os
from typing import Dict
import json


generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_schema": content.Schema(
        type=content.Type.OBJECT,
        required=["explanation_summary", "claim_explanations", "evidence_analysis", "trust_factors"],
        properties={
            "explanation_summary": content.Schema(
                type=content.Type.STRING,
            ),
            "claim_explanations": content.Schema(
                type=content.Type.ARRAY,
                items=content.Schema(
                    type=content.Type.OBJECT,
                    required=["claim", "reasoning", "key_factors", "confidence_explanation"],
                    properties={
                        "claim": content.Schema(type=content.Type.STRING),
                        "reasoning": content.Schema(type=content.Type.STRING),
                        "key_factors": content.Schema(
                            type=content.Type.ARRAY,
                            items=content.Schema(type=content.Type.STRING)
                        ),
                        "confidence_explanation": content.Schema(type=content.Type.STRING)
                    }
                )
            ),
            "evidence_analysis": content.Schema(
                type=content.Type.OBJECT,
                required=["strength_explanation", "gap_analysis", "contradiction_details"],
                properties={
                    "strength_explanation": content.Schema(type=content.Type.STRING),
                    "gap_analysis": content.Schema(type=content.Type.STRING),
                    "contradiction_details": content.Schema(type=content.Type.STRING)
                }
            ),
            "trust_factors": content.Schema(
                type=content.Type.ARRAY,
                items=content.Schema(
                    type=content.Type.OBJECT,
                    required=["factor", "impact", "recommendation"],
                    properties={
                        "factor": content.Schema(type=content.Type.STRING),
                        "impact": content.Schema(type=content.Type.STRING),
                        "recommendation": content.Schema(type=content.Type.STRING)
                    }
                )
            )
        }
    ),
    "response_mime_type": "application/json"
}

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config=generation_config
)

def explain_factcheck_result(factcheck_report: Dict) -> Dict:
    # Extract relevant components from the fact-check report
    detailed_analysis = factcheck_report["detailed_analysis"]
    
    prompt = f"""
    Explain why these fact-checking conclusions were reached based on the following analysis:
    
    Overall Analysis:
    - Truth Score: {detailed_analysis["overall_analysis"]["truth_score"]}
    - Key Findings: {detailed_analysis["overall_analysis"]["key_findings"]}
    
    Claim Analysis:
    {json.dumps(detailed_analysis["claim_analysis"], indent=2)}
    
    Provide a detailed explanation focusing on:
    1. Why each claim was marked as misinformation/true
    2. What evidence led to these conclusions
    3. How the confidence scores were determined
    4. What factors influenced the trust assessment
    """

    response = model.generate_content(prompt)
    explanation = json.loads(response.text)
    
    return {
        "original_report": factcheck_report,
        "explanation": explanation
    }

def generate_visual_explanation(explanation: Dict) -> Dict:
    """
    Generate visualization data for the explanation
    Returns data structure suitable for frontend visualization
    """
    visualization_data = {
        "confidence_breakdown": [],
        "decision_path": []
    }
    
    # Extract visualization data from explanation
    for claim_exp in explanation["claim_explanations"]:
        visualization_data["confidence_breakdown"].append({
            "claim": claim_exp["claim"],
            "factors": claim_exp["key_factors"]
        })
        
        visualization_data["decision_path"].append({
            "claim": claim_exp["claim"],
            "reasoning_steps": claim_exp["reasoning"].split(". ")
        })

    return visualization_data
