# Generated by Django 5.0.4 on 2024-06-30 02:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("zane_api", "0130_alter_simplelog_content"),
    ]

    operations = [
        migrations.AddField(
            model_name="simplelog",
            name="time",
            field=models.DateTimeField(),
            preserve_default=False,
        ),
    ]
