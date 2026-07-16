from django.conf import settings
from django.db import models
from django.urls import reverse


class TicketStatus(models.TextChoices):
    OPEN = "Open", "Open"
    ASSIGNED = "Assigned", "Assigned"
    IN_PROGRESS = "In Progress", "In Progress"
    PENDING = "Pending", "Pending"
    RESOLVED = "Resolved", "Resolved"
    CLOSED = "Closed", "Closed"


class TicketPriority(models.TextChoices):
    LOW = "Low", "Low"
    MEDIUM = "Medium", "Medium"
    HIGH = "High", "High"
    CRITICAL = "Critical", "Critical"


class TicketCategory(models.TextChoices):
    PRINTING = "Printing", "Printing"
    SCANNING = "Scanning", "Scanning"
    OUTLOOK_PASSWORD = "Outlook Password", "Outlook Password"
    OUTLOOK_ACCOUNT = "Outlook Account", "Outlook Account"
    EMAIL = "Email", "Email"
    NETWORK = "Network", "Network"
    WIFI = "Wi-Fi", "Wi-Fi"
    INTERNET = "Internet", "Internet"
    SOFTWARE = "Software", "Software"
    HARDWARE = "Hardware", "Hardware"
    LAPTOP = "Laptop", "Laptop"
    DESKTOP = "Desktop", "Desktop"
    PHONE = "Phone", "Phone"
    SLACK = "Slack"
    TEAMS = "Microsoft Teams", "Microsoft Teams"
    OFFICE365 = "Office 365", "Office 365"
    OTHER = "Other", "Other"


class Department(models.TextChoices):
    FINANCE = "finance", "Finance"
    MANAGEMENT = "management", "Management"
    MARKETING = "marketing", "Marketing"
    ADMIN ="admin" ,'Admin'
    SALES = "sales", "Sales"
    DEBT = "debt", "Debt Collection"
    HR = "hr", "Human Resources"
    IT = "it", "IT"
    OTHER = "other", "Other"


class Asset(models.Model):

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assets"
    )

    name = models.CharField(max_length=100)

    asset_tag = models.CharField(
        max_length=50,
        unique=True
    )

    serial_number = models.CharField(
        max_length=100,
        blank=True
    )

    icon = models.CharField(
        max_length=30,
        default="laptop"
    )

    assigned_on = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.asset_tag


class Ticket(models.Model):

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tickets_created"
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tickets_assigned"
    )

    title = models.CharField(max_length=200)

    category = models.CharField(
        max_length=50,
        choices=TicketCategory.choices,
        default=TicketCategory.OTHER
    )

    department = models.CharField(
        max_length=40,
        choices=Department.choices,
        default=Department.OTHER
    )

    location = models.CharField(max_length=100)

    computer_name = models.CharField(
        max_length=100,
        blank=True
    )

    asset_number = models.CharField(
        max_length=100,
        blank=True
    )

    description = models.TextField()

    attachment = models.FileField(
        upload_to="tickets/",
        blank=True,
        null=True
    )

    priority = models.CharField(
        max_length=20,
        choices=TicketPriority.choices,
        default=TicketPriority.MEDIUM
    )

    status = models.CharField(
        max_length=20,
        choices=TicketStatus.choices,
        default=TicketStatus.OPEN
    )

    resolution = models.TextField(blank=True)

    satisfaction_rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    resolved_at = models.DateTimeField(
        null=True,
        blank=True
    )

    closed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"#{self.id} - {self.title}"

    def get_absolute_url(self):
        return reverse(
            "ticket_detail",
            kwargs={"pk": self.pk}
        )


class TicketComment(models.Model):

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="comments"
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    comment = models.TextField()

    is_internal = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment #{self.id}"


class Announcement(models.Model):

    title = models.CharField(max_length=200)

    message = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
    
class KnowledgeBaseArticle(models.Model):

    CATEGORY_CHOICES = [

        ("Accounts", "Accounts"),

        ("Printing", "Printing"),

        ("Network", "Network"),

        ("Software", "Software"),

        ("Hardware", "Hardware"),

        ("Email", "Email"),

        ("Phones", "Phones"),

        ("Security", "Security"),

        ("General", "General"),

    ]

    title = models.CharField(
        max_length=200
    )
    is_published = models.BooleanField(default=True)
    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES
    )

    summary = models.CharField(
        max_length=250
    )

    content = models.TextField()

    keywords = models.CharField(
        max_length=300,
        blank=True,
        help_text="Comma-separated keywords"
    )

    is_featured = models.BooleanField(
        default=False
    )

    views = models.PositiveIntegerField(
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title
    
class NotificationAudience(models.TextChoices):
    EMPLOYEE = "employee", "Employee"
    TECHNICIAN = "technician", "Technician"


class Notification(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )

    message = models.CharField(max_length=255)

    audience = models.CharField(
        max_length=20,
        choices=NotificationAudience.choices,
        default=NotificationAudience.EMPLOYEE,
    )

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.message