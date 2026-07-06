from livekit.agents import llm

from .common import logger

PORTFOLIO_DATA = {
    "skills": {
        "machine_learning": ["Python", "TensorFlow", "PyTorch", "Scikit-learn", "NLP"],
        "web_development": ["React", "Node.js", "FastAPI", "Django", "PostgreSQL"],
        "data_engineering": ["Apache Spark", "Airflow", "BigQuery", "ETL Pipelines"],
        "voice_ai": ["LiveKit", "Real-time Processing", "WebRTC"],
        "devops": ["Docker", "Kubernetes", "AWS", "CI/CD"],
    },
    "projects": {
        "voice_assistant": {
            "skills": ["voice_ai", "machine_learning", "web_development"],
            "description": "Real-time voice AI assistant with contact management",
        },
        "ml_pipeline": {
            "skills": ["machine_learning", "data_engineering"],
            "description": "Production ML pipeline with model serving",
        },
        "cloud_platform": {
            "skills": ["devops", "web_development", "data_engineering"],
            "description": "Scalable cloud-based platform",
        },
    },
    "contact_info": {
        "email": "mohit@example.com",
        "phone": "(555) 123-4567",
        "linkedin": "linkedin.com/in/mohitsharma",
        "github": "github.com/mohitsharma",
    },
}


@llm.function_tool(
    description="Tell user about Mohit's skills in a specific area (e.g., 'machine learning')."
)
async def tell_about_skill(skill_area: str) -> str:
    """Provide information about Mohit's skills."""
    try:
        skill_lower = skill_area.lower()

        if skill_lower in PORTFOLIO_DATA["skills"]:
            skills = PORTFOLIO_DATA["skills"][skill_lower]
            return (
                f"{skill_area.title()} Skills:\n"
                f"Mohit has expertise in: {', '.join(skills)}\n"
                f"Feel free to ask about any specific projects or experiences!"
            )

        return (
            f"Skill area '{skill_area}' not found. "
            f"Available: {', '.join(PORTFOLIO_DATA['skills'].keys())}"
        )
    except Exception as e:
        logger.error(f"Error describing skill: {e}")
        return f"Failed to retrieve skill info: {e}"


@llm.function_tool(description="Find projects matching user's problem or need.")
async def find_relevant_projects(problem_description: str) -> str:
    """Find relevant projects based on problem description."""
    try:
        problem_lower = problem_description.lower()
        matched_projects = []

        keywords = {
            "voice": ["voice_assistant"],
            "machine learning": ["ml_pipeline"],
            "data": ["ml_pipeline", "cloud_platform"],
            "cloud": ["cloud_platform"],
            "real-time": ["voice_assistant"],
            "scale": ["cloud_platform"],
        }

        for keyword, projects in keywords.items():
            if keyword in problem_lower:
                matched_projects.extend(projects)

        matched_projects = list(set(matched_projects))

        if not matched_projects:
            matched_projects = list(PORTFOLIO_DATA["projects"].keys())

        result = "Relevant Projects:\n"
        for project in matched_projects:
            if project in PORTFOLIO_DATA["projects"]:
                proj_data = PORTFOLIO_DATA["projects"][project]
                result += f"\n- {project.replace('_', ' ').title()}\n"
                result += f"  {proj_data['description']}\n"

        logger.info(f"Found {len(matched_projects)} matching projects")
        return result
    except Exception as e:
        logger.error(f"Error finding projects: {e}")
        return f"Failed to find projects: {e}"


@llm.function_tool(
    description="Get Mohit's contact information (email, phone, LinkedIn, GitHub)."
)
async def get_contact_info(contact_type: str = "all") -> str:
    """Retrieve Mohit's contact information."""
    try:
        contacts = PORTFOLIO_DATA["contact_info"]

        if contact_type == "all":
            info = "Contact Information:\n"
            info += f"Email: {contacts['email']}\n"
            info += f"Phone: {contacts['phone']}\n"
            info += f"LinkedIn: {contacts['linkedin']}\n"
            info += f"GitHub: {contacts['github']}"
            return info
        if contact_type in contacts:
            return f"{contact_type.title()}: {contacts[contact_type]}"
        return f"Contact type '{contact_type}' not found."
    except Exception as e:
        logger.error(f"Error getting contact info: {e}")
        return f"Failed to retrieve contact info: {e}"
