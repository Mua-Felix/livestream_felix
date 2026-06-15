from django.contrib import admin
from .models import Plan, Country, PlanPrice, Subscription, Payment


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'price_usd', 'billing_cycle', 'max_participants', 'is_featured', 'is_active')
    list_editable = ('is_active', 'is_featured')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ('flag_emoji', 'name', 'code', 'currency_code', 'currency_symbol', 'usd_exchange_rate')
    search_fields = ('name', 'code', 'currency_code')


@admin.register(PlanPrice)
class PlanPriceAdmin(admin.ModelAdmin):
    list_display = ('plan', 'country', 'currency_code', 'price')
    list_filter = ('plan', 'country')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status', 'started_at', 'expires_at', 'meetings_this_month')
    list_filter = ('status', 'plan')
    search_fields = ('user__username', 'user__email')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'amount', 'currency', 'status', 'created_at', 'flw_tx_ref')
    list_filter = ('status', 'currency')
    search_fields = ('user__username', 'flw_tx_ref', 'flw_tx_id')
    readonly_fields = ('flw_tx_ref', 'flw_tx_id', 'verified_at')
