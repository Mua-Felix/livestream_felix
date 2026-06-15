from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.utils import timezone
from django.contrib import messages
from dateutil.relativedelta import relativedelta
import json
import uuid
import hmac
import hashlib
import requests

from .models import Plan, Country, Subscription, Payment, PlanPrice
from accounts.models import User


# ── Pricing Page ──────────────────────────────────────────
def pricing_page(request):
    plans = Plan.objects.filter(is_active=True).order_by('sort_order')
    countries = Country.objects.filter(flutterwave_supported=True).order_by('name')

    # Detect user's country from subscription or default
    user_country = None
    user_subscription = None

    if request.user.is_authenticated:
        try:
            user_subscription = request.user.subscription
            user_country = user_subscription.country
        except Subscription.DoesNotExist:
            pass

    # Get country from query param or session
    country_code = request.GET.get('country') or request.session.get('country_code', 'US')
    try:
        selected_country = Country.objects.get(code=country_code.upper())
    except Country.DoesNotExist:
        selected_country = Country.objects.filter(code='US').first()

    # Build plan pricing for selected country
    plan_data = []
    for plan in plans:
        try:
            local_price = PlanPrice.objects.get(plan=plan, country=selected_country)
            price_display = f"{selected_country.currency_symbol}{local_price.price:,.0f}"
            price_amount = local_price.price
            currency = selected_country.currency_code
        except PlanPrice.DoesNotExist:
            # Fall back to USD
            price_display = f"${plan.price_usd}"
            price_amount = plan.price_usd
            currency = 'USD'

        plan_data.append({
            'plan': plan,
            'price_display': price_display,
            'price_amount': price_amount,
            'currency': currency,
            'is_current': user_subscription and user_subscription.plan == plan and user_subscription.is_active,
        })

    context = {
        'plan_data': plan_data,
        'countries': countries,
        'selected_country': selected_country,
        'user_subscription': user_subscription,
        'flw_public_key': settings.FLW_PUBLIC_KEY,
        'faq_items': [
            ('Can I cancel my subscription anytime?', 'Yes, you can cancel at any time. You will continue to have access to your plan until the end of your billing period.'),
            ('What payment methods are accepted?', 'We accept debit/credit cards, mobile money (MTN, Airtel, etc.), bank transfer, and USSD — all powered by Flutterwave.'),
            ('Will I be charged in my local currency?', 'Yes! We automatically show prices in your local currency. Payments are processed in your selected currency.'),
            ('What happens when I exceed my plan limits?', 'On the Free plan, new meetings will be blocked once limits are reached. Upgrade anytime to continue hosting meetings.'),
            ('Is there a free trial for paid plans?', 'The Free plan lets you try the platform with no credit card required. Paid plans are billed immediately upon signup.'),
            ('How do I get a receipt for my payment?', 'A receipt is automatically sent to your email after every successful payment. You can also view all payments in your subscription dashboard.'),
        ],
    }
    return render(request, 'billing/pricing.html', context)


