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
    ITTask,
    Ticket,
    TicketComment,
    TicketStatus,
    KnowledgeBaseArticle,
)
from .views import create_notification  # reuse your existing helper

import csv

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, Q
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import path

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


def _technician_report_stats(start_date=None, end_date=None):
    """Per-technician ticket stats, optionally filtered by created_at date range."""

    qs = Ticket.objects.filter(assigned_to__isnull=False)

    if start_date:
        qs = qs.filter(created_at__date__gte=start_date)
    if end_date:
        qs = qs.filter(created_at__date__lte=end_date)

    resolution_time = ExpressionWrapper(
        F("resolved_at") - F("created_at"),
        output_field=DurationField(),
    )

    stats = (
        qs.values("assigned_to__username")
        .annotate(
            total_tickets=Count("id"),
            resolved_tickets=Count(
                "id",
                filter=Q(status__in=[TicketStatus.RESOLVED]),
            ),
            avg_resolution_time=Avg(
                resolution_time,
                filter=Q(resolved_at__isnull=False),
            ),
        )
        .order_by("-total_tickets")
    )

    # Turn the raw timedelta into something readable for the template/CSV.
    rows = []
    for row in stats:
        avg_duration = row["avg_resolution_time"]
        row["avg_resolution_time"] = (
            f"{max(avg_duration.total_seconds(), 0) / 3600:.1f} hrs" if avg_duration else None
        )
        rows.append(row)

    return rows


def technician_report_view(request):
    if not _is_admin(request.user):
        return redirect("admin:index")

    start_date = request.GET.get("start_date") or None
    end_date = request.GET.get("end_date") or None
    stats = _technician_report_stats(start_date, end_date)

    context = {
        **admin.site.each_context(request),
        "title": "Technician Report",
        "stats": stats,
        "start_date": start_date,
        "end_date": end_date,
    }
    return render(request, "admin/tickets/technician_report.html", context)


def technician_report_export_view(request):
    if not _is_admin(request.user):
        return redirect("admin:index")

    start_date = request.GET.get("start_date") or None
    end_date = request.GET.get("end_date") or None
    stats = _technician_report_stats(start_date, end_date)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="technician_report.csv"'

    writer = csv.writer(response)
    writer.writerow(["Technician", "Total Tickets", "Resolved Tickets", "Avg Resolution Time"])
    for row in stats:
        writer.writerow([
            row["assigned_to__username"],
            row["total_tickets"],
            row["resolved_tickets"],
            row["avg_resolution_time"] or "-",
        ])

    return response


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):

    change_list_template = "admin/tickets/ticket/change_list.html"

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

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "technician-report/",
                staff_member_required(technician_report_view),
                name="ticket_technician_report",
            ),
            path(
                "technician-report/export/",
                staff_member_required(technician_report_export_view),
                name="ticket_technician_report_export",
            ),
        ]
        return custom_urls + urls

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


@admin.register(ITTask)
class ITTaskAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "title",
        "assigned_to",
        "priority",
        "status",
        "due_date",
        "assigned_by",
        "created_at",
    )

    list_filter = (
        "status",
        "priority",
        "assigned_to",
    )

    search_fields = (
        "title",
        "description",
        "assigned_to__username",
        "assigned_to__first_name",
        "assigned_to__last_name",
    )

    readonly_fields = (
        "assigned_by",
        "created_at",
        "updated_at",
        "completed_at",
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Only technicians should show up as assignable — admins and
        # employees are never valid targets for an IT task.
        if db_field.name == "assigned_to":
            kwargs["queryset"] = User.objects.filter(role="TECHNICIAN")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        is_new = obj.pk is None
        reassigned = "assigned_to" in form.changed_data

        if is_new:
            obj.assigned_by = request.user

        super().save_model(request, obj, form, change)

        if is_new or reassigned:
            create_notification(
                obj.assigned_to,
                f"You were assigned a new IT task: \"{obj.title}\" by "
                f"{request.user.get_full_name() or request.user.username}.",
                audience="technician",
            )
    
