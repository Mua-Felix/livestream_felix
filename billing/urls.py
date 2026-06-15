from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    path('pricing/', views.pricing_page, name='pricing'),
    path('checkout/<slug:plan_slug>/', views.checkout, name='checkout'),
    path('payment/callback/', views.payment_callback, name='callback'),
    path('webhook/flutterwave/', views.flutterwave_webhook, name='flw_webhook'),
    path('subscription/', views.subscription_view, name='subscription'),
    path('subscription/cancel/', views.cancel_subscription, name='cancel'),
    path('api/country-pricing/', views.get_country_pricing, name='country_pricing'),
    path('seed/', views.seed_plans, name='seed'),
]
