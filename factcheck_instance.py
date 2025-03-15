from fc.fact_checker import FactChecker
import os

fact_checker_instance = FactChecker(
    groq_api_key=os.environ.get("GROQ_API_KEY"),
    serper_api_key=os.environ.get("SERPER_API_KEY")
)