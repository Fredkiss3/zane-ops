# Generated by Django 5.0.4 on 2024-05-28 08:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("zane_api", "0115_alter_dockerenvvariable_unique_together"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="portconfiguration",
            index=models.Index(fields=["host"], name="zane_api_po_host_ef8ffd_idx"),
        ),
    ]