# ── Initiate Checkout ─────────────────────────────────────
@login_required
def checkout(request, plan_slug):
    plan = get_object_or_404(Plan, slug=plan_slug, is_active=True)

    if plan.is_free:
        # Assign free plan directly
        _assign_plan(request.user, plan, country=None, free=True)
        messages.success(request, f'You are now on the {plan.name} plan!')
        return redirect('dashboard:home')

    # Get country
    country_code = request.POST.get('country') or request.GET.get('country', 'NG')
    try:
        country = Country.objects.get(code=country_code.upper())
    except Country.DoesNotExist:
        country = Country.objects.filter(code='NG').first()

    # Get local price
    try:
        local_price = PlanPrice.objects.get(plan=plan, country=country)
        amount = local_price.price
        currency = local_price.currency_code
    except PlanPrice.DoesNotExist:
        amount = plan.price_usd
        currency = 'USD'

    # Create payment record
    tx_ref = f"LSF-{uuid.uuid4().hex[:16].upper()}"
    payment = Payment.objects.create(
        user=request.user,
        plan=plan,
        amount=amount,
        currency=currency,
        amount_usd=plan.price_usd,
        flw_tx_ref=tx_ref,
        country=country,
        status='pending',
    )

    # Store session
    request.session['country_code'] = country_code
    request.session['pending_payment_id'] = str(payment.id)

    # Build Flutterwave payment payload
    flw_payload = {
        "tx_ref": tx_ref,
        "amount": str(amount),
        "currency": currency,
        "redirect_url": request.build_absolute_uri('/billing/payment/callback/'),
        "meta": {
            "plan_slug": plan.slug,
            "user_id": str(request.user.id),
            "payment_id": str(payment.id),
        },
        "customer": {
            "email": request.user.email,
            "name": request.user.get_full_name() or request.user.username,
            "phonenumber": getattr(request.user, 'phone', ''),
        },
        "customizations": {
            "title": "LiveStream Felix",
            "description": f"{plan.name} Plan — {plan.billing_cycle}",
            "logo": request.build_absolute_uri('/static/images/logo.png'),
        },
        "payment_options": "card,mobilemoney,ussd,banktransfer",
    }

    # Call Flutterwave API to get payment link
    try:
        response = requests.post(
            'https://api.flutterwave.com/v3/payments',
            json=flw_payload,
            headers={
                'Authorization': f'Bearer {settings.FLW_SECRET_KEY}',
                'Content-Type': 'application/json',
            },
            timeout=15,
        )
        data = response.json()

        if data.get('status') == 'success':
            payment_link = data['data']['link']
            return redirect(payment_link)
        else:
            messages.error(request, f"Payment initialization failed: {data.get('message', 'Unknown error')}")
            return redirect('billing:pricing')

    except requests.RequestException as e:
        messages.error(request, 'Could not connect to payment gateway. Please try again.')
        return redirect('billing:pricing')


# ── Payment Callback (after user pays) ───────────────────
@login_required
def payment_callback(request):
    status = request.GET.get('status')
    tx_ref = request.GET.get('tx_ref')
    transaction_id = request.GET.get('transaction_id')

    if status == 'successful' and tx_ref and transaction_id:
        # Verify with Flutterwave
        verified = _verify_flutterwave_payment(transaction_id)

        if verified and verified.get('status') == 'successful':
            try:
                payment = Payment.objects.get(flw_tx_ref=tx_ref)
                payment.flw_tx_id = transaction_id
                payment.flw_flw_ref = verified.get('flw_ref', '')
                payment.status = 'successful'
                payment.verified_at = timezone.now()
                payment.payment_method = verified.get('payment_type', '')
                payment.save()

                # Activate subscription
                subscription = _assign_plan(
                    payment.user,
                    payment.plan,
                    country=payment.country,
                    payment=payment
                )
                payment.subscription = subscription
                payment.save()

                messages.success(request, f'🎉 Payment successful! You are now on the {payment.plan.name} plan.')
                return redirect('billing:subscription')

            except Payment.DoesNotExist:
                messages.error(request, 'Payment record not found.')
        else:
            messages.error(request, 'Payment verification failed. Contact support.')
    else:
        messages.warning(request, 'Payment was cancelled or failed.')

    return redirect('billing:pricing')


# ── Flutterwave Webhook ───────────────────────────────────
@csrf_exempt
@require_POST
def flutterwave_webhook(request):
    # Verify webhook signature
    secret_hash = settings.FLW_WEBHOOK_SECRET
    signature = request.headers.get('verif-hash', '')

    if signature != secret_hash:
        return HttpResponse(status=401)

    try:
        payload = json.loads(request.body)
        event = payload.get('event')

        if event == 'charge.completed':
            data = payload.get('data', {})
            tx_ref = data.get('tx_ref', '')
            transaction_id = str(data.get('id', ''))
            flw_status = data.get('status', '')

            if flw_status == 'successful' and tx_ref:
                try:
                    payment = Payment.objects.get(flw_tx_ref=tx_ref, status='pending')
                    verified = _verify_flutterwave_payment(transaction_id)

                    if verified and verified.get('status') == 'successful':
                        payment.flw_tx_id = transaction_id
                        payment.status = 'successful'
                        payment.verified_at = timezone.now()
                        payment.save()

                        _assign_plan(payment.user, payment.plan, country=payment.country, payment=payment)

                except Payment.DoesNotExist:
                    pass

    except (json.JSONDecodeError, Exception):
        pass

    return HttpResponse(status=200)


# ── Subscription Dashboard ────────────────────────────────
@login_required
def subscription_view(request):
    try:
        subscription = request.user.subscription
    except Subscription.DoesNotExist:
        subscription = None

    payments = request.user.payments.filter(status='successful').order_by('-created_at')[:10]
    plans = Plan.objects.filter(is_active=True).order_by('sort_order')

    context = {
        'subscription': subscription,
        'payments': payments,
        'plans': plans,
    }
    return render(request, 'billing/subscription.html', context)


