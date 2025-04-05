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
from routes.news_summ import get_news
from urllib.parse import urlparse
import threading
import concurrent.futures

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
            required = ["overall_analysis", "claim_analysis"],
            properties = {
            "overall_analysis": content.Schema(
                type = content.Type.OBJECT,
                enum = [],
                required = ["truth_score", "reliability_assessment", "key_findings"],
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
                )
                },
            ),
            "claim_analysis": content.Schema(
                type = content.Type.ARRAY,
                items = content.Schema(
                type = content.Type.OBJECT,
                required = ["claim", "verification_status", "confidence_level", "misinformation_impact"],
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
                },
                ),
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
            type = content.Type.ARRAY,
            items = content.Schema(
            type = content.Type.OBJECT,
            required = ["source", "credibility_score", "fact_checking_history", "transparency_score", "expertise_level", "additional_metrics"],
            properties = {
            "source": content.Schema(
                type = content.Type.STRING,
            ),
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
            }),
        ),
        "response_mime_type": "application/json",
        }


        #############################################################
        self.client = Groq(api_key=groq_api_key)
        self.search_client = SerperEvidenceRetriever(api_key=serper_api_key)
        
        #############################################################
        self.gemini_client = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config=generation_config,
        )
        self.gemini_chat = self.gemini_client.start_chat(
            history=[]
        )
        
        #############################################################
        self.source_correction = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config=generation_config_sources,
        )
        self.gemini_chat_sources = self.source_correction.start_chat(
            history=[]
        )
    
    def generate_verification_questions(self, claim: str) -> List[str]:
        # prompt = {
        #     "role": "user",
        #     "content": f"Generate specific questions to verify this claim. Make a maximum of 5 questions for the claim. Return as JSON array:\n\n{claim}"
        # }
        
        # response = self.client.chat.completions.create(
        #     model="llama-3.3-70b-versatile",
        #     messages=[prompt],
        #     temperature=0.3,
        #     response_format={"type": "json_object"}
        # )
        
        gemini_questions_prompt = f"Generate specific questions to verify this claim. Make a maximum of 3 questions for the claim. Return as JSON array:\n\n{claim}"

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
            model_name="gemini-2.0-flash",
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

    def analyze_source_credibility(self, sources):
        """
        Analyze the credibility of news sources using Gemini
        
        Args:
            sources: List of source URLs to analyze
            
        Returns:
            Dictionary containing source credibility analysis
        """
        if not sources:
            return []
        
        # Extract domain names from URLs for better analysis
        domains = [urlparse(source).netloc for source in sources]
        
        # Create a prompt that asks Gemini to evaluate the sources
        source_analysis_prompt = f"""
        Analyze the credibility of these news sources:
        
        {domains}
        
        For each source, evaluate:
        1. Credibility score (1-100)
        2. Fact-checking history (1-100)
        3. Transparency score (1-100)
        4. Expertise level (1-100)
        
        Also include these additional metrics:
        - Citation score (1-100)
        - Peer recognition (1-100)
        
        Return the analysis as a structured JSON array with one object per source.
        """
        
        # Use the gemini_chat_sources which has the appropriate schema configuration
        response = self.gemini_chat_sources.send_message(source_analysis_prompt)
        
        try:
            source_ratings = json.loads(response.text)
            
            # Map the domain analysis back to the original URLs
            result = []
            for i, url in enumerate(sources):
                if i < len(source_ratings):
                    rating = source_ratings[i]
                    rating['url'] = url
                    result.append(rating)
            
            return result
        except Exception as e:
            print(f"Error parsing source credibility analysis: {str(e)}")
            return []

    def _generate_enhanced_report(self, news_summ, evidences, result_dict):
        """Helper method to generate enhanced report in a separate thread"""
        report_prompt = f"""Generate a comprehensive fact-check analysis report for this news claim and supporting evidence. Structure your analysis according to these sections:

        1. Overall Analysis:
        - Calculate a truth score (0-100) based on evidence verification
        - Provide a detailed reliability assessment of the claim
        - List key findings from cross-referencing evidence
        - Identify any patterns of inaccuracy or misrepresentation

        2. Evidence Analysis for Claim: {news_summ}
        Evidence Sources:
        {json.dumps(evidences)}

        Analyze:
        - Verification status with specific reasoning
        - Confidence level based on evidence strength
        - Potential biases or agendas revealed by evidence
        - Severity of misinformation impact
        
        Please provide numerical scores where applicable and cite specific evidence examples to support your analysis.
        """
                    
        enhanced_report = self.gemini_client.generate_content(report_prompt)
        result_dict['detailed_analysis'] = json.loads(enhanced_report.text)

    def _analyze_sources_credibility(self, sources, result_dict):
        """Helper method to analyze source credibility in a separate thread"""
        source_credibility = self.analyze_source_credibility(sources[:5])  # Analyze top 5 sources
        result_dict['source_credibility'] = source_credibility
    
    def generate_report(self, news_summ: str) -> Dict:
        ### FUTURE PROSPECT ###
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
        ### FUTURE PROSPECT ###
        
        verif_ques = self.generate_verification_questions(news_summ)["questions"]
        
        # retrieve evidences for each question from the search client
        claim_queries_dict = {news_summ: [q for q in verif_ques]}
        
        evidence_dict = self.search_client.retrieve_evidence(claim_queries_dict=claim_queries_dict)
        
        # Collect evidence for each question
        evidences = []
        sources = []
        for claim, evidence in evidence_dict.items():
            for evidence_item in evidence:
                ev_news = get_news(evidence_item['url'])
                if (ev_news["status"] == "success"):
                    evidences.append(ev_news["summary"])
                    sources.append(evidence_item['url'])
        
        # Use a dictionary to store results from threads
        thread_results = {}
        
        # Create threads for parallel execution
        report_thread = threading.Thread(
            target=self._generate_enhanced_report,
            args=(news_summ, evidences, thread_results)
        )
        
        source_thread = threading.Thread(
            target=self._analyze_sources_credibility,
            args=(sources, thread_results)
        )
        
        # Start both threads
        report_thread.start()
        source_thread.start()
        
        # Wait for both threads to complete
        report_thread.join()
        source_thread.join()

        ### FUTURE PROSPECT ###
        # Source Ratings: {json.dumps(source_ratings)}
        # Get additional correction sources for misinfo claims
        # correction_sources = {}
        # for claim in analyzed_claims:    
        #     if claim.verified_status < 50:
        #         correction_query = f"fact check {claim.statement} reliable sources"
        #         correction_results = self.search_client.retrieve_evidence({claim.statement: [correction_query]})
        #         correction_sources[claim.statement] = correction_results
        ### FUTURE PROSPECT ###
            
         # Return the combined results
        return {
            "timestamp": datetime.now().isoformat(),
            "original_text": news_summ,
            "detailed_analysis": thread_results.get('detailed_analysis', {}),
            "sources": sources[:5],
            "source_credibility": thread_results.get('source_credibility', [])
        }
            ### FUTURE PROSPECT ###
            # "correction_sources": correction_sources
            ### FUTURE PROSPECT ###