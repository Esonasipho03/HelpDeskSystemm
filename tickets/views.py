import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, Q
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.urls import reverse

from .models import (
    Announcement,
    Asset,
    ITTask,
    ITTaskStatus,
    KnowledgeBaseArticle,
    Notification,
    Ticket,
    TicketStatus,
    TicketPriority,
    Department,
)
from .forms import (
    SatisfactionRatingForm,
    TicketCommentForm,
    TicketCreateForm,
    KnowledgeBaseArticleForm,
    ITTaskForm,
)

User = get_user_model()

AUTO_ASSIGN = {
    Department.SALES: "Phila",
    Department.DEBT: "bafana",
}


def create_notification(user, message, ticket=None, audience="employee"):
    Notification.objects.create(
        user=user,
        message=message,
        ticket=ticket,
        audience=audience,
    )


def _audience_for(user):
    """Which notification bucket a logged-in user should see, based on role."""
    role = str(getattr(user, "role", "")).upper()
    return "technician" if role == "TECHNICIAN" else "employee"


@login_required
def create_ticket(request):
    initial = {}

    category = request.GET.get("category")
    if category:
        initial["category"] = category

    if request.method == "POST":
        form = TicketCreateForm(request.POST, request.FILES)

        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.created_by = request.user

            # Automatic assignment
            username = AUTO_ASSIGN.get(ticket.department)
            if username:
                try:
                    ticket.assigned_to = User.objects.get(username=username)
                except User.DoesNotExist:
                    ticket.assigned_to = None

            ticket.save()

            if ticket.assigned_to:
                create_notification(
                    request.user,
                    f"Ticket #{ticket.id} was assigned to {ticket.assigned_to.get_full_name()}.",
                    ticket=ticket,
                    audience="employee",
                )

                create_notification(
                    ticket.assigned_to,
                    f"You were assigned Ticket #{ticket.id}.",
                    ticket=ticket,
                    audience="technician",
                )

            else:
                create_notification(
                    request.user,
                    f"Ticket #{ticket.id} created and is waiting to be claimed.",
                    ticket=ticket,
                    audience="employee",
                )

            return redirect("ticket_detail", pk=ticket.pk)

    else:
        form = TicketCreateForm(initial=initial)

    return render(
        request,
        "tickets/create_ticket.html",
        {
            "form": form,
            "base_template": "base_admin_dashboard.html" if _is_admin(request.user) else "base_dashboard.html",
        },
    )


@login_required
def mark_notifications_read(request):
    if request.method == "POST":
        audience = _audience_for(request.user)
        Notification.objects.filter(
            user=request.user,
            audience=audience,
            is_read=False,
        ).update(is_read=True)
    return JsonResponse({"status": "ok"})


@login_required
def notifications_latest(request):
    """Polled by the browser to detect brand-new notifications so we can
    pop a desktop notification + play a sound without a full page reload."""
    audience = _audience_for(request.user)

    try:
        after_id = int(request.GET.get("after", 0))
    except (TypeError, ValueError):
        after_id = 0

    qs = (
        Notification.objects.filter(
            user=request.user,
            audience=audience,
            id__gt=after_id,
        )
        .order_by("id")[:20]
    )

    def note_url(note):
        if not note.ticket_id:
            return ""
        if audience == "technician":
            return reverse("technician_ticket_detail", args=[note.ticket_id])
        return reverse("ticket_detail", args=[note.ticket_id])

    data = [
        {
            "id": note.id,
            "message": note.message,
            "url": note_url(note),
            "created_at": note.created_at.isoformat(),
        }
        for note in qs
    ]

    unread_count = Notification.objects.filter(
        user=request.user,
        audience=audience,
        is_read=False,
    ).count()

    return JsonResponse({"notifications": data, "unread_count": unread_count})