# ── Cancel Subscription ───────────────────────────────────
@login_required
@require_POST
def cancel_subscription(request):
    try:
        sub = request.user.subscription
        sub.status = 'cancelled'
        sub.cancelled_at = timezone.now()
        sub.save()
        messages.success(request, 'Subscription cancelled. You can use your plan until it expires.')
    except Subscription.DoesNotExist:
        messages.error(request, 'No active subscription found.')
    return redirect('billing:subscription')


# ── Get pricing for country (AJAX) ───────────────────────
def get_country_pricing(request):
    country_code = request.GET.get('country', 'NG')
    try:
        country = Country.objects.get(code=country_code.upper())
    except Country.DoesNotExist:
        return JsonResponse({'error': 'Country not found'}, status=404)

    plans = Plan.objects.filter(is_active=True).order_by('sort_order')
    data = []
    for plan in plans:
        try:
            local = PlanPrice.objects.get(plan=plan, country=country)
            price = str(local.price)
            currency = local.currency_code
            symbol = country.currency_symbol
        except PlanPrice.DoesNotExist:
            price = str(plan.price_usd)
            currency = 'USD'
            symbol = '$'

        data.append({
            'slug': plan.slug,
            'price': price,
            'currency': currency,
            'symbol': symbol,
            'display': f"{symbol}{float(price):,.0f}",
        })

    return JsonResponse({
        'country': country.name,
        'currency': country.currency_code,
        'symbol': country.currency_symbol,
        'plans': data,
    })


