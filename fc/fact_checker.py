from groq import Groq
import os
import dotenv
import google.generativeai as genai
from typing import List, Dict
import json
from dataclasses import dataclass
from datetime import datetime
import requests
from urllib.parse import quote
from .serper_search import SerperEvidenceRetriever
from google.ai.generativelanguage_v1beta.types import content
import time

dotenv.load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

@dataclass
class Claim:
    statement: str
    confidence_score: int
    verified_status: str
    key_evidence: List[str]
    sources: List[str]
    worthiness_score: int

class FactChecker:
    def __init__(self, groq_api_key: str, serper_api_key: str):
        generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_schema": content.Schema(
            type = content.Type.OBJECT,
            enum = [],
            required = ["overall_analysis", "claim_analysis", "meta_analysis"],
            properties = {
            "overall_analysis": content.Schema(
                type = content.Type.OBJECT,
                enum = [],
                required = ["truth_score", "reliability_assessment", "key_findings", "patterns_identified"],
                properties = {
                "truth_score": content.Schema(
                    type = content.Type.NUMBER,
                ),
                "reliability_assessment": content.Schema(
                    type = content.Type.STRING,
                ),
                "key_findings": content.Schema(
                    type = content.Type.ARRAY,
                    items = content.Schema(
                    type = content.Type.STRING,
                    ),
                ),
                "patterns_identified": content.Schema(
                    type = content.Type.ARRAY,
                    items = content.Schema(
                    type = content.Type.STRING,
                    ),
                ),
                },
            ),
            "claim_analysis": content.Schema(
                type = content.Type.ARRAY,
                items = content.Schema(
                type = content.Type.OBJECT,
                required = ["claim", "verification_status", "confidence_level", "evidence_quality", "source_assessment", "misinformation_impact", "correction_suggestions"],
                properties = {
                    "claim": content.Schema(
                    type = content.Type.STRING,
                    ),
                    "verification_status": content.Schema(
                    type = content.Type.STRING,
                    ),
                    "confidence_level": content.Schema(
                    type = content.Type.NUMBER,
                    ),
                    "evidence_quality": content.Schema(
                    type = content.Type.OBJECT,
                    required = ["strength", "gaps", "contradictions"],
                    properties = {
                        "strength": content.Schema(
                        type = content.Type.NUMBER,
                        ),
                        "gaps": content.Schema(
                        type = content.Type.ARRAY,
                        items = content.Schema(
                            type = content.Type.STRING,
                        ),
                        ),
                        "contradictions": content.Schema(
                        type = content.Type.ARRAY,
                        items = content.Schema(
                            type = content.Type.STRING,
                        ),
                        ),
                    },
                    ),
                    "source_assessment": content.Schema(
                    type = content.Type.ARRAY,
                    items = content.Schema(
                        type = content.Type.OBJECT,
                        required = ["url", "credibility_metrics", "relevance_to_claim"],
                        properties = {
                        "url": content.Schema(
                            type = content.Type.STRING,
                        ),
                        "credibility_metrics": content.Schema(
                            type = content.Type.OBJECT,
                            required = ["credibility_score", "bias_rating", "fact_checking_history"],
                            properties = {
                            "credibility_score": content.Schema(
                                type = content.Type.NUMBER,
                            ),
                            "bias_rating": content.Schema(
                                type = content.Type.STRING,
                            ),
                            "fact_checking_history": content.Schema(
                                type = content.Type.NUMBER,
                            ),
                            },
                        ),
                        "relevance_to_claim": content.Schema(
                            type = content.Type.NUMBER,
                        ),
                        },
                    ),
                    ),
                    "misinformation_impact": content.Schema(
                    type = content.Type.OBJECT,
                    required = ["severity", "affected_domains", "potential_consequences", "spread_risk"],
                    properties = {
                        "severity": content.Schema(
                        type = content.Type.NUMBER,
                        ),
                        "affected_domains": content.Schema(
                        type = content.Type.ARRAY,
                        items = content.Schema(
                            type = content.Type.STRING,
                        ),
                        ),
                        "potential_consequences": content.Schema(
                        type = content.Type.ARRAY,
                        items = content.Schema(
                            type = content.Type.STRING,
                        ),
                        ),
                        "spread_risk": content.Schema(
                        type = content.Type.NUMBER,
                        ),
                    },
                    ),
                    "correction_suggestions": content.Schema(
                    type = content.Type.OBJECT,
                    required = ["verified_facts", "recommended_sources", "context_missing"],
                    properties = {
                        "verified_facts": content.Schema(
                        type = content.Type.ARRAY,
                        items = content.Schema(
                            type = content.Type.STRING,
                        ),
                        ),
                        "recommended_sources": content.Schema(
                        type = content.Type.ARRAY,
                        items = content.Schema(
                            type = content.Type.OBJECT,
                            properties = {
                            "url": content.Schema(
                                type = content.Type.STRING,
                            ),
                            "credibility_score": content.Schema(
                                type = content.Type.NUMBER,
                            ),
                            "relevance": content.Schema(
                                type = content.Type.NUMBER,
                            ),
                            },
                        ),
                        ),
                        "context_missing": content.Schema(
                        type = content.Type.ARRAY,
                        items = content.Schema(
                            type = content.Type.STRING,
                        ),
                        ),
                    },
                    ),
                },
                ),
            ),
            "meta_analysis": content.Schema(
                type = content.Type.OBJECT,
                required = ["information_ecosystem_impact", "recommended_actions", "prevention_strategies"],
                properties = {
                "information_ecosystem_impact": content.Schema(
                    type = content.Type.STRING,
                ),
                "recommended_actions": content.Schema(
                    type = content.Type.ARRAY,
                    items = content.Schema(
                    type = content.Type.STRING,
                    ),
                ),
                "prevention_strategies": content.Schema(
                    type = content.Type.ARRAY,
                    items = content.Schema(
                    type = content.Type.STRING,
                    ),
                ),
                },
            ),
            },
        ),
        "response_mime_type": "application/json",
        }

        generation_config_sources = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_schema": content.Schema(
            type = content.Type.OBJECT,
            enum = [],
            required = ["credibility_score", "fact_checking_history", "transparency_score", "expertise_level", "brief_explanation"],
            properties = {
            "credibility_score": content.Schema(
                type = content.Type.INTEGER,
            ),
            "fact_checking_history": content.Schema(
                type = content.Type.INTEGER,
            ),
            "transparency_score": content.Schema(
                type = content.Type.INTEGER,
            ),
            "expertise_level": content.Schema(
                type = content.Type.INTEGER,
            ),
            "brief_explanation": content.Schema(
                type = content.Type.STRING,
            ),
            "additional_metrics": content.Schema(
                type = content.Type.OBJECT,
                properties = {
                "citation_score": content.Schema(
                    type = content.Type.INTEGER,
                ),
                "peer_recognition": content.Schema(
                    type = content.Type.INTEGER,
                ),
                },
            ),
            },
        ),
        "response_mime_type": "application/json",
        }


        self.client = Groq(api_key=groq_api_key)
        self.search_client = SerperEvidenceRetriever(api_key=serper_api_key)
        
        self.gemini_client = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=generation_config,
        )
        self.gemini_chat = self.gemini_client.start_chat(
            history=[]
        )

        self.source_correction = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=generation_config_sources,
        )
        self.gemini_chat_sources = self.source_correction.start_chat(
            history=[]
        )
        
    def extract_claims(self, news_text: str) -> List[str]:
        prompt = {
            "role": "user",
            "content": f"Break the following news into atomic claims. Make a maximum of 3 claims, not more at all. Return as JSON array of claim statements:\n\n{news_text}"
        }
        
        response = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[prompt],
            temperature=0.2,
            response_format={"type": "json_object"}
        )

        gemini_extract_prompt = f"Break the following news into atomic claims. Make a maximum of 3 claims, not more at all. Return as JSON array of claim statements:\n\n{news_text}"

        generation_config_extract = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_schema": content.Schema(
            type = content.Type.OBJECT,
            enum = [],
            required = ["claims"],
            properties = {
            "claims": content.Schema(
                type = content.Type.ARRAY,
                items = content.Schema(
                type = content.Type.STRING,
                ),
            ),
            },
        ),
        "response_mime_type": "application/json",
        }

        model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=generation_config_extract,
        )

        chat_session = model.start_chat(
        history=[
        ]
        )

        response = chat_session.send_message(gemini_extract_prompt)

        return json.loads(response.text)

    def generate_verification_questions(self, claim: str) -> List[str]:
        prompt = {
            "role": "user",
            "content": f"Generate specific questions to verify this claim. Make a maximum of 5 questions for the claim. Return as JSON array:\n\n{claim}"
        }
        
        response = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[prompt],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        gemini_questions_prompt = f"Generate specific questions to verify this claim. Make a maximum of 5 questions for the claim. Return as JSON array:\n\n{claim}"

        generation_config_questions = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_schema": content.Schema(
            type = content.Type.OBJECT,
            enum = [],
            required = ["questions"],
            properties = {
            "questions": content.Schema(
                type = content.Type.ARRAY,
                items = content.Schema(
                type = content.Type.STRING,
                ),
            ),
            },
        ),
        "response_mime_type": "application/json",
        }

        model_questions = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=generation_config_questions,
        )

        chat_session_questions = model_questions.start_chat(
        history=[
        ]
        )

        response = chat_session_questions.send_message(gemini_questions_prompt)


        return json.loads(response.text)

    def search_evidence(self, query: str) -> List[Dict]:
        return self.search_client.retrieve_evidence(query)

    def analyze_claim(self, claim: str) -> Claim:
        # Generate verification questions
        questions = self.generate_verification_questions(claim=claim)["questions"]

        claim_queries_dict = {claim: [q for q in questions]}

        evidence_dict = self.search_client.retrieve_evidence(claim_queries_dict=claim_queries_dict)
        
        # Collect evidence for each question
        evidences = []
        sources = []
        
        for claim, evidence in evidence_dict.items():
            for evidence_item in evidence:
                evidences.append(evidence_item['text'])
                sources.append(evidence_item['url'])
        
        # # Analyze evidence using Groq
        # analysis_prompt = {
        #     "role": "user",
        #     "content": f"Analyze this claim and evidence. Return JSON with confidence_score (1-100), verified_status (True/False/Partially True/Unverifiable), and worthiness_score (1-10):\n\nClaim: {claim}\n\nEvidence: {json.dumps(evidence)}"
        # }
        
        # analysis = self.client.chat.completions.create(
        #     model="llama-3.3-70b-versatile",
        #     messages=[analysis_prompt],
        #     temperature=0.2,
        #     response_format={"type": "json_object"}
        # )

        # result = json.loads(analysis.choices[0].message.content)
        
        gemini_analysis_prompt = f"Analyze this claim and evidence. Return JSON with confidence_score - integer - from 1-100, verified_status - an integer in the range 0-100, and worthiness_score, an integer ranging from 1-100:\n\nClaim: {claim}\n\nEvidence: {json.dumps(evidence)}"

        generation_config_analysis = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_schema": content.Schema(
            type = content.Type.OBJECT,
            enum = [],
            required = ["confidence_score", "verified_status", "worthiness_score"],
            properties = {
            "confidence_score": content.Schema(
                type = content.Type.INTEGER,
            ),
            "verified_status": content.Schema(
                type = content.Type.INTEGER,
            ),
            "worthiness_score": content.Schema(
                type = content.Type.INTEGER,
            ),
            },
        ),
        "response_mime_type": "application/json",
        }

        model_analysis = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=generation_config_analysis,
        )

        chat_session_analysis = model_analysis.start_chat(
        history=[
        ]
        )

        response = chat_session_analysis.send_message(gemini_analysis_prompt)

        result = json.loads(response.text)

        return Claim(
            statement=claim,
            confidence_score=result["confidence_score"],
            verified_status=result["verified_status"],
            key_evidence=evidence,
            sources=sources,
            worthiness_score=result["worthiness_score"]
        )

    def generate_report(self, news_text: str) -> Dict:
        claims = self.extract_claims(news_text)
        analyzed_claims = []
        # for claim in claims:
        #     cl = ""
        #     if type(claim) == str:
        #         cl = claim
        #     else:
        #         for tup in claim.items():
        #             cl += tup[1] + " "
        #     analyzed_claims.append(self.analyze_claim(claim=cl))

        for claim in claims["claims"]:
            analyzed_claims.append(self.analyze_claim(claim=claim))

        # # Source credibility analysis
        # source_ratings = {}
        # for claim in analyzed_claims:
        #     for source in claim.sources:
        #         if source not in source_ratings:
        #             credibility_prompt = f"""Analyze this source's credibility: {source}
        #             Return a JSON with:
        #             - credibility_score (1-100)
        #             - bias_rating (Left/Center/Right)
        #             - fact_checking_history (1-100)
        #             - transparency_score (1-100)
        #             - expertise_level (1-100)
        #             - brief_explanation of the rating"""
                    
        #             source_analysis = self.source_correction.generate_content(credibility_prompt)
        #             source_ratings[source] = json.loads(source_analysis.text)

        # #sleep for one minute
        # time.sleep(60)

        report_prompt = f"""Generate a comprehensive fact-check analysis report for the following claims and evidence. Structure your analysis according to these sections:

        1. Overall Analysis:
        - Calculate an aggregate truth score (0-100) based on all claims
        - Provide a detailed reliability assessment explaining major patterns
        - List key findings that emerge from analyzing all claims together
        - Identify recurring patterns in misinformation/disinformation if any

        2. Claim-by-Claim Analysis:
        For each claim in: {json.dumps([vars(claim) for claim in analyzed_claims])}
        - Evaluate verification status with specific reasoning
        - Assign confidence level based on evidence strength
        - Analyze evidence quality:
        * Evaluate evidence strength
        * Identify information gaps
        * Note any contradictions in sources
        - Assess sources:
        * Evaluate credibility metrics
        * Check for bias patterns
        * Review fact-checking history

        3. Meta Analysis:
        - Assess potential impact on information ecosystem
        - Suggest specific actions for correction/prevention
        - Recommend strategies to prevent spread of misinformation

        Please be specific and provide numerical scores where applicable. Include direct quotes from evidence when relevant.
        """


        # Source Ratings: {json.dumps(source_ratings)}
        # Get additional correction sources for misinfo claims
        # correction_sources = {}
        # for claim in analyzed_claims:    
        #     if claim.verified_status < 50:
        #         correction_query = f"fact check {claim.statement} reliable sources"
        #         correction_results = self.search_client.retrieve_evidence({claim.statement: [correction_query]})
        #         correction_sources[claim.statement] = correction_results
            
        enhanced_report = self.gemini_client.generate_content(report_prompt)

        report_content = json.loads(enhanced_report.text)
            # "source_credibility": source_ratings,
        
        return {
            "timestamp": datetime.now().isoformat(),
            "original_text": news_text,
            "detailed_analysis": report_content,
        }
            # "correction_sources": correction_sources