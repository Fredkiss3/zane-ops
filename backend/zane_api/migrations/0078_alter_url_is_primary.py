# Generated by Django 5.0.2 on 2024-05-01 18:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("zane_api", "0077_url_is_primary"),
    ]

    operations = [
        migrations.AlterField(
            model_name="url",
            name="is_primary",
            field=models.BooleanField(default=True),
        ),
    ]