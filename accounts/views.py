from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth import logout as auth_logout

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is not None:
            login(request, user)

            if user.role == "ADMIN":
                return redirect("admin_dashboard")

            elif user.role == "TECHNICIAN":
                return redirect("technician_dashboard")

            elif user.role == "EMPLOYEE":
                return redirect("dashboard")

            return redirect("dashboard")

        else:
            messages.error(request, "Invalid username or password.")

    return render(request, "accounts/login.html")




def logout_view(request):
    auth_logout(request)
    return redirect("login")