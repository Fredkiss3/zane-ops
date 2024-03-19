import docker.errors
from django.conf import settings
from django.db import transaction, IntegrityError
from django.utils.text import slugify
from drf_spectacular.utils import extend_schema
from faker import Faker
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .. import serializers
from ..models import Project, DockerRegistryService, DockerDeployment, Volume, EnvVariable, PortConfiguration, URL
from ..services import create_service_from_docker_registry, size_in_bytes, create_docker_volume, \
    login_to_docker_registry, pull_docker_image


class DockerCredentialsSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=100)
    password = serializers.CharField(max_length=100)
    registry_url = serializers.URLField(required=False)


class ServicePortsSerializer(serializers.Serializer):
    public = serializers.IntegerField(required=False, default=80)
    forwarded = serializers.IntegerField()


class VolumeSizeSerializer(serializers.Serializer):
    n = serializers.IntegerField()
    unit = serializers.ChoiceField(choices=['B', 'MB', 'KB', 'GB'], default='B')


class VolumeSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    size = VolumeSizeSerializer(required=False)
    mount_path = serializers.CharField(max_length=255)


class URLSerializer(serializers.Serializer):
    domain = serializers.URLDomainField(required=True)
    base_path = serializers.URLPathField(required=False, default="/")


class DockerServiceCreateRequestSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    image = serializers.CharField(required=True)
    credentials = DockerCredentialsSerializer(required=False)
    urls = URLSerializer(many=True, required=False)
    command = serializers.CharField(required=False)
    ports = ServicePortsSerializer(required=False, many=True)
    env = serializers.DictField(child=serializers.CharField(), required=False)
    volumes = VolumeSerializer(many=True, required=False)

    def validate(self, data: dict):
        credentials = data.get('credentials')
        image = data.get('image')

        try:
            pull_docker_image(image, auth=dict(credentials) if credentials is not None else None)
        except docker.errors.NotFound:
            registry = credentials.get('registry_url') if credentials is not None else None
            if registry is None:
                registry = "Docker Hub's Registry"
            else:
                registry = f"the registry at {registry}"
            raise serializers.ValidationError({
                'image': [f"This image does not exist on {registry}"]
            })
        except docker.errors.APIError:
            raise serializers.ValidationError({
                'image': [f"This image does not correspond to the credentials provided"]
            })

        return data

    def validate_credentials(self, value: dict):
        try:
            login_to_docker_registry(
                username=value['username'],
                password=value['password'],
                registry_url=value.get("registry_url"),
            )
        except docker.errors.APIError:
            raise serializers.ValidationError("Invalid docker credentials")
        else:
            return value

    def validate_ports(self, value: list[dict[str, int]]):
        # Check for only 1 http port
        no_of_http_ports = 0
        http_ports = [80, 443]
        for port in value:
            public_port = port['public']
            if public_port in http_ports:
                no_of_http_ports += 1
            if no_of_http_ports > 1:
                raise serializers.ValidationError("Only one HTTP port is allowed")

        # Check for duplicate public ports
        public_ports_seen = set()
        for port in value:
            public_port = port['public']
            if public_port in public_ports_seen:
                raise serializers.ValidationError("Duplicate public port values are not allowed.")
            public_ports_seen.add(public_port)
        return value

    def validate_urls(self, value: list[dict[str, str]]):
        # Check for duplicate public ports
        urls_seen = set()
        for url in value:
            new_url = (url['domain'], url['base_path'])
            if new_url in urls_seen:
                raise serializers.ValidationError("Duplicate urls values are not allowed.")
            urls_seen.add(new_url)
        return value


class DockerServiceCreateSuccessResponseSerializer(serializers.Serializer):
    service = serializers.DockerServiceSerializer(read_only=True)


class DockerServiceCreateErrorSerializer(serializers.BaseErrorSerializer):
    name = serializers.StringListField(required=False)
    image = serializers.StringListField(required=False)
    credentials = serializers.StringListField(required=False)
    urls = serializers.StringListField(required=False)
    command = serializers.StringListField(required=False)
    ports = serializers.StringListField(required=False)
    env = serializers.StringListField(required=False)
    volumes = serializers.StringListField(required=False)


class DockerServiceCreateErrorResponseSerializer(serializers.Serializer):
    errors = DockerServiceCreateErrorSerializer()


