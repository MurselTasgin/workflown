import asyncio
from tools.webpage_parser import WebPageParserTool

async def main():
    tool = WebPageParserTool()
    
    try:
        results = await tool.execute({"urls": ["https://www.akbank.com.tr"]})
        
        print("--------------------------------")
        for key, value in results.result.items():
            print(f"key: {key}")
            print(f"value: {value}")

            print("--------------------------------")
    finally:
        await tool.cleanup()

if __name__ == "__main__":
    asyncio.run(main())