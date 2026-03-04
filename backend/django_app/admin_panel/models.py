from django.db import models
from authentication.models import User


class TempleSettings(models.Model):
    price_per_person = models.IntegerField(default=130)
    booking_cutoff_hour = models.IntegerField(default=9)
    max_capacity_per_day = models.IntegerField(default=200)
    is_booking_open = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Temple Settings - Cutoff: {self.booking_cutoff_hour}AM"

    class Meta:
        db_table = 'temple_settings'
        verbose_name = 'Temple Setting'


class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    booking_date = models.DateField()
    number_of_persons = models.IntegerField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    special_occasion = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Booking #{self.id} - {self.user.name} - {self.booking_date}"

    class Meta:
        db_table = 'bookings'
        verbose_name = 'Booking'
        verbose_name_plural = 'Bookings'


class Ticket(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='ticket')
    ticket_number = models.CharField(max_length=20, unique=True)
    qr_code_data = models.TextField()
    qr_code_image = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Ticket {self.ticket_number}"

    class Meta:
        db_table = 'tickets'
        verbose_name = 'Ticket'
        verbose_name_plural = 'Tickets'


class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='payment')
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    paid_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment for Booking #{self.booking.id} - {self.status}"

    class Meta:
        db_table = 'payments'
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'


class WaitingList(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='waiting_list')
    requested_date = models.DateField()
    number_of_persons = models.IntegerField()
    is_notified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Waiting - {self.user.name} - {self.requested_date}"

    class Meta:
        db_table = 'waiting_list'
        verbose_name = 'Waiting List'