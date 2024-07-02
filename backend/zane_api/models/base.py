import time
import uuid
from typing import Union

from django.conf import settings
from django.core.validators import MinLengthValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
from faker import Faker
from shortuuid.django_fields import ShortUUIDField

from ..utils import strip_slash_if_exists, datetime_to_timestamp_string
from ..validators import validate_url_domain, validate_url_path, validate_env_name


class TimestampedModel(models.Model):
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class Project(TimestampedModel):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    slug = models.SlugField(max_length=255, unique=True)
    id = ShortUUIDField(
        length=11,
        max_length=255,
        primary_key=True,
        prefix="prj_",
    )
    description = models.TextField(blank=True, null=True)

    @property
    def create_task_id(self):
        return f"create-{self.id}-{datetime_to_timestamp_string(self.created_at)}"

    @property
    def archive_task_id(self):
        return f"archive-{self.id}-{datetime_to_timestamp_string(self.updated_at)}"

    def __str__(self):
        return f"Project({self.slug})"

    class Meta:
        ordering = ["-updated_at"]


class URL(models.Model):
    ID_PREFIX = "url_"
    id = ShortUUIDField(
        length=11,
        max_length=255,
        primary_key=True,
        prefix=ID_PREFIX,
    )
    domain = models.CharField(
        max_length=1000, null=True, blank=True, validators=[validate_url_domain]
    )
    base_path = models.CharField(default="/", validators=[validate_url_path])
    strip_prefix = models.BooleanField(default=True)

    @classmethod
    def create_default_url(cls, service: "BaseService"):
        if isinstance(service, DockerRegistryService):
            suffix = "docker"
        else:
            suffix = "git"

        return URL.objects.create(
            domain=f"{service.project.slug}-{service.slug}-{suffix}.{settings.ROOT_DOMAIN}",
            base_path="/",
        )

    def __str__(self):
        base_path = (
            "/"
            if self.base_path == "/"
            else strip_slash_if_exists(
                self.base_path, strip_start=False, strip_end=True
            )
        )
        return f'URL(domain="{self.domain}"), base_path="{base_path}")'

    class Meta:
        unique_together = (
            "domain",
            "base_path",
        )


class HealthCheck(models.Model):
    ID_PREFIX = "htc_"
    DEFAULT_TIMEOUT_SECONDS = 60
    DEFAULT_INTERVAL_SECONDS = 15
    id = ShortUUIDField(
        length=11,
        max_length=255,
        primary_key=True,
        prefix=ID_PREFIX,
    )

    class HealthCheckType(models.TextChoices):
        COMMAND = "COMMAND", _("Command")
        PATH = "PATH", _("Path")

    type = models.CharField(
        max_length=255,
        null=False,
        choices=HealthCheckType.choices,
        default=HealthCheckType.PATH,
    )
    value = models.CharField(max_length=255, null=False, default="/")
    interval_seconds = models.PositiveIntegerField(default=DEFAULT_INTERVAL_SECONDS)
    timeout_seconds = models.PositiveIntegerField(default=DEFAULT_TIMEOUT_SECONDS)


class BaseService(TimestampedModel):
    slug = models.SlugField(max_length=255)
    project = models.ForeignKey(to=Project, on_delete=models.CASCADE)
    volumes = models.ManyToManyField(to="Volume")
    ports = models.ManyToManyField(to="PortConfiguration")
    urls = models.ManyToManyField(to=URL)
    healthcheck = models.ForeignKey(
        to=HealthCheck, null=True, on_delete=models.SET_NULL
    )
    network_alias = models.CharField(max_length=300, null=True, unique=True)

    @property
    def host_volumes(self):
        return self.volumes.filter(host_path__isnull=False)

    @property
    def docker_volumes(self):
        return self.volumes.filter(host_path__isnull=True)

    class Meta:
        abstract = True
        unique_together = (
            "slug",
            "project",
        )

    def delete_resources(self):
        self.ports.filter().delete()
        self.urls.filter().delete()
        self.volumes.filter().delete()
        if self.healthcheck is not None:
            self.healthcheck.delete()


class PortConfiguration(models.Model):
    ID_PREFIX = "prt_"
    id = ShortUUIDField(
        length=11,
        max_length=255,
        primary_key=True,
        prefix=ID_PREFIX,
    )
    host = models.PositiveIntegerField(null=True, unique=True)
    forwarded = models.PositiveIntegerField()

    def __str__(self):
        host_port = 80 if self.host is None else self.host
        return f"PortConfiguration({host_port} -> {self.forwarded})"

    class Meta:
        indexes = [models.Index(fields=["host"])]


