from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Azure Foundry
    azure_foundry_endpoint: str = ""
    azure_foundry_api_key: str = ""
    azure_foundry_deployment: str = "gpt-4o"

    # Fabric
    fabric_workspace_id: str = ""
    fabric_lakehouse_id: str = ""
    fabric_client_id: str = ""
    fabric_client_secret: str = ""
    fabric_tenant_id: str = ""

    # Graph API
    graph_client_id: str = ""
    graph_client_secret: str = ""
    graph_tenant_id: str = ""
    graph_teams_channel_id: str = ""
    graph_teams_team_id: str = ""
    graph_sender_email: str = ""

    # External APIs
    opensanctions_api_key: str = ""
    opencorporates_api_key: str = ""
    companies_house_api_key: str = ""
    occrp_api_key: str = ""
    etherscan_api_key: str = ""
    news_api_key: str = ""

    # App
    app_env: str = "development"
    app_port: int = 8000
    confidence_threshold: float = 0.80

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
