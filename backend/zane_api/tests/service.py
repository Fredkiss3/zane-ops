import json
import random
from typing import Any
from unittest.mock import patch, Mock, MagicMock

import docker.errors
from django.conf import settings
from django.urls import reverse
from docker.types import EndpointSpec
from rest_framework import status

from . import AuthAPITestCase
from ..models import Project, DockerRegistryService, DockerDeployment, Volume, PortConfiguration, URL
from ..services import get_service_resource_name, get_volume_resource_name, size_in_bytes


class FakeDockerClient:
    class FakeVolume:
        def __init__(self, parent: 'FakeDockerClient', name: str, size_limit: str = None):
            self.name = name
            self.parent = parent
            self.size_limit = size_limit

        def remove(self, force: bool):
            if self.parent.raise_error:
                raise docker.errors.APIError("Unknown error")
            self.parent.volume_map.pop(self.name)

    class FakeService:
        def __init__(self, parent: 'FakeDockerClient', name: str, volumes: dict[str, str] = None,
                     env: dict[str, str] = None, endpoint: EndpointSpec = None):
            self.name = name
            self.parent = parent
            self.attached_volumes = {} if volumes is None else volumes
            self.env = {} if env is None else env
            self.endpoint = endpoint

    def __init__(self, raise_error: bool = False):
        self.volumes = MagicMock()
        self.services = MagicMock()
        self.images = MagicMock()
        self.raise_error = raise_error
        self.is_logged_in = False
        self.downloaded_images: list[str] = []
        self.credentials = {}

        self.images.pull = self.images_pull
        self.services.create = self.services_create
        self.services.get = self.services_get
        self.volumes.create = self.volumes_create
        self.volumes.get = self.volumes_get
        self.volume_map = {}  # type: dict[str, FakeDockerClient.FakeVolume]
        self.service_map = {}  # type: dict[str, FakeDockerClient.FakeService]

    def volumes_create(self, name: str, driver_opts: dict[str, str], **kwargs):
        self.volume_map[name] = FakeDockerClient.FakeVolume(parent=self, name=name, size_limit=driver_opts.get('o'))

    def volumes_get(self, name: str):
        if name not in self.volume_map:
            raise docker.errors.NotFound("Volume Not found")
        return self.volume_map[name]

    def services_get(self, name: str):
        if name not in self.service_map:
            raise docker.errors.NotFound("Volume Not found")
        return self.service_map[name]

    def services_create(self, name: str, mounts: list[str], env: list[str],
                        endpoint_spec: Any,
                        networks: list[str], image: str,
                        restart_policy: Any, update_config: Any, command: str | None,
                        labels: dict[str, str]):
        volumes: dict[str, str] = {}
        for mount in mounts:
            volume_name, mount_path, _ = mount.split(":")
            volumes[volume_name] = mount_path

        envs: dict[str, str] = {}
        for var in env:
            key, value = var.split("=")
            envs[key] = value

        self.service_map[name] = FakeDockerClient.FakeService(
            parent=self,
            name=name,
            volumes=volumes,
            env=envs,
            endpoint=endpoint_spec
        )

    def login(self, username: str, password: str, registry: str, **kwargs):
        if username != 'fredkiss3' or password != 's3cret' or registry != 'https://dcr.fredkiss.dev/':
            raise docker.errors.APIError("Bad Credentials")
        self.credentials = dict(username=username, password=password)
        self.is_logged_in = True

    def images_pull(self, image: str, auth_config: dict):
        if auth_config:
            if not image.startswith("dcr.fredkiss.dev"):
                raise docker.errors.APIError("Invalid credentials")

            if not image.startswith("dcr.fredkiss.dev/gh-next"):
                raise docker.errors.NotFound("This image does not exist")
            self.downloaded_images.append(image)
        else:
            if image == 'nonexistent':
                raise docker.errors.ImageNotFound("This image does not exist")


