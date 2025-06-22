# import os
# from googleapiclient.discovery import build

# # Replace with your actual API key and Search Engine ID
# API_KEY = "AIzaSyBPxGtYEt1HATWYFqDjdtfnyVbMhG0h0X8"
# SEARCH_ENGINE_ID = "91b5cacfcbf6041c7"

# def Google_Search(query, num_results=10, start_index=1):
#     """
#     Performs a Google Custom Search and returns the results.

#     Args:
#         query (str): The search query string.
#         num_results (int): The number of search results to return (max 10 per request).
#         start_index (int): The index of the first result to return (for pagination).

#     Returns:
#         list: A list of dictionaries, each representing a search result.
#     """
#     try:
#         service = build("customsearch", "v1", developerKey=API_KEY)
#         res = service.cse().list(
#             q=query,
#             cx=SEARCH_ENGINE_ID,
#             num=num_results,
#             start=start_index
#         ).execute()

#         results = []
#         if 'items' in res:
#             for item in res['items']:
#                 results.append({
#                     'title': item.get('title'),
#                     'link': item.get('link'),
#                     'snippet': item.get('snippet'),
#                     'displayLink': item.get('displayLink')
#                 })
#         return results
#     except Exception as e:
#         print(f"An error occurred: {e}")
#         return []

# search_query = "what can I do if I get covid"

# print(f"Searching for: '{search_query}'")

# # Get the first 10 results
# search_results_page1 = Google_Search(search_query)
# if search_results_page1:
#     print("\n--- Page 1 Results ---")
#     for i, result in enumerate(search_results_page1):
#         print(f"Result {i+1}:")
#         print(f"  Title: {result['title']}")
#         print(f"  Link: {result['link']}")
#         print(f"  Snippet: {result['snippet']}")
#         print("-" * 20)
# else:
#     print("No results found for page 1.")

# # Get the next 10 results (for pagination, if available)
# # Note: You'd typically check 'res.get('queries', {}).get('nextPage')' for a 'startIndex'
# # to determine if there's a next page.
# search_results_page2 = Google_Search(search_query, start_index=11)
# if search_results_page2:
#     print("\n--- Page 2 Results ---")
#     for i, result in enumerate(search_results_page2):
#         print(f"Result {i+11}:") # Adjust index for display
#         print(f"  Title: {result['title']}")
#         print(f"  Link: {result['link']}")
#         print(f"  Snippet: {result['snippet']}")
#         print("-" * 20)
# else:
#     print("No results found for page 2 (or no more pages).")