class BaseEnvVariable(models.Model):
    key = models.CharField(max_length=255, validators=[validate_env_name])
    value = models.CharField(max_length=255)

    class Meta:
        abstract = True


class DockerEnvVariable(BaseEnvVariable):
    ID_PREFIX = "env_dkr_"
    id = ShortUUIDField(
        length=11,
        max_length=255,
        primary_key=True,
        prefix=ID_PREFIX,
    )
    service = models.ForeignKey(
        to="DockerRegistryService",
        on_delete=models.CASCADE,
        related_name="env_variables",
    )

    def __str__(self):
        return f"DockerEnvVariable({self.key})"

    class Meta:
        unique_together = ["key", "service"]


class DockerRegistryService(BaseService):
    ID_PREFIX = "srv_dkr_"
    id = ShortUUIDField(
        length=11,
        max_length=255,
        primary_key=True,
        prefix=ID_PREFIX,
    )
    image = models.CharField(max_length=510, null=True)
    command = models.TextField(null=True, blank=True)
    credentials = models.JSONField(
        max_length=255,
        null=True,
    )

    def __str__(self):
        return f"DockerRegistryService({self.slug})"

    @property
    def unprefixed_id(self):
        return self.id.replace(self.ID_PREFIX, "") if self.id is not None else None

    @property
    def network_aliases(self):
        return (
            [
                f"{self.network_alias}.{settings.ZANE_INTERNAL_DOMAIN}",
                self.network_alias,
            ]
            if self.network_alias is not None
            else []
        )

    @property
    def archive_task_id(self):
        return f"archive-{self.id}-{datetime_to_timestamp_string(self.updated_at)}"

    def delete_resources(self):
        super().delete_resources()
        all_deployments = self.deployments.all()
        all_monitor_tasks = PeriodicTask.objects.filter(
            dockerdeployment__in=all_deployments
        )

        interval_ids = []
        for task in all_monitor_tasks.all():
            interval_ids.append(task.interval_id)
        IntervalSchedule.objects.filter(id__in=interval_ids).delete()
        all_monitor_tasks.delete()

    @property
    def latest_production_deployment(self) -> Union["DockerDeployment", None]:
        return (
            self.deployments.filter(is_current_production=True)
            .select_related("service", "service__project")
            .prefetch_related(
                "service__volumes",
                "service__urls",
                "service__ports",
                "service__env_variables",
            )
            .order_by("-created_at")
            .first()
        )

    @property
    def unapplied_changes(self):
        return self.changes.filter(applied=False)

    @property
    def applied_changes(self):
        return self.changes.filter(applied=True)

    @property
    def http_port(self) -> PortConfiguration | None:
        return self.ports.filter(host__isnull=True).first()

    @property
    def last_queued_deployment(self) -> Union["DockerDeployment", None]:
        return (
            self.deployments.filter(
                is_current_production=False,
                status=DockerDeployment.DeploymentStatus.QUEUED,
            )
            .prefetch_related(
                "service__volumes",
                "service__urls",
                "service__ports",
                "service__env_variables",
            )
            .order_by("-created_at")
            .first()
        )

    def apply_pending_changes(self, deployment: "DockerDeployment"):
        added_new_http_port = False
        for change in self.unapplied_changes:
            match change.field:
                case (
                    DockerDeploymentChange.ChangeField.IMAGE
                    | DockerDeploymentChange.ChangeField.COMMAND
                ):
                    setattr(self, change.field, change.new_value)
                case DockerDeploymentChange.ChangeField.CREDENTIALS:
                    if change.new_value is None:
                        self.credentials = None
                        continue
                    self.credentials = {
                        "username": change.new_value.get("username"),
                        "password": change.new_value.get("password"),
                    }
                case DockerDeploymentChange.ChangeField.HEALTHCHECK:
                    if change.new_value is None:
                        if self.healthcheck is not None:
                            self.healthcheck.delete()
                            self.healthcheck = None
                        continue

                    if self.healthcheck is None:
                        self.healthcheck = HealthCheck()

                    self.healthcheck.type = change.new_value.get("type")
                    self.healthcheck.value = change.new_value.get("value")
                    self.healthcheck.timeout_seconds = (
                        change.new_value.get("timeout_seconds")
                        or HealthCheck.DEFAULT_TIMEOUT_SECONDS
                    )
                    self.healthcheck.interval_seconds = (
                        change.new_value.get("interval_seconds")
                        or HealthCheck.DEFAULT_INTERVAL_SECONDS
                    )
                    self.healthcheck.save()
                case DockerDeploymentChange.ChangeField.VOLUMES:
                    if change.type == DockerDeploymentChange.ChangeType.ADD:
                        fake = Faker()
                        Faker.seed(time.monotonic())
                        self.volumes.add(
                            Volume.objects.create(
                                container_path=change.new_value.get("container_path"),
                                host_path=change.new_value.get("host_path"),
                                mode=change.new_value.get("mode"),
                                name=change.new_value.get("name", fake.slug().lower()),
                            )
                        )
                    if change.type == DockerDeploymentChange.ChangeType.DELETE:
                        self.volumes.get(id=change.item_id).delete()
                    if change.type == DockerDeploymentChange.ChangeType.UPDATE:
                        volume = self.volumes.get(id=change.item_id)
                        volume.host_path = change.new_value.get("host_path")
                        volume.container_path = change.new_value.get("container_path")
                        volume.mode = change.new_value.get("mode")
                        volume.name = change.new_value.get("name", volume.name)
                        volume.save()
                case DockerDeploymentChange.ChangeField.ENV_VARIABLES:
                    if change.type == DockerDeploymentChange.ChangeType.ADD:
                        DockerEnvVariable.objects.create(
                            key=change.new_value.get("key"),
                            value=change.new_value.get("value"),
                            service=self,
                        )
                    if change.type == DockerDeploymentChange.ChangeType.DELETE:
                        self.env_variables.get(id=change.item_id).delete()
                    if change.type == DockerDeploymentChange.ChangeType.UPDATE:
                        env = self.env_variables.get(id=change.item_id)
                        env.key = change.new_value.get("key")
                        env.value = change.new_value.get("value")
                        env.save()
                case DockerDeploymentChange.ChangeField.URLS:
                    if change.type == DockerDeploymentChange.ChangeType.ADD:
                        self.urls.add(
                            URL.objects.create(
                                domain=change.new_value.get("domain"),
                                base_path=change.new_value.get("base_path"),
                                strip_prefix=change.new_value.get("strip_prefix"),
                            )
                        )
                    if change.type == DockerDeploymentChange.ChangeType.DELETE:
                        self.urls.get(id=change.item_id).delete()
                    if change.type == DockerDeploymentChange.ChangeType.UPDATE:
                        url = self.urls.get(id=change.item_id)
                        url.domain = change.new_value.get("domain")
                        url.base_path = change.new_value.get("base_path")
                        url.strip_prefix = change.new_value.get("strip_prefix")
                        url.save()
                case DockerDeploymentChange.ChangeField.PORTS:
                    if change.type == DockerDeploymentChange.ChangeType.ADD:
                        is_http_port = change.new_value.get(
                            "host"
                        ) is None or change.new_value.get("host") in [80, 443]
                        self.ports.add(
                            PortConfiguration.objects.create(
                                host=(
                                    None
                                    if is_http_port
                                    else change.new_value.get("host")
                                ),
                                forwarded=change.new_value.get("forwarded"),
                            )
                        )
                        if is_http_port:
                            added_new_http_port = True

                    if change.type == DockerDeploymentChange.ChangeType.DELETE:
                        self.ports.get(id=change.item_id).delete()
                    if change.type == DockerDeploymentChange.ChangeType.UPDATE:
                        is_http_port = change.new_value.get(
                            "host"
                        ) is None or change.new_value.get("host") in [80, 443]

                        port = self.ports.get(id=change.item_id)
                        port.host = (
                            None if is_http_port else change.new_value.get("host")
                        )
                        port.forwarded = change.new_value.get("forwarded")
                        port.save()

                        if is_http_port:
                            added_new_http_port = True

        # Always recreate an URL if there is an http port
        if added_new_http_port and self.urls.count() == 0:
            self.urls.add(URL.create_default_url(service=self))

        self.unapplied_changes.update(applied=True, deployment=deployment)
        self.save()
        self.refresh_from_db()

    def add_change(self, change: "DockerDeploymentChange"):
        change.service = self
        match change.field:
            case "image" | "command" | "credentials" | "healthcheck":
                change_for_field: "DockerDeploymentChange" = (
                    self.unapplied_changes.filter(field=change.field).first()
                )
                if change_for_field is not None:
                    change_for_field.new_value = change.new_value
                else:
                    change_for_field = change
                change_for_field.save()
            case _:
                change.save()

    @property
    def logs(self):
        deployment = self.latest_production_deployment
        if deployment is not None:
            return deployment.logs
        return None


