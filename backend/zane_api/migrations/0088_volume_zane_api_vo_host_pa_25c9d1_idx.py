# Generated by Django 5.0.4 on 2024-05-06 18:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("zane_api", "0087_rename_containerpath_volume_container_path_and_more"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="volume",
            index=models.Index(
                fields=["host_path"], name="zane_api_vo_host_pa_25c9d1_idx"
            ),
        ),
    ]
