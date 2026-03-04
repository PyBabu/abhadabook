from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings


def home(request):
    return render(request, 'home.html')


def booking(request):
    return render(request, 'booking.html')


def my_tickets(request):
    return render(request, 'my_tickets.html')


def print_ticket(request):
    return render(request, 'print_ticket.html')


def staff_login(request):
    if request.method == "POST":
        password = request.POST.get("password")
        if password == "Temple@123":
            request.session['is_staff_logged'] = True
            return redirect('scanner')
        else:
            messages.error(request, "Invalid password")
    return render(request, 'staff_login.html')


def scanner(request):
    if not request.session.get('is_staff_logged'):
        return redirect('staff_login')
    return render(request, 'scanner.html')


def analytics(request):
    if not request.session.get('is_staff_logged'):
        return redirect('staff_login')
    return render(request, 'analytics.html')


def staff_logout(request):
    request.session.flush()
    return redirect('home')