class GitRepositoryService(BaseService):
    ID_PREFIX = "srv_git_"
    id = ShortUUIDField(
        length=11,
        max_length=255,
        primary_key=True,
        prefix=ID_PREFIX,
    )
    previews_enabled = models.BooleanField(default=True)
    auto_deploy = models.BooleanField(default=True)
    preview_protected = models.BooleanField(default=True)
    delete_preview_after_merge = models.BooleanField(default=True)
    production_branch_name = models.CharField(max_length=255)
    repository_url = models.URLField(max_length=1000)
    build_success_webhook_url = models.URLField(null=True, blank=True)

    # for docker build context
    dockerfile_path = models.CharField(max_length=255, default="./Dockerfile")
    docker_build_context_dir = models.CharField(max_length=255, default=".")
    docker_cmd = models.CharField(max_length=255, null=True, blank=True)

    @property
    def unprefixed_id(self):
        return self.id.replace(self.ID_PREFIX, "") if self.id is not None else None


class GitEnvVariable(BaseEnvVariable):
    service = models.ForeignKey(
        to="GitRepositoryService",
        on_delete=models.CASCADE,
        related_name="env_variables",
    )

    def __str__(self):
        return f"GitEnvVariable({self.key})"


class Volume(TimestampedModel):
    ID_PREFIX = "vol_"
    id = ShortUUIDField(length=11, max_length=255, primary_key=True, prefix=ID_PREFIX)

    class VolumeMode(models.TextChoices):
        READ_ONLY = "READ_ONLY", _("Read-Only")
        READ_WRITE = "READ_WRITE", _("Read-Write")

    mode = models.CharField(
        max_length=255,
        null=False,
        choices=VolumeMode.choices,
        default=VolumeMode.READ_WRITE,
    )
    name = models.CharField(
        max_length=255,
        blank=False,
        null=False,
        validators=[MinLengthValidator(limit_value=1)],
    )
    container_path = models.CharField(max_length=255)
    host_path = models.CharField(
        max_length=255, null=True, validators=[validate_url_path], unique=True
    )

    def __str__(self):
        return f"Volume({self.name})"

    class Meta:
        indexes = [
            models.Index(fields=["host_path"]),
            models.Index(fields=["container_path"]),
        ]


