"""Setup configuration for AI Travel Planner package."""

from setuptools import setup, find_packages
from pathlib import Path

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
with open(requirements_path) as f:
    requirements = f.read().splitlines()

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = ""
if readme_path.exists():
    with open(readme_path, encoding="utf-8") as f:
        long_description = f.read()

setup(
    name="ai-travel-planner",
    version="1.0.0",
    description="AI-powered travel itinerary planner using LLM",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Paras Chinchalkar",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/ai-travel-planner",
    packages=find_packages(),
    install_requires=requirements,
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="ai travel planner llm langchain groq streamlit",
)
