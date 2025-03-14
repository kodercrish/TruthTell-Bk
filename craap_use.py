#!/usr/bin/env python3
import os
import argparse
from craap_evaluator import CRAAPEvaluator

def main():
    parser = argparse.ArgumentParser(description='Evaluate news sources using the CRAAP method')
    parser.add_argument('--sources', default='news_sources.json', help='Path to the news sources JSON file')
    parser.add_argument('--max', type=int, help='Maximum number of sources to evaluate (default: all)')
    parser.add_argument('--threads', type=int, default=5, help='Number of concurrent threads (default: 5)')
    parser.add_argument('--output', default='results', help='Output directory for results (default: results)')
    args = parser.parse_args()

    # Create output directory if it doesn't exist
    if not os.path.exists(args.output):
        os.makedirs(args.output)

    # Initialize the evaluator
    evaluator = CRAAPEvaluator(sources_file=args.sources)
    
    # Run the evaluation
    print(f"Starting CRAAP evaluation of news sources...")
    evaluator.evaluate_all_sources(max_sources=args.max, threads=args.threads)
    
    # Save results in different formats
    csv_path = os.path.join(args.output, 'craap_evaluation_results_v2.xlsx')
    json_path = os.path.join(args.output, 'craap_evaluation_results_v2.json')
    # html_path = os.path.join(args.output, 'craap_evaluation_report.html')
    
    evaluator.save_results_to_csv(filename=csv_path)
    evaluator.save_results_to_json(filename=json_path)
    # evaluator.generate_html_report(filename=html_path)
    
    # # Print summary
    # results = evaluator.results
    # if results:
    #     avg_score = sum(r.get('total_score', 0) for r in results) / len(results)
    #     top_source = max(results, key=lambda x: x.get('total_score', 0))
    #     bottom_source = min(results, key=lambda x: x.get('total_score', 0))
        
        # print("\n=== EVALUATION SUMMARY ===")
        # print(f"Total sources evaluated: {len(results)}")
        # print(f"Average CRAAP score: {avg_score:.2f}/50")
        # print(f"Top rated source: {top_source['name']} ({top_source['total_score']}/50, {top_source['rating']})")
        # print(f"Lowest rated source: {bottom_source['name']} ({bottom_source['total_score']}/50, {bottom_source['rating']})")
        # print(f"\nDetailed results saved to:")
        # print(f"  - CSV: {csv_path}")
        # print(f"  - JSON: {json_path}")
        # print(f"  - HTML Report: {html_path}")
    # else:
    #     print("No results were generated. Check for errors in the evaluation process.")

if __name__ == "__main__":
    main()
