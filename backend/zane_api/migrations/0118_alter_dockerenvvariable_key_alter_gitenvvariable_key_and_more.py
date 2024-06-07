# Generated by Django 5.0.4 on 2024-05-31 22:34

import django.core.validators
import zane_api.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("zane_api", "0117_alter_volume_host_path"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dockerenvvariable",
            name="key",
            field=models.CharField(
                max_length=255, validators=[zane_api.validators.validate_env_name]
            ),
        ),
        migrations.AlterField(
            model_name="gitenvvariable",
            name="key",
            field=models.CharField(
                max_length=255, validators=[zane_api.validators.validate_env_name]
            ),
        ),
        migrations.AlterField(
            model_name="volume",
            name="name",
            field=models.CharField(
                max_length=255,
                validators=[django.core.validators.MinLengthValidator(limit_value=1)],
            ),
        ),
    ]