from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, render


def home_view(request):
    # PURPOSE:
    # Show a clean public landing page with login form.
    # Users are created by admin and log in from here.
    if request.user.is_authenticated:
        return redirect("dashboard_home")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, "Welcome back.")
            return redirect("dashboard_home")
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, "home.html")


@login_required
def dashboard_home(request):
    # PURPOSE:
    # Bridge page between login and operational modules.
    # For now only Daily Report is active; other modules are placeholders.
    return render(request, "dashboard/home.html")