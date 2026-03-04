from django.contrib import admin
from .models import TempleSettings, Booking, Ticket, Payment, WaitingList


@admin.register(TempleSettings)
class TempleSettingsAdmin(admin.ModelAdmin):
    list_display = ['price_per_person', 'booking_cutoff_hour', 'max_capacity_per_day', 'is_booking_open', 'updated_at']


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'booking_date', 'number_of_persons', 'total_amount', 'status', 'created_at']
    list_filter = ['status', 'booking_date']
    search_fields = ['user__name', 'user__mobile_number']
    ordering = ['-created_at']


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['ticket_number', 'booking', 'is_used', 'used_at', 'created_at']
    list_filter = ['is_used']
    search_fields = ['ticket_number']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['booking', 'amount', 'payment_method', 'status', 'paid_at']
    list_filter = ['status']


@admin.register(WaitingList)
class WaitingListAdmin(admin.ModelAdmin):
    list_display = ['user', 'requested_date', 'number_of_persons', 'is_notified', 'created_at']
    list_filter = ['is_notified', 'requested_date']
