# Generated by Django 5.0.4 on 2024-05-04 16:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("zane_api", "0082_alter_dockerdeployment_deployment_status_reason"),
    ]

    operations = [
        migrations.AlterField(
            model_name="gitdeployment",
            name="deployment_status",
            field=models.CharField(
                choices=[
                    ("QUEUED", "Queued"),
                    ("PREPARING", "Preparing"),
                    ("FAILED", "Failed"),
                    ("STARTING", "Starting"),
                    ("RESTARTING", "Restarting"),
                    ("BUILDING", "Building"),
                    ("CANCELLED", "Cancelled"),
                    ("HEALTHY", "Healthy"),
                    ("UNHEALTHY", "UnHealthy"),
                    ("OFFLINE", "Offline"),
                    ("SLEEPING", "Sleeping"),
                ],
                default="QUEUED",
                max_length=10,
            ),
        ),
    ]