@login_required
def ticket_history(request):

    tickets = Ticket.objects.filter(
        created_by=request.user
    )

    status = request.GET.get("status")

    if status:
        tickets = tickets.filter(
            status=status
        )

    return render(
        request,
        "tickets/ticket_history.html",
        {
            "tickets": tickets,
            "status_choices": TicketStatus.choices,
            "status_filter": status,
            "base_template": "base_admin_dashboard.html" if _is_admin(request.user) else "base_dashboard.html",
        },
    )


@login_required
def ticket_detail(request, pk):

    ticket = get_object_or_404(
        Ticket,
        pk=pk,
        created_by=request.user,
    )

    if request.method == "POST":

        comment_form = TicketCommentForm(
            request.POST
        )

        if comment_form.is_valid():

            comment = comment_form.save(
                commit=False
            )

            comment.ticket = ticket
            comment.author = request.user

            comment.save()

            messages.success(
                request,
                "Comment added successfully."
            )

            create_notification(
                request.user,
                f"Your comment on Ticket #{ticket.id} was added successfully.",
                ticket=ticket,
                audience="employee",
            )

            if ticket.assigned_to:
                create_notification(
                    ticket.assigned_to,
                    f"{request.user.get_full_name() or request.user.username} replied on Ticket #{ticket.id}.",
                    ticket=ticket,
                    audience="technician",
                )

            return redirect(
                "ticket_detail",
                pk=ticket.pk,
            )

    else:

        comment_form = TicketCommentForm()

    comments = ticket.comments.filter(
        is_internal=False
    )

    return render(
        request,
        "tickets/ticket_detail.html",
        {
            "ticket": ticket,
            "comments": comments,
            "comment_form": comment_form,
            "base_template": "base_admin_dashboard.html" if _is_admin(request.user) else "base_dashboard.html",
        },
    )


@login_required
def rate_ticket(request, pk):

    ticket = get_object_or_404(
        Ticket,
        pk=pk,
        created_by=request.user,
    )

    if ticket.status != TicketStatus.RESOLVED:
        messages.error(
            request,
            "Only resolved tickets can be rated."
        )
        return redirect(
            "ticket_detail",
            pk=ticket.pk,
        )

    if request.method == "POST":

        form = SatisfactionRatingForm(
            request.POST,
            instance=ticket,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Thank you for your feedback."
            )

            create_notification(
                request.user,
                f"Thanks for rating Ticket #{ticket.id}.",
                ticket=ticket,
                audience="employee",
            )

            if ticket.assigned_to:
                create_notification(
                    ticket.assigned_to,
                    f"Ticket #{ticket.id} was rated {ticket.satisfaction_rating}/5.",
                    ticket=ticket,
                    audience="technician",
                )

            return redirect(
                "ticket_detail",
                pk=ticket.pk,
            )

    else:

        form = SatisfactionRatingForm(
            instance=ticket
        )

    return render(
        request,
        "tickets/rate_ticket.html",
        {
            "ticket": ticket,
            "form": form,
        },
    )


@login_required
def knowledge_base(request):

    query = request.GET.get("q", "")

    category = request.GET.get("category", "")

    articles = KnowledgeBaseArticle.objects.all()

    if query:
        articles = articles.filter(
            Q(title__icontains=query) |
            Q(summary__icontains=query) |
            Q(content__icontains=query) |
            Q(keywords__icontains=query)
        )

    if category:
        articles = articles.filter(category=category)

    featured = KnowledgeBaseArticle.objects.filter(
        is_featured=True
    )[:6]

    categories = KnowledgeBaseArticle.objects.values_list(
        "category",
        flat=True
    ).distinct()

    latest_articles = KnowledgeBaseArticle.objects.order_by(
        "-created_at"
    )[:5]

    popular_articles = KnowledgeBaseArticle.objects.order_by(
        "-views"
    )[:5]

    return render(
        request,
        "tickets/knowledge_base.html",
        {
            "articles": articles,
            "featured": featured,
            "categories": categories,
            "latest_articles": latest_articles,
            "popular_articles": popular_articles,
            "query": query,
            "selected_category": category,
        },
    )


