from django.contrib import admin
from .models import User, OTPVerification


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'mobile_number', 'city', 'is_active', 'created_at']
    search_fields = ['name', 'mobile_number']
    list_filter = ['is_active']


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ['mobile_number', 'otp_code', 'is_verified', 'created_at', 'expires_at']