# ── Admin: Seed Plans ─────────────────────────────────────
def seed_plans(request):
    """Run once to create default plans — /billing/seed/ (remove in production)"""
    if not request.user.is_superuser:
        return HttpResponse('Forbidden', status=403)

    plans_data = [
        {
            'name': 'Free', 'slug': 'free', 'price_usd': 0,
            'max_participants': 2, 'max_meeting_minutes': 40,
            'max_meetings_per_month': 3, 'allow_recording': False,
            'allow_polls': False, 'allow_whiteboard': False,
            'allow_analytics': False, 'cloud_storage_gb': 0,
            'sort_order': 1, 'description': 'Perfect for personal use',
        },
        {
            'name': 'Starter', 'slug': 'starter', 'price_usd': 9.99,
            'max_participants': 10, 'max_meeting_minutes': 120,
            'max_meetings_per_month': 20, 'allow_recording': True,
            'allow_polls': True, 'allow_whiteboard': False,
            'allow_analytics': False, 'cloud_storage_gb': 5,
            'sort_order': 2, 'is_featured': False,
            'description': 'Great for small teams',
        },
        {
            'name': 'Pro', 'slug': 'pro', 'price_usd': 19.99,
            'max_participants': 50, 'max_meeting_minutes': 300,
            'max_meetings_per_month': 100, 'allow_recording': True,
            'allow_polls': True, 'allow_whiteboard': True,
            'allow_analytics': True, 'cloud_storage_gb': 20,
            'sort_order': 3, 'is_featured': True,
            'description': 'Best for growing businesses',
        },
        {
            'name': 'Business', 'slug': 'business', 'price_usd': 39.99,
            'max_participants': 100, 'max_meeting_minutes': 9999,
            'max_meetings_per_month': 9999, 'allow_recording': True,
            'allow_polls': True, 'allow_whiteboard': True,
            'allow_analytics': True, 'cloud_storage_gb': 100,
            'allow_custom_branding': True,
            'sort_order': 4, 'description': 'Enterprise-grade for large teams',
        },
    ]

    for p in plans_data:
        Plan.objects.update_or_create(slug=p['slug'], defaults=p)

    # Seed countries with exchange rates
    countries_data = [
        {'name': 'Nigeria', 'code': 'NG', 'currency_code': 'NGN', 'currency_symbol': '₦', 'currency_name': 'Naira', 'usd_exchange_rate': 1580, 'flag_emoji': '🇳🇬'},
        {'name': 'Ghana', 'code': 'GH', 'currency_code': 'GHS', 'currency_symbol': '₵', 'currency_name': 'Cedi', 'usd_exchange_rate': 15.5, 'flag_emoji': '🇬🇭'},
        {'name': 'Kenya', 'code': 'KE', 'currency_code': 'KES', 'currency_symbol': 'KSh', 'currency_name': 'Shilling', 'usd_exchange_rate': 129, 'flag_emoji': '🇰🇪'},
        {'name': 'South Africa', 'code': 'ZA', 'currency_code': 'ZAR', 'currency_symbol': 'R', 'currency_name': 'Rand', 'usd_exchange_rate': 18.5, 'flag_emoji': '🇿🇦'},
        {'name': 'Uganda', 'code': 'UG', 'currency_code': 'UGX', 'currency_symbol': 'USh', 'currency_name': 'Shilling', 'usd_exchange_rate': 3750, 'flag_emoji': '🇺🇬'},
        {'name': 'Tanzania', 'code': 'TZ', 'currency_code': 'TZS', 'currency_symbol': 'TSh', 'currency_name': 'Shilling', 'usd_exchange_rate': 2650, 'flag_emoji': '🇹🇿'},
        {'name': 'Rwanda', 'code': 'RW', 'currency_code': 'RWF', 'currency_symbol': 'Fr', 'currency_name': 'Franc', 'usd_exchange_rate': 1290, 'flag_emoji': '🇷🇼'},
        {'name': 'Zambia', 'code': 'ZM', 'currency_code': 'ZMW', 'currency_symbol': 'ZK', 'currency_name': 'Kwacha', 'usd_exchange_rate': 26, 'flag_emoji': '🇿🇲'},
        {'name': 'United States', 'code': 'US', 'currency_code': 'USD', 'currency_symbol': '$', 'currency_name': 'Dollar', 'usd_exchange_rate': 1, 'flag_emoji': '🇺🇸'},
        {'name': 'United Kingdom', 'code': 'GB', 'currency_code': 'GBP', 'currency_symbol': '£', 'currency_name': 'Pound', 'usd_exchange_rate': 0.79, 'flag_emoji': '🇬🇧'},
        {'name': 'Cameroon', 'code': 'CM', 'currency_code': 'XAF', 'currency_symbol': 'Fr', 'currency_name': 'CFA Franc', 'usd_exchange_rate': 615, 'flag_emoji': '🇨🇲'},
        {'name': 'Ivory Coast', 'code': 'CI', 'currency_code': 'XOF', 'currency_symbol': 'Fr', 'currency_name': 'CFA Franc', 'usd_exchange_rate': 615, 'flag_emoji': '🇨🇮'},
    ]

    for c in countries_data:
        country, _ = Country.objects.update_or_create(code=c['code'], defaults=c)

        # Set local prices for each plan
        for plan in Plan.objects.all():
            local_price = round(float(plan.price_usd) * float(country.usd_exchange_rate), 2)
            # Round nicely
            if local_price > 1000:
                local_price = round(local_price / 100) * 100
            elif local_price > 100:
                local_price = round(local_price / 10) * 10
            elif local_price > 10:
                local_price = round(local_price)

            PlanPrice.objects.update_or_create(
                plan=plan, country=country,
                defaults={'price': local_price, 'currency_code': country.currency_code}
            )

    return HttpResponse('✅ Plans, countries and prices seeded successfully! <a href="/billing/pricing/">View Pricing</a>')


# ── Helpers ───────────────────────────────────────────────
def _verify_flutterwave_payment(transaction_id):
    """Verify a payment with Flutterwave API"""
    try:
        response = requests.get(
            f'https://api.flutterwave.com/v3/transactions/{transaction_id}/verify',
            headers={
                'Authorization': f'Bearer {settings.FLW_SECRET_KEY}',
                'Content-Type': 'application/json',
            },
            timeout=15,
        )
        data = response.json()
        if data.get('status') == 'success':
            return data.get('data', {})
    except Exception:
        pass
    return None


def _assign_plan(user, plan, country=None, free=False, payment=None):
    """Create or update a user's subscription"""
    from dateutil.relativedelta import relativedelta

    now = timezone.now()

    if plan.billing_cycle == 'yearly':
        expires = now + relativedelta(years=1)
    elif free:
        expires = None
    else:
        expires = now + relativedelta(months=1)

    subscription, created = Subscription.objects.update_or_create(
        user=user,
        defaults={
            'plan': plan,
            'status': 'active',
            'expires_at': expires,
            'country': country,
            'meetings_this_month': 0,
            'minutes_this_month': 0,
            'usage_reset_date': now.date(),
        }
    )
    return subscription
