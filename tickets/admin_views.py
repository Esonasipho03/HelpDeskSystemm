"""Admin console, IT-task and technician-report views.

Admin  : dashboard, IT task assignment, technician report, all-tickets export.
Technician : the IT tasks an admin has handed to them.
Everyone : the live notification poll used by notifications-live.js.
"""
import csv
from datetime import datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import ITTaskForm
from .models import (
    ITTask,
    Notification,
    Ticket,
    TicketPriority,
    TicketStatus,
)

User = get_user_model()

OPEN_STATUSES = [
    TicketStatus.OPEN,
    TicketStatus.ASSIGNED,
    TicketStatus.IN_PROGRESS,
    TicketStatus.PENDING,
]


# ---------------------------------------------------------------- helpers

def is_admin(user):
    role = str(getattr(user, "role", "")).upper()
    return user.is_authenticated and (role == "ADMIN" or user.is_superuser)


def is_technician(user):
    return user.is_authenticated and str(getattr(user, "role", "")).upper() == "TECHNICIAN"


def _home_for(user):
    """Where a user belongs when they land somewhere they shouldn't."""
    if is_admin(user):
        return "admin_dashboard"
    if is_technician(user):
        return "technician_dashboard"
    return "dashboard"


def admin_required(view):
    """Login required, then admins only; everyone else goes to their own home."""
    @login_required
    def wrapper(request, *args, **kwargs):
        if not is_admin(request.user):
            messages.error(request, "You don't have permission to view that page.")
            return redirect(_home_for(request.user))
        return view(request, *args, **kwargs)
    wrapper.__name__ = view.__name__
    wrapper.__doc__ = view.__doc__
    return wrapper



def staff_required(view):
    """Technicians and admins only (shared work pages). Employees go home."""
    @login_required
    def wrapper(request, *args, **kwargs):
        if not (is_technician(request.user) or is_admin(request.user)):
            messages.error(request, "You don't have permission to view that page.")
            return redirect(_home_for(request.user))
        return view(request, *args, **kwargs)
    wrapper.__name__ = view.__name__
    wrapper.__doc__ = view.__doc__
    return wrapper


def technician_only(admin_redirect="admin_dashboard"):
    """Technician-only pages. Admins are sent to their equivalent admin page
    (so they never land in the technician layout); employees go home."""
    def decorate(view):
        @login_required
        def wrapper(request, *args, **kwargs):
            if is_technician(request.user):
                return view(request, *args, **kwargs)
            if is_admin(request.user):
                target = admin_redirect(request, *args, **kwargs) if callable(admin_redirect) else admin_redirect
                return redirect(target) if isinstance(target, str) else target
            messages.error(request, "You don't have permission to view that page.")
            return redirect(_home_for(request.user))
        wrapper.__name__ = view.__name__
        wrapper.__doc__ = view.__doc__
        return wrapper
    return decorate


def _notify(user, message, audience):
    Notification.objects.create(user=user, message=message, audience=audience)


def _technicians():
    return User.objects.filter(role="TECHNICIAN", is_active=True).order_by("first_name", "username")


def _parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


# -------------------------------------------------------------- dashboard

@admin_required
def admin_dashboard(request):
    tickets = Ticket.objects.all()
    context = {
        "total_tickets": tickets.count(),
        "unassigned_count": tickets.filter(assigned_to__isnull=True, status__in=OPEN_STATUSES).count(),
        "open_count": tickets.filter(status__in=OPEN_STATUSES).count(),
        "resolved_count": tickets.filter(status__in=[TicketStatus.RESOLVED, TicketStatus.CLOSED]).count(),
        "technician_count": _technicians().count(),
        "open_task_count": ITTask.objects.exclude(status="Completed").count(),
        "recent_tasks": ITTask.objects.select_related("assigned_to")[:6],
        "recent_tickets": tickets.select_related("created_by").order_by("-created_at")[:6],
    }
    return render(request, "dashboard/admin_dashboard.html", context)


# ------------------------------------------------------- admin: IT tasks

@admin_required
def admin_task_list(request):
    tasks = ITTask.objects.select_related("assigned_to", "assigned_by")
    status_filter = request.GET.get("status")
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    return render(request, "tickets/admin_task_list.html", {
        "tasks": tasks,
        "status_filter": status_filter,
        "status_choices": ITTask.STATUS_CHOICES,
    })


