"""
Itinerary generation chain using LangChain and Groq.
"""

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from typing import List
from src.config.config import GROQ_API_KEY

# ✅ FIX: Use constant for model name (defined once)
GROQ_MODEL = "llama-3.3-70b-versatile"

# Prompt template for itinerary generation
itinerary_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an expert travel assistant specializing in personalized trip planning.
Create a detailed day trip itinerary for {city} based on these interests: {interests}.

Format your response as:
- Morning activities
- Afternoon activities  
- Evening activities

Include specific recommendations for:
- Must-visit attractions
- Local cuisine/restaurants
- Transportation tips
- Estimated costs (if applicable)

Keep it concise but informative."""),
    ("human", "Create an itinerary for my day trip!"),
])


def get_llm() -> ChatGroq:
    """
    Lazily construct and return a ChatGroq client with production settings.
    
    Returns:
        ChatGroq: Configured LLM client
        
    Raises:
        RuntimeError: If GROQ_API_KEY is not set
    """
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Please set the GROQ_API_KEY environment variable "
            "or add it to your Streamlit secrets/.env file."
        )
    
    # ✅ FIX: Use constant instead of hardcoded model name
    return ChatGroq(
        groq_api_key=GROQ_API_KEY,
        model=GROQ_MODEL,  # Use constant
        temperature=0.7,
        max_retries=3,
        timeout=30,
        max_tokens=1024,
    )


def generate_itinerary(city: str, interests: List[str]) -> str:  # ✅ FIX: Added return type hint
    """
    Generate a personalized travel itinerary using Groq LLM.
    
    Args:
        city: Destination city name
        interests: List of user interests/preferences
        
    Returns:
        str: Generated itinerary content
        
    Raises:
        RuntimeError: If LLM invocation fails
    """
    try:
        llm = get_llm()
        
        # Format interests as comma-separated string
        interests_str = ", ".join(interests) if interests else "general sightseeing"
        
        # Invoke LLM with formatted prompt
        response = llm.invoke(
            itinerary_prompt.format_messages(
                city=city,
                interests=interests_str
            )
        )
        
        return response.content
        
    except Exception as e:
        raise RuntimeError(f"Failed to generate itinerary: {str(e)}") from e
