# Generated by Django 5.0.4 on 2024-05-26 23:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("django_celery_beat", "0018_improve_crontab_helptext"),
        ("zane_api", "0103_archivedproject_description"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="dockerdeployment",
            index=models.Index(fields=["status"], name="zane_api_do_status_00a3ce_idx"),
        ),
        migrations.AddIndex(
            model_name="gitdeployment",
            index=models.Index(fields=["status"], name="zane_api_gi_status_7b6698_idx"),
        ),
    ]