@admin_required
def admin_task_create(request):
    form = ITTaskForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        task = form.save(commit=False)
        task.assigned_by = request.user
        task.save()
        _notify(
            task.assigned_to,
            f"New IT task assigned to you: {task.title}",
            "technician",
        )
        messages.success(request, "Task assigned.")
        return redirect("admin_task_list")
    return render(request, "tickets/admin_task_form.html", {"form": form, "is_edit": False})


@admin_required
def admin_task_edit(request, pk):
    task = get_object_or_404(ITTask, pk=pk)
    previous_owner = task.assigned_to_id
    form = ITTaskForm(request.POST or None, instance=task)
    if request.method == "POST" and form.is_valid():
        task = form.save()
        if task.assigned_to_id != previous_owner:
            _notify(task.assigned_to, f"IT task assigned to you: {task.title}", "technician")
        messages.success(request, "Task updated.")
        return redirect("admin_task_list")
    return render(request, "tickets/admin_task_form.html", {"form": form, "is_edit": True, "task": task})


# ------------------------------------------------- technician: IT tasks

def _set_task_status(task, status):
    task.status = status
    task.completed_at = timezone.now() if status == "Completed" else None
    task.save()


@technician_only("admin_task_list")
def technician_tasks(request):
    tasks = ITTask.objects.filter(assigned_to=request.user).select_related("assigned_by")
    status_filter = request.GET.get("status")
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    return render(request, "tickets/it_tasks.html", {
        "tasks": tasks,
        "status_filter": status_filter,
        "status_choices": ITTask.STATUS_CHOICES,
    })


@technician_only(lambda request, pk: redirect("admin_task_edit", pk=pk))
def technician_task_detail(request, pk):
    task = get_object_or_404(ITTask, pk=pk, assigned_to=request.user)
    valid = {value for value, _ in ITTask.STATUS_CHOICES}
    if request.method == "POST":
        status = request.POST.get("status")
        if status in valid:
            _set_task_status(task, status)
            messages.success(request, "Task status updated.")
        return redirect("technician_task_detail", pk=task.pk)
    return render(request, "tickets/it_task_detail.html", {
        "task": task,
        "status_choices": ITTask.STATUS_CHOICES,
    })


@technician_only("admin_task_list")
def update_task_status(request, pk):
    task = get_object_or_404(ITTask, pk=pk, assigned_to=request.user)
    if request.method == "POST":
        status = request.POST.get("status")
        if status in {value for value, _ in ITTask.STATUS_CHOICES}:
            _set_task_status(task, status)
    nxt = request.POST.get("next", "")
    # Only follow local paths
    if nxt.startswith("/") and not nxt.startswith("//"):
        return redirect(nxt)
    return redirect("technician_tasks")


# ------------------------------------------------- admin: ticket views

def _filtered_tickets(request):
    """Shared by the all-tickets page and its CSV export."""
    tickets = Ticket.objects.select_related("created_by", "assigned_to").order_by("-created_at")

    search = request.GET.get("search") or request.GET.get("q")
    status = request.GET.get("status")
    priority = request.GET.get("priority")
    technician = request.GET.get("technician")

    if search:
        tickets = tickets.filter(
            Q(title__icontains=search)
            | Q(created_by__username__icontains=search)
            | Q(description__icontains=search)
        )
    if status:
        tickets = tickets.filter(status=status)
    if priority:
        tickets = tickets.filter(priority=priority)
    if technician:
        tickets = tickets.filter(assigned_to_id=technician) if technician.isdigit() else tickets.none()
    return tickets, technician


def admin_all_tickets_context(request):
    tickets, technician = _filtered_tickets(request)
    return {
        "tickets": tickets,
        "status_choices": TicketStatus.choices,
        "priority_choices": TicketPriority.choices,
        "technicians": _technicians(),
        "selected_technician": technician or "",
    }


def admin_unassigned_context(request):
    return {
        "tickets": Ticket.objects.filter(assigned_to__isnull=True, status__in=OPEN_STATUSES)
                         .select_related("created_by").order_by("-created_at"),
        "technicians": _technicians(),
    }


def _csv_response(filename):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("﻿")   # lets Excel read UTF-8 correctly
    return response


