from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .forms import RegisterForm, LoginForm, ProfileUpdateForm
from .models import User


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Assign free plan on registration
            try:
                from billing.models import Plan, Subscription, Country
                free_plan = Plan.objects.get(slug='free')
                country_code = form.cleaned_data.get('country_code', 'NG')
                country = Country.objects.filter(code=country_code.upper()).first()
                Subscription.objects.create(
                    user=user,
                    plan=free_plan,
                    status='active',
                    country=country,
                )
                # Store country in session
                request.session['country_code'] = country_code
            except Exception:
                pass
            login(request, user)
            messages.success(request, f'Welcome to LiveStream Felix, {user.first_name}!')
            return redirect('dashboard:home')
    else:
        form = RegisterForm()

    # Load countries for dropdown
    try:
        from billing.models import Country
        countries = Country.objects.filter(flutterwave_supported=True).order_by('name')
    except Exception:
        countries = []

    return render(request, 'accounts/register.html', {'form': form, 'countries': countries})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            user.is_online = True
            user.save(update_fields=['is_online'])
            login(request, user)
            return redirect('dashboard:home')
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})


@login_required
def logout_view(request):
    request.user.is_online = False
    request.user.last_seen = timezone.now()
    request.user.save(update_fields=['is_online', 'last_seen'])
    logout(request)
    return redirect('accounts:login')


@login_required
def profile_view(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('accounts:profile')
    else:
        form = ProfileUpdateForm(instance=request.user)
    return render(request, 'accounts/profile.html', {'form': form})
