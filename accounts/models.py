from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Plan(models.TextChoices):
        STARTER = "starter", "Starter"
        PRO = "pro", "Pro"
        TEAM = "team", "Team"

    plan = models.CharField(max_length=20, choices=Plan.choices, default=Plan.STARTER)
    # LemonSqueezy, no Stripe -- Colombia no esta soportada para cuenta vendedora en Stripe.
    lemonsqueezy_customer_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.username