@login_required
def article_detail(request, pk):

    article = get_object_or_404(
        KnowledgeBaseArticle,
        pk=pk
    )

    article.views += 1
    article.save(update_fields=["views"])

    return render(
        request,
        "tickets/article_detail.html",
        {
            "article": article,
        }
    )


@login_required
def all_tickets(request):
    tickets = Ticket.objects.all().order_by("-created_at")

    q = request.GET.get("search") or request.GET.get("q")
    status = request.GET.get("status")
    priority = request.GET.get("priority")
    technician = request.GET.get("technician")

    if q:
        tickets = tickets.filter(
            title__icontains=q
        )

    if status:
        tickets = tickets.filter(status=status)

    if priority:
        tickets = tickets.filter(priority=priority)

    if technician:
        tickets = tickets.filter(assigned_to_id=technician)

    context = {
        "tickets": tickets,
        "status_choices": TicketStatus.choices,
        "priority_choices": TicketPriority.choices,
        "technicians": User.objects.filter(role="TECHNICIAN").order_by("username"),
        "selected_technician": technician,
    }

    if _is_admin(request.user):
        return render(request, "tickets/admin_all_tickets.html", context)

    return render(request, "tickets/all_tickets.html", context)


def _csv_datetime(value):
    """Format an aware datetime for CSV export as plain readable text.

    Leading apostrophe tells Excel to treat the cell as literal text
    instead of auto-detecting it as a date/number - Excel strips the
    apostrophe on display, so this avoids the "column too narrow" #####
    that shows up when Excel reformats an auto-detected date into a
    wider representation than the column currently allows.
    """
    if not value:
        return ""
    return "'" + timezone.localtime(value).strftime("%Y-%m-%d %H:%M")


@login_required
def all_tickets_export(request):
    """CSV export of the All Tickets list, admin-only, respecting whatever
    search/status/priority/technician filters are currently applied."""
    if not _is_admin(request.user):
        return redirect("all_tickets")

    tickets = Ticket.objects.all().order_by("-created_at")

    q = request.GET.get("search") or request.GET.get("q")
    status = request.GET.get("status")
    priority = request.GET.get("priority")
    technician_id = request.GET.get("technician")

    if q:
        tickets = tickets.filter(title__icontains=q)

    if status:
        tickets = tickets.filter(status=status)

    if priority:
        tickets = tickets.filter(priority=priority)

    technician_user = None
    if technician_id:
        tickets = tickets.filter(assigned_to_id=technician_id)
        technician_user = User.objects.filter(pk=technician_id).first()

    filename = "all_tickets_report.csv"
    if technician_user:
        # e.g. "tickets_report_jsmith.csv"
        safe_username = "".join(
            c if c.isalnum() else "_" for c in technician_user.username
        )
        filename = f"tickets_report_{safe_username}.csv"

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        "ID",
        "Employee",
        "Issue",
        "Description",
        "Category",
        "Department",
        "Status",
        "Priority",
        "Assigned To",
        "Resolution",
        "Satisfaction Rating",
        "Created At",
        "Updated At",
        "Resolved At",
    ])
    for ticket in tickets.select_related("created_by", "assigned_to"):
        writer.writerow([
            ticket.id,
            ticket.created_by.username if ticket.created_by else "",
            ticket.title,
            ticket.description,
            ticket.get_category_display(),
            ticket.get_department_display(),
            ticket.get_status_display(),
            ticket.get_priority_display(),
            ticket.assigned_to.username if ticket.assigned_to else "Unassigned",
            ticket.resolution,
            ticket.satisfaction_rating if ticket.satisfaction_rating is not None else "",
            # created_at/updated_at/resolved_at are stored in UTC (USE_TZ=True) -
            # _csv_datetime() converts to settings.TIME_ZONE
            # (Africa/Johannesburg) before formatting, so the CSV matches
            # what's shown on-screen, and forces Excel to treat it as text
            # so it doesn't collapse into ##### in a narrow column.
            _csv_datetime(ticket.created_at),
            _csv_datetime(ticket.updated_at),
            _csv_datetime(ticket.resolved_at),
        ])

    return response


