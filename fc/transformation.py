import json
import os
import dotenv
import time
import sys
from datetime import datetime

dotenv.load_dotenv()

os.makedirs("reports", exist_ok=True)


def handler(factcheck_data):
    return factcheck_data
    # fact_checker = FactChecker(
    #     groq_api_key=os.getenv("GROQ_API_KEY"),
    #     serper_api_key=os.getenv("SERPER_API_KEY")
    # )

    # report_factchecked = fact_checker.generate_report(data)

    # return report_factchecked
    
    ################# Example usage #################
    # news_list = [
    #     "Vijay Rupani turned his back on BJP and joined AAP",
    #     "Bengaluru to host world's largest event ever by AliBaba in January, 2025. They are planning to provide jobs to every person eligibe to work in the whole country. Supposedly, it is going to allow every person alive in the world to attend the event offline, in Chinnaswamy Stadium.",
    #     "The Indian government has decided to ban all cryptocurrencies in the country. The decision was taken after a meeting with the Prime Minister and the Finance Minister.",
    #     "The American government has officially declared that Indians are the best people in the world.",
    #     "U.K. Minister Tulip Siddiq resigns over financial ties with aunt Sheikh Hasina",
    #     "Hockey India League: A Soorma without Harmanpreet loses 1-2 to Gonasika",
    #     "FIR against AAP for posting AI-generated videos of PM Modi, Amit Shah on X",
    #     "Naval combatants to strengthen India's efforts to be global leader in defence: PM Modi",
    #     "24, Akbar Road: Wrapping within its walls, history of Congress and much more",
    #     "After death of Kerala youth, India reiterates demand to release all Indians serving in Russian military",
    #     "FIR registered against Haryana BJP chief, singer for alleged gangrape in Kasauli",
    #     "Smriti Irani, Shekhar Kapur in reconstituted Prime Ministers' Museum and Library Society"
    # ]
    
    # for i, news in enumerate(news_list):
    #     report = fact_checker.generate_report(news)
        
    #     # Generate unique filename using timestamp and index
    #     timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    #     filename = f'reports/report_{timestamp}_{i}.json'
        
    #     # Write report to JSON file
    #     with open(filename, 'w', encoding='utf-8') as f:
    #         json.dump(report, f, indent=2)
        
    #     #print(f"Report saved to {filename}")
    #     time.sleep(90)
