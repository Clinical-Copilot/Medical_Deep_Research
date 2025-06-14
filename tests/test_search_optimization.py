import asyncio
import json
import time
import sys
from pathlib import Path
from typing import Dict, List
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.tools.google_search import google_search

def evaluate_results(results: List[Dict]) -> Dict:
    """Evaluate the quality and relevance of search results."""
    metrics = {
        "total_results": len(results),
        "unique_domains": len(set(r.get("domain", "") for r in results)),
        "avg_snippet_length": sum(len(r.get("snippet", "")) for r in results) / len(results) if results else 0,
        "has_authoritative_sources": any(
            domain in ["www.cdc.gov", "www.who.int", "www.nih.gov", "www.mayoclinic.org", "www.nhs.uk"]
            for domain in [r.get("domain", "") for r in results]
        )
    }
    return metrics

async def test_search_optimization():
    """Test different numbers of search results to find optimal value."""
    test_queries = [
        "What are the symptoms of COVID-19?",
        "How to treat a common cold?",
        "What is the latest treatment for diabetes?"
    ]
    
    result_counts = [3, 5, 7, 10]
    results = {}
    
    print("\n🔍 Starting Search Optimization Test")
    print("=" * 80)
    
    for query in test_queries:
        print(f"\n📝 Testing Query: {query}")
        print("-" * 80)
        
        query_results = {}
        for num_results in result_counts:
            print(f"\nTesting with {num_results} results...")
            
            # Measure execution time
            start_time = time.time()
            search_results = google_search.invoke({"query": query, "num_results": num_results})
            execution_time = time.time() - start_time
            
            # Evaluate results
            metrics = evaluate_results(search_results.get("results", []))
            metrics["execution_time"] = execution_time
            
            query_results[num_results] = {
                "metrics": metrics,
                "results": search_results.get("results", [])
            }
            
            print(f"Execution time: {execution_time:.2f}s")
            print(f"Unique domains: {metrics['unique_domains']}")
            print(f"Has authoritative sources: {metrics['has_authoritative_sources']}")
            print(f"Average snippet length: {metrics['avg_snippet_length']:.0f} chars")
        
        results[query] = query_results
    
    # Print summary
    print("\n📊 Summary of Results")
    print("=" * 80)
    
    for query, query_data in results.items():
        print(f"\nQuery: {query}")
        print("-" * 40)
        for num_results, data in query_data.items():
            metrics = data["metrics"]
            print(f"\nNumber of results: {num_results}")
            print(f"Execution time: {metrics['execution_time']:.2f}s")
            print(f"Unique domains: {metrics['unique_domains']}")
            print(f"Has authoritative sources: {metrics['has_authoritative_sources']}")
            print(f"Average snippet length: {metrics['avg_snippet_length']:.0f} chars")

if __name__ == "__main__":
    asyncio.run(test_search_optimization()) 