def _technician_report_stats(start_date=None, end_date=None):
    """Per-technician ticket stats, optionally filtered by created_at date
    range. Used to measure each technician's workload and how efficiently
    they're resolving tickets."""

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

    rows = []
    for row in stats:
        avg_duration = row["avg_resolution_time"]
        row["avg_resolution_time"] = (
            f"{max(avg_duration.total_seconds(), 0) / 3600:.1f} hrs" if avg_duration else None
        )
        row["resolution_rate"] = (
            round(row["resolved_tickets"] / row["total_tickets"] * 100)
            if row["total_tickets"] else 0
        )
        rows.append(row)

    return rows


@login_required
def technician_report(request):
    """Admin-only page (on the custom dashboard, not Django admin) showing
    each technician's ticket volume, resolution count, and average
    resolution time so admins can gauge efficiency at a glance."""
    if not _is_admin(request.user):
        return redirect("all_tickets")

    start_date = request.GET.get("start_date") or None
    end_date = request.GET.get("end_date") or None
    stats = _technician_report_stats(start_date, end_date)

    context = {
        "stats": stats,
        "start_date": start_date,
        "end_date": end_date,
    }
    return render(request, "tickets/technician_report.html", context)


@login_required
def technician_report_export(request):
    if not _is_admin(request.user):
        return redirect("all_tickets")

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


@login_required
def my_queue(request):

    tickets = Ticket.objects.filter(
        assigned_to=request.user
    )

    status = request.GET.get("status")
    search = request.GET.get("q")

    if status:
        tickets = tickets.filter(status=status)

    if search:
        tickets = tickets.filter(title__icontains=search)

    context = {
        "tickets": tickets,
        "status_filter": status,
        "status_choices": TicketStatus.choices,
    }

    return render(
        request,
        "tickets/my_queue.html",
        context,
    )


@login_required
def unassigned_queue(request):

    tickets = Ticket.objects.filter(
        assigned_to__isnull=True
    )

    if _is_admin(request.user):
        technicians = User.objects.filter(role="TECHNICIAN")

        return render(
            request,
            "tickets/admin_unassigned_queue.html",
            {
                "tickets": tickets,
                "technicians": technicians,
            }
        )

    return render(
        request,
        "tickets/unassigned_queue.html",
        {
            "tickets": tickets,
        }
    )


@login_required
def ticket_search(request):
    query = request.GET.get("q", "")

    tickets = Ticket.objects.filter(
        title__icontains=query
    ).order_by("-created_at")

    return render(request, "tickets/technician/search_results.html", {
        "tickets": tickets,
        "query": query,
    })


@login_required
def technician_profile(request):

    context = {

        "assigned":
        Ticket.objects.filter(
            assigned_to=request.user
        ).count(),

        "resolved":
        Ticket.objects.filter(
            assigned_to=request.user,
            status=TicketStatus.RESOLVED
        ).count(),

        "closed":
        Ticket.objects.filter(
            assigned_to=request.user,
            status=TicketStatus.RESOLVED
        ).count(),

    }

    return render(
        request,
        "tickets/profile.html",
        context,
    )


@login_required
def technician_tasks(request):
    """IT tasks the admin has assigned directly to this technician —
    separate from tickets, since employees never raised them."""

    tasks = ITTask.objects.filter(assigned_to=request.user)

    status_filter = request.GET.get("status")
    if status_filter:
        tasks = tasks.filter(status=status_filter)

    return render(request, "tickets/it_tasks.html", {
        "tasks": tasks,
        "status_filter": status_filter,
        "status_choices": ITTaskStatus.choices,
    })


