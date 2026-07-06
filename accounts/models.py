from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Plan(models.TextChoices):
        STARTER = "starter", "Starter"
        PRO = "pro", "Pro"
        TEAM = "team", "Team"

    plan = models.CharField(max_length=20, choices=Plan.choices, default=Plan.STARTER)
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.username