class BaseDeployment(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    url = models.URLField(null=True)

    class Meta:
        abstract = True


class DockerDeployment(BaseDeployment):
    HASH_PREFIX = "dpl_dkr_"
    hash = ShortUUIDField(length=11, max_length=255, unique=True, prefix=HASH_PREFIX)

    is_redeploy_of = models.ForeignKey("self", on_delete=models.SET_NULL, null=True)

    class DeploymentStatus(models.TextChoices):
        QUEUED = "QUEUED", _("Queued")
        CANCELLED = "CANCELLED", _("Cancelled")
        FAILED = "FAILED", _("Failed")
        PREPARING = "PREPARING", _("Preparing")
        STARTING = "STARTING", _("Starting")
        RESTARTING = "RESTARTING", _("Restarting")
        HEALTHY = "HEALTHY", _("Healthy")
        UNHEALTHY = "UNHEALTHY", _("Unhealthy")
        REMOVED = "REMOVED", _("Removed")

    class DeploymentSlot(models.TextChoices):
        BLUE = "BLUE", _("Blue")
        GREEN = "GREEN", _("Green")

    slot = models.CharField(
        max_length=10,
        choices=DeploymentSlot.choices,
        default=DeploymentSlot.BLUE,
    )

    status = models.CharField(
        max_length=10,
        choices=DeploymentStatus.choices,
        default=DeploymentStatus.QUEUED,
    )
    status_reason = models.TextField(null=True, blank=True)
    is_current_production = models.BooleanField(default=False)
    service = models.ForeignKey(
        to=DockerRegistryService, on_delete=models.CASCADE, related_name="deployments"
    )
    monitor_task = models.ForeignKey(
        to=PeriodicTask, null=True, on_delete=models.SET_NULL
    )
    service_snapshot = models.JSONField(null=True)

    @property
    def task_id(self):
        return f"deploy-{self.hash}-{self.service.id}-{self.service.project.id}"

    @property
    def monitor_task_name(self):
        return f"monitor_deployment_{self.hash}"

    @property
    def unprefixed_hash(self):
        return None if self.hash is None else self.hash.replace(self.HASH_PREFIX, "")

    @property
    def network_aliases(self):
        aliases = []
        if self.service is not None and len(self.service.network_aliases) > 0:
            aliases = self.service.network_aliases + [
                f"{self.service.network_alias}.{self.slot.lower()}.{settings.ZANE_INTERNAL_DOMAIN}",
            ]
        return aliases

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["url"]),
            models.Index(fields=["is_current_production"]),
        ]

    @property
    def logs(self):
        return SimpleLog.objects.filter(deployment_id=self.hash)

    @property
    def http_logs(self):
        return HttpLog.objects.filter(deployment_id=self.hash)

    def __str__(self):
        return f"DockerDeployment(hash={self.hash}, service={self.service.slug}, project={self.service.project.slug})"


