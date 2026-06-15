from django.db import models
from django.conf import settings
import uuid


# ── Subscription Plans ────────────────────────────────────
class Plan(models.Model):
    BILLING_CYCLES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)          # Free, Starter, Pro, Business
    slug = models.SlugField(unique=True)              # free, starter, pro, business
    description = models.TextField(blank=True)
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLES, default='monthly')

    # Pricing in USD (base currency)
    price_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Features
    max_participants = models.PositiveIntegerField(default=2)
    max_meeting_minutes = models.PositiveIntegerField(default=40)  # per meeting
    max_meetings_per_month = models.PositiveIntegerField(default=3)
    allow_recording = models.BooleanField(default=False)
    allow_screen_share = models.BooleanField(default=True)
    allow_polls = models.BooleanField(default=False)
    allow_whiteboard = models.BooleanField(default=False)
    allow_custom_branding = models.BooleanField(default=False)
    allow_analytics = models.BooleanField(default=False)
    cloud_storage_gb = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', 'price_usd']

    def __str__(self):
        return f"{self.name} ({self.billing_cycle})"

    @property
    def is_free(self):
        return self.price_usd == 0


# ── Country & Currency ────────────────────────────────────
class Country(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=3, unique=True)   # NG, GH, KE, ZA, US …
    currency_code = models.CharField(max_length=10)      # NGN, GHS, KES, ZAR, USD
    currency_symbol = models.CharField(max_length=5)     # ₦, ₵, KSh, R, $
    currency_name = models.CharField(max_length=50)      # Naira, Cedi, Shilling…
    flutterwave_supported = models.BooleanField(default=True)
    flag_emoji = models.CharField(max_length=10, blank=True)

    # Exchange rate to USD (updated periodically)
    usd_exchange_rate = models.DecimalField(max_digits=12, decimal_places=4, default=1.0)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Countries'

    def __str__(self):
        return f"{self.flag_emoji} {self.name} ({self.currency_code})"

    def convert_from_usd(self, usd_amount):
        """Convert USD amount to local currency"""
        return round(float(usd_amount) * float(self.usd_exchange_rate), 2)


# ── Plan Pricing per Country ──────────────────────────────
class PlanPrice(models.Model):
    """Local currency pricing for each plan per country"""
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='local_prices')
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='plan_prices')
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency_code = models.CharField(max_length=10)

    class Meta:
        unique_together = ('plan', 'country')

    def __str__(self):
        return f"{self.plan.name} in {self.country.name}: {self.currency_code} {self.price}"


# ── User Subscription ─────────────────────────────────────
class Subscription(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('pending', 'Pending'),
        ('trial', 'Trial'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='subscriptions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True)

    # Billing dates
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    # Flutterwave reference
    flw_subscription_id = models.CharField(max_length=200, blank=True)
    flw_customer_id = models.CharField(max_length=200, blank=True)

    # Usage tracking this month
    meetings_this_month = models.PositiveIntegerField(default=0)
    minutes_this_month = models.PositiveIntegerField(default=0)
    usage_reset_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} — {self.plan.name} ({self.status})"

    @property
    def is_active(self):
        from django.utils import timezone
        if self.status not in ('active', 'trial'):
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return True

    @property
    def can_start_meeting(self):
        if self.plan.is_free:
            return self.meetings_this_month < self.plan.max_meetings_per_month
        return self.is_active

    @property
    def meetings_remaining(self):
        if self.plan.is_free:
            return max(0, self.plan.max_meetings_per_month - self.meetings_this_month)
        return 999  # unlimited for paid


# ── Payment Transaction ───────────────────────────────────
class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payments')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')

    # Amount
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10)
    amount_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Flutterwave data
    flw_tx_ref = models.CharField(max_length=200, unique=True)    # our reference
    flw_tx_id = models.CharField(max_length=200, blank=True)      # flutterwave tx id
    flw_flw_ref = models.CharField(max_length=200, blank=True)    # flutterwave ref
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)  # card, mobilemoney, etc

    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} — {self.currency} {self.amount} ({self.status})"