class CreateDockerServiceAPIView(APIView):
    serializer_class = DockerServiceCreateSuccessResponseSerializer
    error_serializer_class = DockerServiceCreateErrorResponseSerializer
    forbidden_serializer_class = serializers.ForbiddenResponseSerializer

    @extend_schema(
        request=DockerServiceCreateRequestSerializer,
        responses={
            422: error_serializer_class,
            404: error_serializer_class,
            409: error_serializer_class,
            201: serializer_class,
            403: forbidden_serializer_class
        },
        operation_id="createDockerService",
    )
    @transaction.atomic()
    def post(self, request: Request, project_slug: str):
        try:
            project = Project.objects.get(slug=project_slug)
        except Project.DoesNotExist:
            response = self.error_serializer_class(
                {
                    "errors": {
                        "root": [f"A project with the slug `{project_slug}` does not exist"],
                    }
                }
            )
            return Response(response.data, status=status.HTTP_404_NOT_FOUND)
        else:
            form = DockerServiceCreateRequestSerializer(data=request.data)
            if form.is_valid():
                data = form.data

                # Create service in DB
                docker_credentials: dict | None = data.get('credentials')
                service_slug = slugify(data["name"])
                try:
                    service = DockerRegistryService.objects.create(
                        name=data['name'],
                        slug=service_slug,
                        project=project,
                        image=data['image'],
                        command=data.get('command'),
                        docker_credentials_username=docker_credentials.get(
                            'username') if docker_credentials is not None else None,
                        docker_credentials_password=docker_credentials.get(
                            'password') if docker_credentials is not None else None,
                    )
                except IntegrityError:
                    response = self.error_serializer_class(
                        {
                            "errors": {
                                "root": [
                                    "A service with a similar slug already exist in this project,"
                                    " please use another name for this service"
                                ]
                            }
                        }
                    )
                    return Response(response.data, status=status.HTTP_409_CONFLICT)

                # Create volumes if exists
                fake = Faker()
                volumes_request = data.get('volumes', [])
                created_volumes = Volume.objects.bulk_create([
                    Volume(
                        name=volume['name'],
                        slug=f"{service.slug}-{fake.slug()}",
                        project=project,
                        size_limit=size_in_bytes(volume["size"]['n'], volume['size']['unit']) if volume.get(
                            "size") is not None else None,
                        containerPath=volume['mount_path'],
                    ) for volume in volumes_request
                ])

                for volume in created_volumes:
                    service.volumes.add(volume)

                # Create envs if exists
                envs_from_request: dict[str, str] = data.get('env', {})

                created_envs = EnvVariable.objects.bulk_create([
                    EnvVariable(
                        key=key,
                        value=value,
                        project=project,
                    ) for key, value in envs_from_request.items()
                ])

                for env in created_envs:
                    service.env_variables.add(env)

                # create ports configuration
                ports_from_request = data.get('ports', [])

                created_ports = PortConfiguration.objects.bulk_create([
                    PortConfiguration(
                        project=project,
                        host=port['public'],
                        forwarded=port['forwarded'],
                    ) for port in ports_from_request
                ])

                for port in created_ports:
                    service.port_config.add(port)

                # Create urls to route the service to
                http_ports = [80, 443]

                can_create_urls = False
                for port in ports_from_request:
                    public_port = port['public']
                    if public_port in http_ports:
                        can_create_urls = True
                        break

                if can_create_urls:
                    service_urls = data.get("urls", [])
                    if len(service_urls) == 0:
                        default_url = URL.objects.create(
                            domain=f"{project.slug}-{service_slug}.{settings.ROOT_DOMAIN}",
                            base_path="/"
                        )
                        service.urls.add(default_url)
                    else:
                        created_urls = URL.objects.bulk_create([
                            URL(domain=url['domain'], base_path=url['base_path']) for url in service_urls
                        ])

                        for url in created_urls:
                            service.urls.add(url)

                # Create first deployment
                DockerDeployment.objects.create(
                    service=service
                )

                # Create resources in docker
                create_service_from_docker_registry(service)
                for volume in created_volumes:
                    create_docker_volume(volume)

                response = self.serializer_class({"service": service})
                return Response(response.data, status=status.HTTP_201_CREATED)

            response = self.error_serializer_class({"errors": form.errors})
            return Response(data=response.data, status=status.HTTP_422_UNPROCESSABLE_ENTITY)