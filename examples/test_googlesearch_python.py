import asyncio
from tools.websearch.googlesearch_python_search import GoogleSearchPythonTool

async def main():
    tool = GoogleSearchPythonTool()
    
    results = await tool.execute({"query": "agentic AI frameworks", "max_results": 5})
    
    
    print("--------------------------------")
    for enum, result in enumerate(results.result):
        print(f"result {enum+1}:")
        print("--------------------------------")
        print(f"title: {result['title']}")
        print(f"url: {result['url']}")
        print(f"snippet: {result['snippet']}")
        print(f"relevance: {result['relevance']}")
        print(f"result.metadata: {result['metadata']}")
        print("--------------------------------")
    print("--------------------------------")

if __name__ == "__main__":
    asyncio.run(main())