@login_required
def technician_task_detail(request, pk):
    """Full details of a single IT task, viewable/updatable only by the
    technician it was assigned to."""
    task = get_object_or_404(ITTask, pk=pk, assigned_to=request.user)

    if request.method == "POST":
        new_status = request.POST.get("status")
        valid_statuses = {choice.value for choice in ITTaskStatus}
        if new_status in valid_statuses:
            task.status = new_status
            if new_status == ITTaskStatus.COMPLETED:
                task.completed_at = timezone.now()
            else:
                task.completed_at = None
            task.save()
            messages.success(request, f"Task marked as {task.get_status_display()}.")
            return redirect("technician_task_detail", pk=task.pk)

    return render(request, "tickets/it_task_detail.html", {
        "task": task,
        "status_choices": ITTaskStatus.choices,
    })


@login_required
def update_task_status(request, pk):
    """Technician updates the status of an IT task assigned to them."""
    if request.method == "POST":
        task = get_object_or_404(ITTask, pk=pk, assigned_to=request.user)
        new_status = request.POST.get("status")
        valid_statuses = {choice.value for choice in ITTaskStatus}
        if new_status in valid_statuses:
            task.status = new_status
            if new_status == ITTaskStatus.COMPLETED:
                task.completed_at = timezone.now()
            else:
                task.completed_at = None
            task.save()
            messages.success(request, f"Task \"{task.title}\" marked as {task.get_status_display()}.")

    next_url = request.POST.get("next") or "technician_tasks"
    return redirect(next_url)


@login_required
def claim_ticket(request, pk):

    ticket = get_object_or_404(
        Ticket,
        pk=pk,
    )

    if ticket.assigned_to is None:

        ticket.assigned_to = request.user
        ticket.status = TicketStatus.IN_PROGRESS
        ticket.save()

        messages.success(
            request,
            "Ticket claimed successfully."
        )

        create_notification(
            request.user,
            f"You claimed Ticket #{ticket.id}.",
            ticket=ticket,
            audience="technician",
        )

        create_notification(
            ticket.created_by,
            f"Ticket #{ticket.id} was claimed by {request.user.get_full_name() or request.user.username}.",
            ticket=ticket,
            audience="employee",
        )

    else:

        messages.warning(
            request,
            "Ticket has already been assigned."
        )

    return redirect(
        "technician_ticket_detail",
        pk=ticket.pk,
    )


@login_required
def update_ticket_status(request, pk):

    ticket = get_object_or_404(
        Ticket,
        pk=pk
    )

    if request.method == "POST":

        new_status = request.POST.get("status")
        resolution = request.POST.get("resolution")

        if new_status == TicketStatus.RESOLVED and resolution:
            ticket.resolution = resolution

        # resolved_at is now handled in Ticket.save() based on the status
        # transition, so it's set consistently regardless of which page
        # or action changed the status.
        ticket.status = new_status
        ticket.save()

        messages.success(
            request,
            "Ticket updated."
        )

        # Let the technician who made the change see it in their own bell
        create_notification(
            request.user,
            f"You updated Ticket #{ticket.id} to {new_status}.",
            ticket=ticket,
            audience="technician",
        )

        # Notify the employee who filed it, worded to match the actual new status
        if new_status == TicketStatus.RESOLVED:
            create_notification(
                ticket.created_by,
                f"Ticket #{ticket.id} was resolved. Let us know how we did!",
                ticket=ticket,
                audience="employee",
            )
        else:
            create_notification(
                ticket.created_by,
                f"Ticket #{ticket.id} status changed to {new_status}.",
                ticket=ticket,
                audience="employee",
            )

    next_url = request.POST.get("next")
    if next_url:
        return redirect(next_url)

    return redirect(
        "technician_ticket_detail",
        pk=ticket.pk
    )


