# DuckDuckGo (no API key needed)
from duckduckgo_search import DDGS

from googlesearch import search
results = search("Agentic AI frameworks", advanced=True)
# print the results
print("--------------------------------")
for result in results:
    print(result)
    
print("--------------------------------")