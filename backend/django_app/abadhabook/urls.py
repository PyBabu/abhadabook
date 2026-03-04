from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('booking', views.booking, name='booking'),
    path('my-tickets', views.my_tickets, name='my_tickets'),
    path('print-ticket/', views.print_ticket, name='print_ticket'),
    path('scanner/', views.scanner, name='scanner'),
    path('analytics/',    views.analytics,   name='analytics'),
    path('staff-login/', views.staff_login, name='staff_login'),
    path('staff-logout/', views.staff_logout, name='staff_logout'),
]