@login_required
def technician_ticket_detail(request, pk):

    ticket = get_object_or_404(
        Ticket,
        pk=pk,
    )

    if request.method == "POST":

        comment_form = TicketCommentForm(request.POST)

        if comment_form.is_valid():

            comment = comment_form.save(commit=False)

            comment.ticket = ticket
            comment.author = request.user

            # Internal note if hidden field exists
            comment.is_internal = "internal_note" in request.POST

            comment.save()

            if not comment.is_internal:
                create_notification(
                    ticket.created_by,
                    f"{request.user.get_full_name() or request.user.username} replied on Ticket #{ticket.id}.",
                    ticket=ticket,
                    audience="employee",
                )

            return redirect(
                "technician_ticket_detail",
                pk=ticket.pk,
            )

    else:

        comment_form = TicketCommentForm()

    # Comments visible to employees
    public_comments = ticket.comments.filter(
        is_internal=False
    )

    # Technician-only notes
    internal_comments = ticket.comments.filter(
        is_internal=True
    )

    return render(
        request,
        "tickets/technician_ticket_detail.html",
        {
            "ticket": ticket,
            "comments": public_comments,
            "internal_comments": internal_comments,
            "comment_form": comment_form,
            "base_template": "base_admin_dashboard.html" if _is_admin(request.user) else "base_technician_dashboard .html",
            "back_url_name": "all_tickets" if _is_admin(request.user) else "my_queue",
        },
    )


@login_required
def manage_articles(request):

    articles = KnowledgeBaseArticle.objects.all()

    search = request.GET.get("q")

    if search:
        articles = articles.filter(
            title__icontains=search
        )

    return render(
        request,
        "tickets/manage_articles.html",
        {
            "articles": articles,
        }
    )


@login_required
def create_article(request):

    if request.method == "POST":

        form = KnowledgeBaseArticleForm(
            request.POST
        )

        if form.is_valid():

            article = form.save(commit=False)
            article.author = request.user
            article.save()

            messages.success(
                request,
                "Knowledge Base article created."
            )

            return redirect(
                "manage_articles"
            )

    else:

        form = KnowledgeBaseArticleForm()

    return render(
        request,
        "tickets/article_form.html",
        {
            "form": form,
            "title": "Create Article",
        }
    )


@login_required
def delete_article(request, pk):

    article = get_object_or_404(
        KnowledgeBaseArticle,
        pk=pk,
    )

    article.delete()

    messages.success(
        request,
        "Article deleted."
    )

    return redirect(
        "manage_articles"
    )


@login_required
def edit_article(request, pk):
    article = get_object_or_404(
        KnowledgeBaseArticle,
        pk=pk
    )

    if request.method == "POST":
        form = KnowledgeBaseArticleForm(
            request.POST,
            instance=article
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Article updated successfully."
            )

            return redirect(
                "knowledge_base"
            )

    else:
        form = KnowledgeBaseArticleForm(
            instance=article
        )

    return render(
        request,
        "tickets/edit_article.html",
        {
            "form": form,
            "article": article,
        },
    )


@login_required
def preview_article(request, pk):
    article = get_object_or_404(
        KnowledgeBaseArticle,
        pk=pk
    )

    return render(
        request,
        "tickets/preview_article.html",
        {
            "article": article,
        },
    )
def _is_admin(user):
    role = str(getattr(user, "role", "")).upper()
    return role == "ADMIN" or user.is_superuser

@login_required
def admin_assign_ticket(request, pk):

    if not _is_admin(request.user):
        messages.error(
            request,
            "You don't have permission to do that."
        )
        return redirect("unassigned_queue")

    ticket = get_object_or_404(
        Ticket,
        pk=pk,
    )

    if request.method == "POST":

        technician_username = request.POST.get("technician")

        if ticket.assigned_to is not None:
            messages.warning(
                request,
                "Ticket has already been assigned."
            )
            return redirect("unassigned_queue")

        technician = get_object_or_404(
            User,
            username=technician_username,
        )

        ticket.assigned_to = technician
        ticket.status = TicketStatus.ASSIGNED
        ticket.save()

        messages.success(
            request,
            f"Ticket #{ticket.id} assigned to {technician.get_full_name() or technician.username}."
        )

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

    return redirect("unassigned_queue")