def _safe(value):
    """Stop spreadsheet apps from running user text that starts with = + - @ as a formula."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@") else text


@admin_required
def all_tickets_export(request):
    tickets, _ = _filtered_tickets(request)
    response = _csv_response("all_tickets.csv")
    writer = csv.writer(response)
    writer.writerow(["ID", "Title", "Employee", "Category", "Department", "Status", "Priority",
                     "Assigned To", "Created", "Resolved"])
    for t in tickets:
        writer.writerow([
            t.id, _safe(t.title), t.created_by.username if t.created_by else "",
            t.get_category_display(), t.department, t.status, t.priority,
            t.assigned_to.username if t.assigned_to else "Unassigned",
            t.created_at.strftime("%Y-%m-%d %H:%M"),
            t.resolved_at.strftime("%Y-%m-%d %H:%M") if t.resolved_at else "",
        ])
    return response


# -------------------------------------------------- admin: tech report

def _format_duration(delta):
    if not delta:
        return None
    total_minutes = int(delta.total_seconds() // 60)
    days, rem = divmod(total_minutes, 1440)
    hours, minutes = divmod(rem, 60)
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def _report_rows(request):
    start = _parse_date(request.GET.get("start_date"))
    end = _parse_date(request.GET.get("end_date"))

    tickets = Ticket.objects.filter(assigned_to__isnull=False)
    tz = timezone.get_current_timezone()
    if start:
        tickets = tickets.filter(created_at__gte=timezone.make_aware(datetime.combine(start, time.min), tz))
    if end:
        tickets = tickets.filter(created_at__lt=timezone.make_aware(datetime.combine(end + timedelta(days=1), time.min), tz))

    done = [TicketStatus.RESOLVED, TicketStatus.CLOSED]
    resolution = ExpressionWrapper(F("resolved_at") - F("created_at"), output_field=DurationField())

    rows = list(
        tickets.values("assigned_to__username")
        .annotate(
            total_tickets=Count("id"),
            resolved_tickets=Count("id", filter=Q(status__in=done)),
            avg_resolution=Avg(resolution, filter=Q(resolved_at__isnull=False)),
        )
        .order_by("-resolved_tickets", "assigned_to__username")
    )
    for row in rows:
        total = row["total_tickets"]
        row["resolution_rate"] = round(row["resolved_tickets"] * 100 / total) if total else 0
        row["avg_resolution_time"] = _format_duration(row["avg_resolution"])
    return rows, start, end


@admin_required
def technician_report(request):
    rows, start, end = _report_rows(request)
    return render(request, "tickets/technician_report.html", {
        "stats": rows,
        "start_date": start.isoformat() if start else "",
        "end_date": end.isoformat() if end else "",
    })


@admin_required
def technician_report_export(request):
    rows, _, _ = _report_rows(request)
    response = _csv_response("technician_report.csv")
    writer = csv.writer(response)
    writer.writerow(["Technician", "Total Tickets", "Resolved Tickets", "Resolution Rate (%)", "Avg Resolution Time"])
    for r in rows:
        writer.writerow([
            _safe(r["assigned_to__username"]), r["total_tickets"], r["resolved_tickets"],
            r["resolution_rate"], r["avg_resolution_time"] or "",
        ])
    return response


# ---------------------------------------------------- live notifications

@login_required
def notifications_latest(request):
    """JSON feed polled by static/js/notifications-live.js."""
    role = str(getattr(request.user, "role", "")).upper()
    audience = "technician" if role == "TECHNICIAN" else "employee"

    try:
        after = int(request.GET.get("after", 0))
    except (TypeError, ValueError):
        after = 0

    mine = Notification.objects.filter(user=request.user, audience=audience)
    new = mine.filter(id__gt=after, is_read=False).select_related("ticket").order_by("id")[:20]

    detail_route = "ticket_detail" if audience == "employee" and not is_admin(request.user) else "technician_ticket_detail"
    notes = [
        {
            "id": n.id,
            "message": n.message,
            "url": reverse(detail_route, args=[n.ticket_id]) if n.ticket_id else "",
        }
        for n in new
    ]
    return JsonResponse({
        "notifications": notes,
        "unread_count": mine.filter(is_read=False).count(),
    })
