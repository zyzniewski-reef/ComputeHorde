# Generated by Django 4.2.16 on 2024-10-10 05:45

from django.db import migrations, models

import compute_horde.executor_class


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="JobFinishedReceipt",
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
                ("job_uuid", models.UUIDField()),
                ("validator_hotkey", models.CharField(max_length=256)),
                ("miner_hotkey", models.CharField(max_length=256)),
                ("validator_signature", models.CharField(max_length=256)),
                (
                    "miner_signature",
                    models.CharField(blank=True, max_length=256, null=True),
                ),
                ("time_started", models.DateTimeField()),
                ("time_took_us", models.BigIntegerField()),
                ("score_str", models.CharField(max_length=256)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="JobStartedReceipt",
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
                ("job_uuid", models.UUIDField()),
                ("validator_hotkey", models.CharField(max_length=256)),
                ("miner_hotkey", models.CharField(max_length=256)),
                ("validator_signature", models.CharField(max_length=256)),
                (
                    "miner_signature",
                    models.CharField(blank=True, max_length=256, null=True),
                ),
                (
                    "executor_class",
                    models.CharField(
                        default=compute_horde.executor_class.ExecutorClass[
                            "spin_up_4min__gpu_24gb"
                        ],
                        max_length=255,
                    ),
                ),
                ("time_accepted", models.DateTimeField()),
                ("max_timeout", models.IntegerField()),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.AddConstraint(
            model_name="jobstartedreceipt",
            constraint=models.UniqueConstraint(
                fields=("job_uuid",), name="unique_jobstartedreceipt_job_uuid"
            ),
        ),
        migrations.AddConstraint(
            model_name="jobfinishedreceipt",
            constraint=models.UniqueConstraint(
                fields=("job_uuid",), name="unique_jobfinishedreceipt_job_uuid"
            ),
        ),
    ]