@login_required
def admin_task_list(request):
    """Real-site page (not /admin/) where an admin can see and manage
    every IT task handed out to technicians."""

    if not _is_admin(request.user):
        messages.error(request, "You don't have permission to view this page.")
        return redirect("dashboard")

    tasks = ITTask.objects.select_related("assigned_to", "assigned_by").all()

    status_filter = request.GET.get("status")
    if status_filter:
        tasks = tasks.filter(status=status_filter)

    technician_filter = request.GET.get("technician")
    if technician_filter:
        tasks = tasks.filter(assigned_to__username=technician_filter)

    return render(request, "tickets/admin_task_list.html", {
        "tasks": tasks,
        "status_filter": status_filter,
        "technician_filter": technician_filter,
        "status_choices": ITTaskStatus.choices,
        "technicians": User.objects.filter(role="TECHNICIAN"),
    })


@login_required
def admin_task_create(request):
    """Real-site page where an admin assigns a new IT task to a technician."""

    if not _is_admin(request.user):
        messages.error(request, "You don't have permission to do that.")
        return redirect("dashboard")

    if request.method == "POST":
        form = ITTaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.assigned_by = request.user
            task.save()

            create_notification(
                task.assigned_to,
                f"You were assigned a new IT task: \"{task.title}\" by "
                f"{request.user.get_full_name() or request.user.username}.",
                audience="technician",
            )

            messages.success(request, f"Task \"{task.title}\" assigned to "
                              f"{task.assigned_to.get_full_name() or task.assigned_to.username}.")
            return redirect("admin_task_list")
    else:
        form = ITTaskForm()

    return render(request, "tickets/admin_task_form.html", {
        "form": form,
        "is_edit": False,
    })


@login_required
def admin_task_edit(request, pk):
    """Real-site page where an admin edits or reassigns an existing IT task."""

    if not _is_admin(request.user):
        messages.error(request, "You don't have permission to do that.")
        return redirect("dashboard")

    task = get_object_or_404(ITTask, pk=pk)
    previous_assignee = task.assigned_to

    if request.method == "POST":
        form = ITTaskForm(request.POST, instance=task)
        if form.is_valid():
            task = form.save()

            if task.assigned_to != previous_assignee:
                create_notification(
                    task.assigned_to,
                    f"You were assigned IT task: \"{task.title}\" by "
                    f"{request.user.get_full_name() or request.user.username}.",
                    audience="technician",
                )

            messages.success(request, f"Task \"{task.title}\" updated.")
            return redirect("admin_task_list")
    else:
        form = ITTaskForm(instance=task)

    return render(request, "tickets/admin_task_form.html", {
        "form": form,
        "task": task,
        "is_edit": True,
    })

from django.http import JsonResponse

@login_required
def ticket_search_api(request):
    query = request.GET.get("q", "").strip()

    if not query:
        return JsonResponse({"results": []})

    filters = (
        Q(title__icontains=query)
        | Q(created_by__first_name__icontains=query)
        | Q(created_by__last_name__icontains=query)
        | Q(created_by__username__icontains=query)
    )

    if query.isdigit():
        filters |= Q(pk=int(query))

    tickets = Ticket.objects.filter(filters).order_by("-created_at")[:8]

    results = [
        {
            "id": ticket.pk,
            "title": ticket.title,
            "requester": ticket.created_by.get_full_name() or ticket.created_by.username,
            "status": ticket.get_status_display(),
            "priority": ticket.priority,
            "url": reverse("technician_ticket_detail", kwargs={"pk": ticket.pk}),
        }
        for ticket in tickets
    ]

    return JsonResponse({"results": results})