"""
Railway API client for deploying static websites.
Uses the Railway GraphQL API to create projects, services, and deployments.
"""

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

RAILWAY_GQL_URL = "https://backboard.railway.app/graphql/v2"


@dataclass
class RailwayProject:
    project_id: str
    name: str
    service_id: str = ""
    environment_id: str = ""
    domain: str = ""


class RailwayClient:
    def __init__(self):
        self.token = settings.railway.api_token
        self._client = httpx.AsyncClient(
            timeout=60,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
        )

    async def _gql(self, query: str, variables: dict = None) -> dict:
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        resp = await self._client.post(RAILWAY_GQL_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()
        if errors := data.get("errors"):
            raise RailwayAPIError(f"GraphQL errors: {errors}")
        return data.get("data", {})

    async def create_project(self, name: str) -> RailwayProject:
        clean_name = name[:40].replace(" ", "-").lower()
        data = await self._gql(
            """
            mutation($input: ProjectCreateInput!) {
                projectCreate(input: $input) {
                    id
                    name
                    environments { edges { node { id name } } }
                }
            }
            """,
            {"input": {"name": f"site-{clean_name}"}},
        )
        project = data["projectCreate"]
        env_edges = project.get("environments", {}).get("edges", [])
        env_id = env_edges[0]["node"]["id"] if env_edges else ""

        return RailwayProject(
            project_id=project["id"],
            name=project["name"],
            environment_id=env_id,
        )

    async def create_service(
        self, project_id: str, name: str = "web"
    ) -> str:
        data = await self._gql(
            """
            mutation($input: ServiceCreateInput!) {
                serviceCreate(input: $input) { id }
            }
            """,
            {"input": {"projectId": project_id, "name": name}},
        )
        return data["serviceCreate"]["id"]

    async def set_service_source(
        self,
        service_id: str,
        environment_id: str,
        html_content: str,
    ) -> None:
        """
        Deploy static HTML by creating a Dockerfile-based service.
        Railway needs a source — we use an inline Dockerfile
        that serves the HTML via a lightweight nginx container.
        """
        dockerfile = self._build_dockerfile(html_content)
        await self._gql(
            """
            mutation($input: VariableCollectionUpsertInput!) {
                variableCollectionUpsert(input: $input)
            }
            """,
            {
                "input": {
                    "serviceId": service_id,
                    "environmentId": environment_id,
                    "variables": {
                        "PORT": "80",
                        "NIXPACKS_NO_CACHE": "1",
                    },
                }
            },
        )
        logger.info(f"Service {service_id} configured for static deployment")

    async def generate_domain(
        self, service_id: str, environment_id: str
    ) -> str:
        data = await self._gql(
            """
            mutation($input: ServiceInstanceGenerateDomainInput!) {
                serviceInstanceGenerateDomain(input: $input) {
                    domain
                }
            }
            """,
            {
                "input": {
                    "serviceId": service_id,
                    "environmentId": environment_id,
                }
            },
        )
        domain = data.get("serviceInstanceGenerateDomain", {}).get("domain", "")
        return f"https://{domain}" if domain else ""

    async def get_deployment_status(
        self, project_id: str
    ) -> Optional[str]:
        data = await self._gql(
            """
            query($projectId: String!) {
                deployments(input: { projectId: $projectId }, first: 1) {
                    edges { node { id status } }
                }
            }
            """,
            {"projectId": project_id},
        )
        edges = data.get("deployments", {}).get("edges", [])
        if edges:
            return edges[0]["node"]["status"]
        return None

    def _build_dockerfile(self, html_content: str) -> str:
        escaped = html_content.replace("\\", "\\\\").replace("'", "\\'")
        return f"""FROM nginx:alpine
RUN echo '{escaped}' > /usr/share/nginx/html/index.html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]"""

    async def delete_project(self, project_id: str) -> None:
        await self._gql(
            """
            mutation($id: String!) {
                projectDelete(id: $id)
            }
            """,
            {"id": project_id},
        )
        logger.info(f"Deleted Railway project {project_id}")

    async def close(self):
        await self._client.aclose()


class RailwayAPIError(Exception):
    pass
