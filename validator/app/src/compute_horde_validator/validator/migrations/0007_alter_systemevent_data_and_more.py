# Generated by Django 4.2.11 on 2024-05-12 18:52

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("validator", "0006_systemevent"),
    ]

    operations = [
        migrations.AlterField(
            model_name="systemevent",
            name="data",
            field=models.JSONField(blank=True),
        ),
        migrations.AlterField(
            model_name="systemevent",
            name="long_description",
            field=models.TextField(blank=True),
        ),
    ]
