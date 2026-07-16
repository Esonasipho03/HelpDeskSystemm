from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    EMPLOYEE = "EMPLOYEE"
    TECHNICIAN = "TECHNICIAN"
    ADMIN = "ADMIN"

    ROLE_CHOICES = [
        (EMPLOYEE, "Employee"),
        (TECHNICIAN, "Technician"),
        (ADMIN, "Admin"),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=EMPLOYEE
    )

    employee_number = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    def __str__(self):
        return self.username
