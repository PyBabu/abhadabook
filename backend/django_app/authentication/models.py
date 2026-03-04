from django.db import models

class User(models.Model):
    name = models.CharField(max_length=100)
    mobile_number = models.CharField(max_length=15, unique=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.mobile_number}"

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'


class OTPVerification(models.Model):
    mobile_number = models.CharField(max_length=15)
    otp_code = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def __str__(self):
        return f"{self.mobile_number} - {self.otp_code}"

    class Meta:
        db_table = 'otp_verifications'
