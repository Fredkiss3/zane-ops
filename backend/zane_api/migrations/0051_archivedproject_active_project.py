# Generated by Django 5.0.2 on 2024-03-29 17:03

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("zane_api", "0050_remove_dockerdeployment_env_variables_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="archivedproject",
            name="active_project",
            field=models.OneToOneField(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="zane_api.project",
            ),
        ),
    ]