class BaseDeploymentChange(TimestampedModel):
    class ChangeType(models.TextChoices):
        UPDATE = "UPDATE", _("update")
        DELETE = "DELETE", _("delete")
        ADD = "ADD", _("add")

    type = models.CharField(
        max_length=10,
        choices=ChangeType.choices,
    )
    field = models.CharField(max_length=255)
    item_id = models.CharField(max_length=255, null=True)
    old_value = models.JSONField(null=True)
    new_value = models.JSONField(null=True)
    applied = models.BooleanField(default=False)

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["field"]),
            models.Index(fields=["type"]),
            models.Index(fields=["applied"]),
        ]


class DockerDeploymentChange(BaseDeploymentChange):
    ID_PREFIX = "chg_dkr_"
    id = ShortUUIDField(
        length=11,
        max_length=255,
        primary_key=True,
        prefix=ID_PREFIX,
    )

    class ChangeField(models.TextChoices):
        IMAGE = "image", _("image")
        COMMAND = "command", _("command")
        CREDENTIALS = "credentials", _("credentials")
        HEALTHCHECK = "healthcheck", _("healthcheck")
        VOLUMES = "volumes", _("volumes")
        ENV_VARIABLES = "env_variables", _("env_variables")
        URLS = "urls", _("urls")
        PORTS = "ports", _("ports")

    field = models.CharField(max_length=255, choices=ChangeField.choices)

    service = models.ForeignKey(
        to=DockerRegistryService, on_delete=models.CASCADE, related_name="changes"
    )
    deployment = models.ForeignKey(
        to=DockerDeployment, on_delete=models.CASCADE, related_name="changes", null=True
    )

    def __str__(self):
        return (
            f"DockerDeploymentChange("
            f"\n\ttype={self.type},"
            f"\n\tfield={repr(self.field)},"
            f"\n\titem_id={repr(self.item_id)},"
            f"\n\told_value={repr(self.old_value)},"
            f"\n\tnew_value={repr(self.new_value)},"
            f"\n\tapplied={repr(self.applied)}"
            f"\n)"
        )


class GitDeployment(BaseDeployment):
    HASH_PREFIX = "dpl_git_"
    hash = ShortUUIDField(length=11, max_length=255, unique=True, prefix=HASH_PREFIX)

    is_redeploy_of = models.ForeignKey("self", on_delete=models.SET_NULL, null=True)

    class BuildStatus(models.TextChoices):
        ERROR = "ERROR", _("Error")
        SUCCESS = "SUCCESS", _("Success")
        PENDING = "PENDING", _("Pending")
        QUEUED = "QUEUED", _("Queued")

    build_status = models.CharField(
        max_length=10,
        choices=BuildStatus.choices,
        default=BuildStatus.QUEUED,
    )

    class DeploymentStatus(models.TextChoices):
        QUEUED = "QUEUED", _("Queued")
        PREPARING = "PREPARING", _("Preparing")
        FAILED = "FAILED", _("Failed")
        STARTING = "STARTING", _("Starting")
        RESTARTING = "RESTARTING", _("Restarting")
        BUILDING = "BUILDING", _("Building")
        CANCELLED = "CANCELLED", _("Cancelled")
        HEALTHY = "HEALTHY", _("Healthy")
        UNHEALTHY = "UNHEALTHY", _("UnHealthy")
        OFFLINE = "OFFLINE", _("Offline")
        SLEEPING = "SLEEPING", _("Sleeping")  # preview deploys

    status = models.CharField(
        max_length=10,
        choices=DeploymentStatus.choices,
        default=DeploymentStatus.QUEUED,
    )
    status_reason = models.CharField(max_length=255, null=True)

    class DeploymentEnvironment(models.TextChoices):
        PRODUCTION = "PRODUCTION", _("Production")
        PREVIEW = "PREVIEW", _("Preview")

    deployment_environment = models.CharField(
        max_length=10,
        choices=DeploymentEnvironment.choices,
        default=DeploymentEnvironment.PREVIEW,
    )
    is_current_production = models.BooleanField(default=False)

    commit_hash = models.CharField(
        max_length=40
    )  # Typical length of a Git commit hash, but we will use the short version
    commit_message = models.TextField(blank=True)
    build_duration_in_ms = models.PositiveIntegerField(null=True)
    branch = models.CharField(max_length=255)
    service = models.ForeignKey(to=GitRepositoryService, on_delete=models.CASCADE)
    commit_author_username = models.CharField(max_length=255)
    commit_author_avatar_url = models.URLField(null=True)

    def __str__(self):
        return f"GitDeployment(branch={self.branch} - commit_ha={self.commit_hash[:7]} - status={self.build_status})"

    @property
    def unprefixed_hash(self):
        return None if self.hash is None else self.hash.replace(self.HASH_PREFIX, "")

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["is_current_production"]),
        ]