class DockerServiceCreateViewTest(AuthAPITestCase):
    @patch("zane_api.services.get_docker_client", return_value=FakeDockerClient())
    def test_create_simple_service(self, mock_fake_docker: Mock):
        owner = self.loginUser()
        p = Project.objects.create(name="KISS CAM", slug="kiss-cam", owner=owner)

        create_service_payload = {
            "name": "cache db",
            "image": "redis:alpine",
        }

        response = self.client.post(
            reverse('zane_api:services.docker', kwargs={"project_slug": p.slug}),
            data=create_service_payload
        )
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        data = response.json().get('service')
        self.assertIsNotNone(data)

        created_service = DockerRegistryService.objects.filter(slug="cache-db").first()
        self.assertIsNotNone(created_service)
        fake_docker_client: FakeDockerClient = mock_fake_docker.return_value
        self.assertEqual(1, len(fake_docker_client.service_map))

        deployment = DockerDeployment.objects.filter(service=created_service).first()
        self.assertIsNotNone(deployment)

    @patch("zane_api.services.get_docker_client", return_value=FakeDockerClient())
    def test_create_service_with_volume(self, mock_fake_docker: Mock):
        owner = self.loginUser()
        p = Project.objects.create(name="KISS CAM", slug="kiss-cam", owner=owner)

        create_service_payload = {
            "name": "cache db",
            "image": "redis:alpine",
            "volumes": [
                {
                    "name": "REDIS Data volume",
                    "mount_path": "/data"
                }
            ]
        }

        response = self.client.post(
            reverse('zane_api:services.docker', kwargs={"project_slug": p.slug}),
            data=json.dumps(create_service_payload),
            content_type='application/json'
        )
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        created_service: DockerRegistryService = DockerRegistryService.objects.filter(slug="cache-db").first()
        self.assertIsNotNone(created_service)
        self.assertEqual(1, created_service.volumes.count())

        created_volume = created_service.volumes.first()

        fake_docker_client: FakeDockerClient = mock_fake_docker.return_value
        self.assertEqual(1, len(fake_docker_client.volume_map))

        fake_service = fake_docker_client.service_map[get_service_resource_name(created_service)]
        self.assertEqual(1, len(fake_service.attached_volumes))
        self.assertIsNotNone(fake_service.attached_volumes.get(get_volume_resource_name(created_volume)))

    @patch("zane_api.services.get_docker_client", return_value=FakeDockerClient())
    def test_create_service_with_volume_and_size_limit(self, mock_fake_docker: Mock):
        owner = self.loginUser()
        p = Project.objects.create(name="KISS CAM", slug="kiss-cam", owner=owner)

        create_service_payload = {
            "name": "cache db",
            "image": "redis:alpine",
            "volumes": [
                {
                    "name": "redis_data_volume",
                    "mount_path": "/data",
                    "size": {
                        "n": 500,
                        "unit": "MB"
                    },
                }
            ]
        }

        response = self.client.post(
            reverse('zane_api:services.docker', kwargs={"project_slug": p.slug}),
            data=json.dumps(create_service_payload),
            content_type='application/json'
        )
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        created_service: DockerRegistryService = DockerRegistryService.objects.filter(slug="cache-db").first()
        volume: Volume = created_service.volumes.first()

        self.assertEqual(size_in_bytes(500, 'MB'), volume.size_limit)

        fake_docker_client: FakeDockerClient = mock_fake_docker.return_value
        fake_volume = list(fake_docker_client.volume_map.values())[0]
        self.assertIsNotNone(fake_volume.size_limit)

    @patch("zane_api.services.get_docker_client", return_value=FakeDockerClient())
    def test_create_service_with_env_and_command(self, mock_fake_docker: Mock):
        owner = self.loginUser()
        p = Project.objects.create(name="KISS CAM", slug="kiss-cam", owner=owner)

        create_service_payload = {
            "name": "cache db",
            "image": "redis:alpine",
            "command": "redis-server --requirepass ${REDIS_PASSWORD}",
            "env": {
                "REDIS_PASSWORD": "strongPassword123"
            },
        }

        response = self.client.post(
            reverse('zane_api:services.docker', kwargs={"project_slug": p.slug}),
            data=json.dumps(create_service_payload),
            content_type='application/json'
        )
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        created_service: DockerRegistryService = DockerRegistryService.objects.filter(slug="cache-db").first()
        env = created_service.env_variables.first()

        self.assertIsNotNone(created_service.command)
        self.assertIsNotNone(env)

        fake_docker_client: FakeDockerClient = mock_fake_docker.return_value
        fake_service = fake_docker_client.service_map[get_service_resource_name(created_service)]
        self.assertEqual(1, len(fake_service.env))
        self.assertEqual("strongPassword123", fake_service.env.get("REDIS_PASSWORD"))

    @patch("zane_api.services.get_docker_client", return_value=FakeDockerClient())
    def test_create_service_with_port(self, mock_fake_docker: Mock):
        owner = self.loginUser()
        p = Project.objects.create(name="KISS CAM", slug="kiss-cam", owner=owner)

        create_service_payload = {
            "name": "noSQL db",
            "image": "redis:alpine",
            "ports": [
                {
                    "public": 6383,
                    "forwarded": 6379
                }
            ]
        }

        response = self.client.post(
            reverse('zane_api:services.docker', kwargs={"project_slug": p.slug}),
            data=json.dumps(create_service_payload),
            content_type='application/json'
        )
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        created_service: DockerRegistryService = DockerRegistryService.objects.filter(slug="nosql-db").first()
        port: PortConfiguration = created_service.port_config.first()

        self.assertIsNotNone(port)
        self.assertEqual(6383, port.host)
        self.assertEqual(6379, port.forwarded)

        fake_docker_client: FakeDockerClient = mock_fake_docker.return_value
        fake_service = fake_docker_client.service_map[get_service_resource_name(created_service)]

        self.assertIsNotNone(fake_service.endpoint)

        port_in_docker = fake_service.endpoint.get('Ports')[0]
        self.assertEqual(6383, port_in_docker["PublishedPort"])
        self.assertEqual(6379, port_in_docker["TargetPort"])

    @patch("zane_api.services.get_docker_client", return_value=FakeDockerClient())
    def test_create_service_with_http_port(self, mock_fake_docker: Mock):
        owner = self.loginUser()
        p = Project.objects.create(name="KISS CAM", slug="kiss-cam", owner=owner)

        create_service_payload = {
            "name": "Adminer UI",
            "image": "adminer:latest",
            "ports": [
                {
                    "forwarded": 8080
                }
            ]
        }

        response = self.client.post(
            reverse('zane_api:services.docker', kwargs={"project_slug": p.slug}),
            data=json.dumps(create_service_payload),
            content_type='application/json'
        )
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        created_service: DockerRegistryService = DockerRegistryService.objects.filter(slug="adminer-ui").first()
        port: PortConfiguration = created_service.port_config.first()

        self.assertIsNotNone(port)
        self.assertEqual(80, port.host)
        self.assertEqual(8080, port.forwarded)

        fake_docker_client: FakeDockerClient = mock_fake_docker.return_value
        fake_service = fake_docker_client.service_map[get_service_resource_name(created_service)]

        self.assertIsNone(fake_service.endpoint)

    @patch("zane_api.services.get_docker_client", return_value=FakeDockerClient())
    def test_create_service_with_port_create_a_domain(self, mock_fake_docker: Mock):
        owner = self.loginUser()
        p = Project.objects.create(name="KISS CAM", slug="kiss-cam", owner=owner)

        create_service_payload = {
            "name": "Adminer UI",
            "image": "adminer:latest",
            "ports": [
                {
                    "forwarded": 8080
                }
            ]
        }

        response = self.client.post(
            reverse('zane_api:services.docker', kwargs={"project_slug": p.slug}),
            data=json.dumps(create_service_payload),
            content_type='application/json'
        )
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        created_service: DockerRegistryService = DockerRegistryService.objects.filter(slug="adminer-ui").first()

        default_url: URL = created_service.urls.first()
        self.assertIsNotNone(default_url)
        self.assertEqual(f"{p.slug}-{created_service.slug}.{settings.ROOT_DOMAIN}", default_url.domain)
        self.assertEqual("/", default_url.base_path)

    @patch("zane_api.services.get_docker_client", return_value=FakeDockerClient())
    def test_create_service_with_explicit_domain(self, mock_fake_docker: Mock):
        owner = self.loginUser()
        p = Project.objects.create(name="KISS CAM", slug="kiss-cam", owner=owner)

        create_service_payload = {
            "name": "Portainer UI",
            "image": "portainer/portainer-ce:latest",
            "urls": [
                {
                    "domain": "dcr.fredkiss.dev",
                    "base_path": "/portainer"
                }
            ],
            "ports": [
                {
                    "forwarded": 8000
                }
            ]
        }

        response = self.client.post(
            reverse('zane_api:services.docker', kwargs={"project_slug": p.slug}),
            data=json.dumps(create_service_payload),
            content_type='application/json'
        )
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        created_service: DockerRegistryService = DockerRegistryService.objects.filter(slug="portainer-ui").first()

        self.assertEqual(1, created_service.urls.count())
        url: URL = created_service.urls.first()
        self.assertIsNotNone(url)
        self.assertEqual("dcr.fredkiss.dev", url.domain)
        self.assertEqual("/portainer", url.base_path)

    @patch("zane_api.services.get_docker_client", return_value=FakeDockerClient())
    def test_create_service_without_port_does_not_create_a_domain(self, mock_fake_docker: Mock):
        owner = self.loginUser()
        p = Project.objects.create(name="KISS CAM", slug="kiss-cam", owner=owner)

        create_service_payload = {
            "name": "Main Database",
            "image": "postgres:12-alpine",
        }

        response = self.client.post(
            reverse('zane_api:services.docker', kwargs={"project_slug": p.slug}),
            data=json.dumps(create_service_payload),
            content_type='application/json'
        )
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        created_service: DockerRegistryService = DockerRegistryService.objects.filter(slug="main-database").first()
        self.assertEqual(0, created_service.urls.count())

    @patch("zane_api.services.get_docker_client", return_value=FakeDockerClient())
    def test_create_service_with_no_http_public_port_does_not_create_a_domain(self, mock_fake_docker: Mock):
        owner = self.loginUser()
        p = Project.objects.create(name="KISS CAM", slug="kiss-cam", owner=owner)

        create_service_payload = {
            "name": "Public Database",
            "image": "postgres:12-alpine",
            "ports": [
                {
                    "public": 5433,
                    "forwarded": 5432
                }
            ]
        }

        response = self.client.post(
            reverse('zane_api:services.docker', kwargs={"project_slug": p.slug}),
            data=json.dumps(create_service_payload),
            content_type='application/json'
        )
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        created_service: DockerRegistryService = DockerRegistryService.objects.filter(slug="public-database").first()
        self.assertEqual(0, created_service.urls.count())

    @patch("zane_api.services.get_docker_client", return_value=FakeDockerClient())
    def test_create_service_create_a_domain_if_public_port_is_80_or_443(self, mock_fake_docker: Mock):
        owner = self.loginUser()
        p = Project.objects.create(name="KISS CAM", slug="kiss-cam", owner=owner)

        create_service_payload = {
            "name": "Adminer UI",
            "image": "adminer:latest",
            "ports": [
                {
                    "public": random.choice([443, 80]),
                    "forwarded": 8080
                }
            ]
        }

        response = self.client.post(
            reverse('zane_api:services.docker', kwargs={"project_slug": p.slug}),
            data=json.dumps(create_service_payload),
            content_type='application/json'
        )
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        created_service: DockerRegistryService = DockerRegistryService.objects.filter(slug="adminer-ui").first()
        self.assertEqual(1, created_service.urls.count())

    @patch("zane_api.services.get_docker_client", return_value=FakeDockerClient())
    def test_create_service_can_only_specify_one_http_port(self, mock_fake_docker: Mock):
        owner = self.loginUser()
        p = Project.objects.create(name="KISS CAM", slug="kiss-cam", owner=owner)

        create_service_payload = {
            "name": "Adminer UI",
            "image": "adminer:latest",
            "ports": [
                {
                    "public": 443,
                    "forwarded": 8080
                },
                {
                    "public": 80,
                    "forwarded": 8080
                },
            ]
        }

        response = self.client.post(
            reverse('zane_api:services.docker', kwargs={"project_slug": p.slug}),
            data=json.dumps(create_service_payload),
            content_type='application/json'
        )
        self.assertEqual(status.HTTP_422_UNPROCESSABLE_ENTITY, response.status_code)

        errors = response.json()['errors']
        self.assertIsNotNone(errors.get('ports'))

    @patch("zane_api.services.get_docker_client", return_value=FakeDockerClient())
    def test_create_service_cannot_specify_the_same_public_port_twice(self, mock_fake_docker: Mock):
        owner = self.loginUser()
        p = Project.objects.create(name="KISS CAM", slug="kiss-cam", owner=owner)

        create_service_payload = {
            "name": "Adminer UI",
            "image": "adminer:latest",
            "ports": [
                {
                    "public": 8080,
                    "forwarded": 8080
                },
                {
                    "public": 8080,
                    "forwarded": 8080
                },
            ]
        }

        response = self.client.post(
            reverse('zane_api:services.docker', kwargs={"project_slug": p.slug}),
            data=json.dumps(create_service_payload),
            content_type='application/json'
        )
        self.assertEqual(status.HTTP_422_UNPROCESSABLE_ENTITY, response.status_code)

        errors = response.json()['errors']
        self.assertIsNotNone(errors.get('ports'))

    @patch("zane_api.services.get_docker_client", return_value=FakeDockerClient())
    def test_create_service_cannot_specify_the_same_url_twice(self, mock_fake_docker: Mock):
        owner = self.loginUser()
        p = Project.objects.create(name="KISS CAM", slug="kiss-cam", owner=owner)

        create_service_payload = {
            "name": "Adminer UI",
            "image": "adminer:latest",
            "urls": [
                {
                    "domain": "dcr.fredkiss.dev",
                    "base_path": "/portainer"
                },
                {
                    "domain": "dcr.fredkiss.dev",
                    "base_path": "/portainer"
                },
            ],
            "ports": [
                {
                    "forwarded": 8080
                },
            ]
        }

        response = self.client.post(
            reverse('zane_api:services.docker', kwargs={"project_slug": p.slug}),
            data=json.dumps(create_service_payload),
            content_type='application/json'
        )
        self.assertEqual(status.HTTP_422_UNPROCESSABLE_ENTITY, response.status_code)

        errors = response.json()['errors']
        self.assertIsNotNone(errors.get('urls'))

    @patch("zane_api.services.get_docker_client", return_value=FakeDockerClient())
    def test_create_service_with_custom_registry(self, mock_fake_docker: Mock):
        owner = self.loginUser()
        p = Project.objects.create(name="Gh clone", slug="gh-clone", owner=owner)

        create_service_payload = {
            "name": "main app",
            "image": "dcr.fredkiss.dev/gh-next:latest",
            "credentials": {
                "username": "fredkiss3",
                "password": "s3cret",
                "registry_url": "https://dcr.fredkiss.dev/"
            },
        }

        response = self.client.post(
            reverse('zane_api:services.docker', kwargs={"project_slug": p.slug}),
            data=json.dumps(create_service_payload),
            content_type='application/json'
        )
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        created_service: DockerRegistryService = DockerRegistryService.objects.filter(slug="main-app").first()
        self.assertIsNotNone(created_service)
        self.assertEqual("fredkiss3", created_service.docker_credentials_username)
        self.assertEqual("s3cret", created_service.docker_credentials_password)

        fake_docker_client: FakeDockerClient = mock_fake_docker.return_value

        self.assertTrue(fake_docker_client.is_logged_in)
        self.assertEqual(1, len(fake_docker_client.downloaded_images))

    @patch("zane_api.services.get_docker_client", return_value=FakeDockerClient())
    def test_create_service_with_custom_registry_does_not_create_service_if_bad_image_credentials(
            self,
            mock_fake_docker: Mock):
        owner = self.loginUser()
        p = Project.objects.create(name="Gh clone", slug="gh-clone", owner=owner)

        create_service_payload = {
            "name": "main app",
            "image": "dcr.fredkiss.dev/gh-next:latest",
            "credentials": {
                "username": "fredkiss3",
                "password": "bad",
                "registry_url": "https://dcr.fredkiss.dev/"
            },
        }

        response = self.client.post(
            reverse('zane_api:services.docker', kwargs={"project_slug": p.slug}),
            data=json.dumps(create_service_payload),
            content_type='application/json'
        )
        self.assertEqual(status.HTTP_422_UNPROCESSABLE_ENTITY, response.status_code)

        errors = response.json()['errors']
        self.assertIsNotNone(errors.get('credentials'))

        created_service: DockerRegistryService = DockerRegistryService.objects.filter(slug="main-app").first()
        self.assertIsNone(created_service)

        fake_docker_client: FakeDockerClient = mock_fake_docker.return_value
        self.assertFalse(fake_docker_client.is_logged_in)
        self.assertEqual(0, len(fake_docker_client.downloaded_images))

    @patch("zane_api.services.get_docker_client", return_value=FakeDockerClient())
    def test_create_service_with_custom_registry_does_not_create_service_if_nonexistent_image(
            self,
            mock_fake_docker: Mock):
        owner = self.loginUser()
        p = Project.objects.create(name="Gh clone", slug="gh-clone", owner=owner)

        create_service_payload = {
            "name": "main app",
            "image": "dcr.fredkiss.dev/nonexistent:latest",
            "credentials": {
                "username": "fredkiss3",
                "password": "s3cret",
                "registry_url": "https://dcr.fredkiss.dev/"
            },
        }

        response = self.client.post(
            reverse('zane_api:services.docker', kwargs={"project_slug": p.slug}),
            data=json.dumps(create_service_payload),
            content_type='application/json'
        )
        self.assertEqual(status.HTTP_422_UNPROCESSABLE_ENTITY, response.status_code)

        errors = response.json()['errors']
        self.assertIsNotNone(errors.get('image'))

        created_service: DockerRegistryService = DockerRegistryService.objects.filter(slug="main-app").first()
        self.assertIsNone(created_service)

        fake_docker_client: FakeDockerClient = mock_fake_docker.return_value
        self.assertTrue(fake_docker_client.is_logged_in)
        self.assertEqual(0, len(fake_docker_client.downloaded_images))

    @patch("zane_api.services.get_docker_client", return_value=FakeDockerClient())
    def test_create_service_credentials_do_not_correspond_to_image(
            self,
            mock_fake_docker: Mock):
        owner = self.loginUser()
        p = Project.objects.create(name="Gh clone", slug="gh-clone", owner=owner)

        create_service_payload = {
            "name": "main app",
            "image": "gcr.io/redis:latest",
            "credentials": {
                "username": "fredkiss3",
                "password": "s3cret",
                "registry_url": "https://dcr.fredkiss.dev/"
            },
        }

        response = self.client.post(
            reverse('zane_api:services.docker', kwargs={"project_slug": p.slug}),
            data=json.dumps(create_service_payload),
            content_type='application/json'
        )
        self.assertEqual(status.HTTP_422_UNPROCESSABLE_ENTITY, response.status_code)

        errors = response.json()['errors']
        self.assertIsNotNone(errors.get('image'))

        created_service: DockerRegistryService = DockerRegistryService.objects.filter(slug="main-app").first()
        self.assertIsNone(created_service)

        fake_docker_client: FakeDockerClient = mock_fake_docker.return_value
        self.assertTrue(fake_docker_client.is_logged_in)
        self.assertEqual(0, len(fake_docker_client.downloaded_images))

    @patch("zane_api.services.get_docker_client", return_value=FakeDockerClient())
    def test_create_service_with_service_if_nonexistent_dockerhub_image(
            self,
            mock_fake_docker: Mock):
        owner = self.loginUser()
        p = Project.objects.create(name="Gh clone", slug="gh-clone", owner=owner)

        create_service_payload = {
            "name": "main app",
            "image": "nonexistent",
        }

        response = self.client.post(
            reverse('zane_api:services.docker', kwargs={"project_slug": p.slug}),
            data=json.dumps(create_service_payload),
            content_type='application/json'
        )
        self.assertEqual(status.HTTP_422_UNPROCESSABLE_ENTITY, response.status_code)

        errors = response.json()['errors']
        self.assertIsNotNone(errors.get('image'))

        created_service: DockerRegistryService = DockerRegistryService.objects.filter(slug="main-app").first()
        self.assertIsNone(created_service)

    @patch("zane_api.services.get_docker_client", return_value=FakeDockerClient())
    def test_create_service_bad_request(self, mock_fake_docker: Mock):
        owner = self.loginUser()
        p = Project.objects.create(name="Gh clone", slug="gh-clone", owner=owner)

        response = self.client.post(
            reverse('zane_api:services.docker', kwargs={"project_slug": p.slug}),
            data=json.dumps({}),
            content_type='application/json'
        )
        self.assertEqual(status.HTTP_422_UNPROCESSABLE_ENTITY, response.status_code)

        errors = response.json().get('errors')
        self.assertIsNotNone(errors)

        created_service: DockerRegistryService = DockerRegistryService.objects.filter(slug="main-app").first()
        self.assertIsNone(created_service)

    @patch("zane_api.services.get_docker_client", return_value=FakeDockerClient())
    def test_create_service_for_nonexistent_project(self, mock_fake_docker: Mock):
        self.loginUser()
        create_service_payload = {
            "name": "cache db",
            "image": "redis:alpine",
        }

        response = self.client.post(
            reverse('zane_api:services.docker', kwargs={"project_slug": "gh-clone"}),
            data=json.dumps(create_service_payload),
            content_type='application/json'
        )
        self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)

        errors = response.json().get('errors')
        self.assertIsNotNone(errors)
        self.assertIsNotNone(errors.get('root'))

        created_service: DockerRegistryService = DockerRegistryService.objects.filter(slug="main-app").first()
        self.assertIsNone(created_service)

    @patch("zane_api.services.get_docker_client", return_value=FakeDockerClient())
    def test_create_service_conflict(self, mock_fake_docker: Mock):
        owner = self.loginUser()
        p = Project.objects.create(name="KISS CAM", slug="kiss-cam", owner=owner)

        DockerRegistryService.objects.create(
            name="cache db2",
            slug="cache-db",
            image="redis:alpine",
            project=p
        )

        create_service_payload = {
            "name": "cache db",
            "image": "redis:alpine",
        }

        response = self.client.post(
            reverse('zane_api:services.docker', kwargs={"project_slug": p.slug}),
            data=create_service_payload
        )
        self.assertEqual(status.HTTP_409_CONFLICT, response.status_code)

        errors = response.json()['errors']
        self.assertIsNotNone(errors.get('root'))