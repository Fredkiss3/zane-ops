# Generated by Django 5.0.2 on 2024-03-29 15:37

import django.db.models.deletion
import shortuuid.django_fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("zane_api", "0048_alter_project_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="ArchivedDockerEnvVariables",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("archived_at", models.DateTimeField(auto_now_add=True)),
                ("key", models.CharField(max_length=255)),
                ("value", models.CharField(max_length=255)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="ArchivedPortConfiguration",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("archived_at", models.DateTimeField(auto_now_add=True)),
                ("host", models.PositiveIntegerField(null=True)),
                ("forwarded", models.PositiveIntegerField()),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="ArchivedURL",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("domain", models.CharField(blank=True, max_length=1000, null=True)),
                ("base_path", models.CharField(default="/")),
                ("strip_prefix", models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name="ArchivedVolume",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("archived_at", models.DateTimeField(auto_now_add=True)),
                ("name", models.CharField(max_length=255)),
                ("containerPath", models.CharField(max_length=255)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.AlterUniqueTogether(
            name="volume",
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name="dockerregistryservice",
            name="archived",
        ),
        migrations.RemoveField(
            model_name="dockerregistryservice",
            name="name",
        ),
        migrations.RemoveField(
            model_name="envvariable",
            name="project",
        ),
        migrations.RemoveField(
            model_name="gitrepositoryservice",
            name="archived",
        ),
        migrations.RemoveField(
            model_name="gitrepositoryservice",
            name="name",
        ),
        migrations.AlterField(
            model_name="dockerregistryservice",
            name="id",
            field=shortuuid.django_fields.ShortUUIDField(
                alphabet=None,
                length=11,
                max_length=11,
                prefix="",
                primary_key=True,
                serialize=False,
            ),
        ),
        migrations.AlterField(
            model_name="gitrepositoryservice",
            name="id",
            field=shortuuid.django_fields.ShortUUIDField(
                alphabet=None,
                length=11,
                max_length=11,
                prefix="",
                primary_key=True,
                serialize=False,
            ),
        ),
        migrations.AlterField(
            model_name="volume",
            name="id",
            field=shortuuid.django_fields.ShortUUIDField(
                alphabet=None,
                length=11,
                max_length=11,
                prefix="",
                primary_key=True,
                serialize=False,
            ),
        ),
        migrations.CreateModel(
            name="ArchivedDockerService",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("archived_at", models.DateTimeField(auto_now_add=True)),
                ("slug", models.SlugField(max_length=255)),
                ("image", models.CharField(max_length=510)),
                ("command", models.TextField(blank=True, null=True)),
                (
                    "docker_credentials_username",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "docker_credentials_password",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "env_variables",
                    models.ManyToManyField(to="zane_api.archiveddockerenvvariables"),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="zane_api.archivedproject",
                    ),
                ),
                (
                    "ports",
                    models.ManyToManyField(to="zane_api.archivedportconfiguration"),
                ),
                ("urls", models.ManyToManyField(to="zane_api.archivedurl")),
                ("volumes", models.ManyToManyField(to="zane_api.archivedvolume")),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.RemoveField(
            model_name="volume",
            name="project",
        ),
        migrations.RemoveField(
            model_name="volume",
            name="slug",
        ),
    ]