class Log(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    service_id = models.CharField(null=True)
    deployment_id = models.CharField(null=True)
    time = models.DateTimeField()

    class Meta:
        abstract = True


class SimpleLog(Log):
    class LogLevel(models.TextChoices):
        ERROR = "ERROR", _("Error")
        INFO = "INFO", _("Info")

    class LogSource(models.TextChoices):
        SYSTEM = "SYSTEM", _("System Logs")
        PROXY = "PROXY", _("Proxy Logs")
        SERVICE = "SERVICE", _("Service Logs")

    content = models.JSONField(null=True)
    level = models.CharField(
        max_length=10,
        choices=LogLevel.choices,
        default=LogLevel.INFO,
    )
    source = models.CharField(
        max_length=10,
        choices=LogSource.choices,
        default=LogSource.SERVICE,
    )

    class Meta:
        indexes = [
            models.Index(fields=["deployment_id"]),
            models.Index(fields=["service_id"]),
            models.Index(fields=["source"]),
            models.Index(fields=["level"]),
            models.Index(fields=["time"]),
        ]
        ordering = ("time",)


class HttpLog(Log):
    class RequestMethod(models.TextChoices):
        GET = "GET", _("GET")
        POST = "POST", _("POST")
        PUT = "PUT", _("PUT")
        DELETE = "DELETE", _("DELETE")
        PATCH = "PATCH", _("PATCH")
        OPTIONS = "OPTIONS", _("OPTIONS")
        HEAD = "HEAD", _("HEAD")

    request_method = models.CharField(
        max_length=7,
        choices=RequestMethod.choices,
    )
    status = models.PositiveIntegerField()
    request_duration_ms = models.PositiveIntegerField()
    request_headers = models.JSONField()
    response_headers = models.JSONField()
    request_host = models.URLField(max_length=1000)
    request_uri = models.CharField(max_length=2000)
    request_ip = models.GenericIPAddressField()

    class Meta:
        indexes = [
            models.Index(fields=["deployment_id"]),
            models.Index(fields=["service_id"]),
            models.Index(fields=["status"]),
            models.Index(fields=["request_host"]),
            models.Index(fields=["request_uri"]),
            models.Index(fields=["time"]),
        ]
        ordering = ("time",)


class CRON(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=255)
    schedule = models.ForeignKey(to=CrontabSchedule, on_delete=models.RESTRICT)
    archived = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class HttpCRON(CRON):
    class RequestMethod(models.TextChoices):
        GET = "GET", _("GET")
        POST = "POST", _("POST")
        PUT = "PUT", _("PUT")
        DELETE = "DELETE", _("DELETE")
        PATCH = "PATCH", _("PATCH")
        OPTIONS = "OPTIONS", _("OPTIONS")
        HEAD = "HEAD", _("HEAD")

    url = models.URLField(max_length=2000)
    headers = models.JSONField()
    body = models.JSONField()
    method = models.CharField(
        max_length=7,
        choices=RequestMethod.choices,
    )

    def __str__(self):
        return f"HTTP CRON {self.name}"


class ServiceCommandCRON(CRON):
    command = models.TextField()
    dockerService = models.ForeignKey(
        to=DockerRegistryService, null=True, on_delete=models.CASCADE
    )
    gitService = models.ForeignKey(
        to=GitRepositoryService, null=True, on_delete=models.CASCADE
    )

    def __str__(self):
        return f"HTTP CRON {self.name}"
