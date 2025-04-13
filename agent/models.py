import os
from langchain.chat_models import init_chat_model
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from google.cloud import aiplatform
from dotenv import load_dotenv

# Load the .env file
load_dotenv()

gemini_api_key = os.getenv("GEMINI_API_KEY")
aiplatform.init(api_key=gemini_api_key)
model = init_chat_model("gemini-2.0-flash-001", model_provider="google_vertexai", ) 

if __name__=="__main__":
    print("Executed Successfully")