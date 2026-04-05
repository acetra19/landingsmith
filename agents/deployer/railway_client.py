"""
Railway API client — simplified for single-project deployment.
Manages ONE Railway project that hosts the entire WebReach app
(dashboard + preview server + API).
"""

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

RAILWAY_GQL_URL = "https://backboard.railway.app/graphql/v2"


@dataclass
class ProjectInfo:
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

    async def get_project(self, project_id: str) -> Optional[ProjectInfo]:
        data = await self._gql(
            """
            query($id: String!) {
                project(id: $id) {
                    id
                    name
                    services { edges { node { id name } } }
                    environments { edges { node { id name } } }
                }
            }
            """,
            {"id": project_id},
        )
        project = data.get("project")
        if not project:
            return None

        svc_edges = project.get("services", {}).get("edges", [])
        env_edges = project.get("environments", {}).get("edges", [])

        return ProjectInfo(
            project_id=project["id"],
            name=project["name"],
            service_id=svc_edges[0]["node"]["id"] if svc_edges else "",
            environment_id=env_edges[0]["node"]["id"] if env_edges else "",
        )

    async def create_project(self, name: str = "webreach") -> ProjectInfo:
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
            {"input": {"name": name}},
        )
        project = data["projectCreate"]
        env_edges = project.get("environments", {}).get("edges", [])

        return ProjectInfo(
            project_id=project["id"],
            name=project["name"],
            environment_id=env_edges[0]["node"]["id"] if env_edges else "",
        )

    async def trigger_redeploy(self, service_id: str, environment_id: str) -> str:
        data = await self._gql(
            """
            mutation($input: ServiceInstanceRedeployInput!) {
                serviceInstanceRedeploy(input: $input)
            }
            """,
            {
                "input": {
                    "serviceId": service_id,
                    "environmentId": environment_id,
                }
            },
        )
        return data.get("serviceInstanceRedeploy", "")

    async def get_service_domain(self, service_id: str, environment_id: str) -> str:
        data = await self._gql(
            """
            query($serviceId: String!, $environmentId: String!) {
                serviceInstance(serviceId: $serviceId, environmentId: $environmentId) {
                    domains { serviceDomains { domain } }
                }
            }
            """,
            {"serviceId": service_id, "environmentId": environment_id},
        )
        instance = data.get("serviceInstance", {})
        service_domains = (
            instance.get("domains", {}).get("serviceDomains", [])
        )
        if service_domains:
            return service_domains[0].get("domain", "")
        return ""

    async def set_variables(
        self, service_id: str, environment_id: str, variables: dict
    ) -> None:
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
                    "variables": variables,
                }
            },
        )

    async def close(self):
        await self._client.aclose()


class RailwayAPIError(Exception):
    pass
