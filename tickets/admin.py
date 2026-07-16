from django.contrib import admin

from .models import (
    Announcement,
    Asset,
    Ticket,
    TicketComment,
    KnowledgeBaseArticle,
)

from django.contrib import admin
from django.contrib.auth import get_user_model

from .models import (
    Announcement,
    Asset,
    Ticket,
    TicketComment,
    TicketStatus,
    KnowledgeBaseArticle,
)
from .views import create_notification  # reuse your existing helper

User = get_user_model()


class TicketCommentInline(admin.TabularInline):
    model = TicketComment
    extra = 0
    readonly_fields = (
        "author",
        "created_at",
    )


def _is_admin(user):
    role = str(getattr(user, "role", "")).upper()
    return role == "ADMIN" or user.is_superuser


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "title",
        "category",
        "priority",
        "status",
        "created_by",
        "assigned_to",
        "created_at",
    )

    list_filter = (
        "status",
        "priority",
        "category",
        "department",
    )

    search_fields = (
        "title",
        "description",
        "created_by__username",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    inlines = [
        TicketCommentInline
    ]

    actions = [
        "assign_to_phila",
        "assign_to_bafana",
    ]

    def _bulk_assign(self, request, queryset, username):

        if not _is_admin(request.user):
            self.message_user(
                request,
                "You don't have permission to assign tickets.",
                level="error",
            )
            return

        try:
            technician = User.objects.get(username=username)
        except User.DoesNotExist:
            self.message_user(
                request,
                f"No user found with username '{username}'.",
                level="error",
            )
            return

        unclaimed = queryset.filter(assigned_to__isnull=True)
        skipped = queryset.exclude(assigned_to__isnull=True).count()

        for ticket in unclaimed:
            ticket.assigned_to = technician
            ticket.status = TicketStatus.ASSIGNED
            ticket.save()

            create_notification(
                technician,
                f"You were assigned Ticket #{ticket.id} by {request.user.get_full_name() or request.user.username}.",
                ticket=ticket,
                audience="technician",
            )

            create_notification(
                ticket.created_by,
                f"Ticket #{ticket.id} was assigned to {technician.get_full_name() or technician.username}.",
                ticket=ticket,
                audience="employee",
            )

        self.message_user(
            request,
            f"Assigned {unclaimed.count()} ticket(s) to {username}. "
            f"Skipped {skipped} already-assigned ticket(s)."
        )

    def assign_to_phila(self, request, queryset):
        self._bulk_assign(request, queryset, "Phila")
    assign_to_phila.short_description = "Assign selected unclaimed tickets to Phila"

    def assign_to_bafana(self, request, queryset):
        self._bulk_assign(request, queryset, "bafana")
    assign_to_bafana.short_description = "Assign selected unclaimed tickets to Bafana"


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):

    list_display = (
        "asset_tag",
        "name",
        "owner",
        "assigned_on",
    )

    search_fields = (
        "asset_tag",
        "name",
    )


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
    )


@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):

    list_display = (
        "ticket",
        "author",
        "is_internal",
        "created_at",
    )

    list_filter = (
        "is_internal",
    )
    
@admin.register(KnowledgeBaseArticle)
class KnowledgeBaseArticleAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "category",
        "is_featured",
        "views",
    )

    list_filter = (
        "category",
        "is_featured",
    )

    search_fields = (
        "title",
        "summary",
        "keywords",
    )
    
