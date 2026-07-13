import logging
import random
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.http import JsonResponse
from django.views import View
from cart.utils import merge_guest_cart
from .forms import (LoginForm, SignupForm, ForgotPasswordForm, ResetPasswordForm,
                    ProfileForm, AddressForm, first_error)
from .models import CustomUser, OTP, Address
from .tasks import send_otp_sms

logger = logging.getLogger('oramshop')

OTP_MAX_VERIFY_ATTEMPTS = 5
OTP_RATE_LIMIT_ERROR = 'تعداد درخواست‌های کد تأیید بیش از حد مجاز است. لطفاً کمی بعد دوباره تلاش کنید'




# AUTHENTICATION
class LoginView(View):
    template_name = 'accounts/login.html'
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('catalog:index')
        return render(request, self.template_name)

    def post(self, request):
        form = LoginForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'error': first_error(form)})

        user = authenticate(request, username=form.cleaned_data['mobile'],
                            password=form.cleaned_data['password'])

        if user:
            # The session key is captured before login so the guest cart can be merged
            old_session_key = request.session.session_key
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            merge_guest_cart(user, old_session_key)

            # Only internal site URLs are allowed (prevents open redirects)
            next_url = request.GET.get('next')
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
                return redirect(next_url)
            return redirect('catalog:index')
        return render(request, self.template_name, {'error': 'شماره موبایل یا رمز عبور اشتباه است'})


class SignupView(View):
    template_name = 'accounts/signup.html'
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('catalog:index')
        return render(request, self.template_name)

    def post(self, request):
        form = SignupForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'error': first_error(form)})

        mobile = form.cleaned_data['mobile']
        if not _send_otp(mobile):
            return render(request, self.template_name, {'error': OTP_RATE_LIMIT_ERROR})

        # The password is kept hashed in the session, never in plain text
        request.session['signup_data'] = {
            'mobile': mobile,
            'first_name': form.cleaned_data.get('first_name', ''),
            'last_name': form.cleaned_data.get('last_name', ''),
            'password_hash': make_password(form.cleaned_data['password']),
        }

        return redirect('accounts:verify_otp')


class LogoutView(LoginRequiredMixin, View):
    def post(self, request):
        logout(request)
        return redirect('catalog:index')


class ForgotPasswordView(View):
    template_name = 'accounts/forgot-password.html'
    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        form = ForgotPasswordForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'error': first_error(form)})

        mobile = form.cleaned_data['mobile']
        if not CustomUser.objects.filter(mobile=mobile).exists():
            return render(request, self.template_name, {'error': 'کاربری با این شماره موبایل یافت نشد'})

        if not _send_otp(mobile):
            return render(request, self.template_name, {'error': OTP_RATE_LIMIT_ERROR})

        request.session['reset_mobile'] = mobile
        return redirect('accounts:verify_otp')


# OTP
def _send_otp(mobile):
    """
        Create & Send OTP With Celery
        برمی‌گرداند True در صورت ارسال؛ False اگر سقف درخواست پر شده باشد
    """

    # Limit On Otp For 10 Min
    recent_otps = OTP.objects.filter(mobile=mobile, created_at__gte=timezone.now() - timedelta(minutes=10)).count()

    if recent_otps >= 5:
        logger.warning('OTP rate limit hit for mobile %s', mobile)
        return False

    code = str(random.randint(100000, 999999))
    expires_at = timezone.now() + timedelta(minutes=2)

    OTP.objects.create(mobile=mobile,code=code,expires_at=expires_at)

    # Send Async With Celery
    send_otp_sms.delay(mobile, code)

    return True


class SendOTPView(View):
    def post(self, request):
        mobile = request.POST.get('mobile')
        if mobile:
            if not _send_otp(mobile):
                return JsonResponse({'status': 'error', 'message': OTP_RATE_LIMIT_ERROR}, status=429)
            return JsonResponse({'status': 'ok'})
        return JsonResponse({'status': 'error'}, status=400)


class VerifyOTPView(View):
    template_name = 'accounts/verify-otp.html'
    def get(self, request):
        mobile = request.session.get('signup_data', {}).get('mobile') or request.session.get('reset_mobile', '')
        return render(request, self.template_name, {'mobile': mobile})

    def post(self, request):
        mobile = request.POST.get('mobile')
        code = request.POST.get('code')
        next_url = request.POST.get('next', '')

        # Attempt limit to stop code guessing
        attempts_key = f'otp_verify_attempts:{mobile}'
        attempts = cache.get(attempts_key, 0)
        if attempts >= OTP_MAX_VERIFY_ATTEMPTS:
            logger.warning('OTP verify attempts exceeded for mobile %s', mobile)
            return render(request, self.template_name, {'error': 'تعداد تلاش‌های ناموفق بیش از حد مجاز است. لطفاً کد جدید درخواست کنید', 'mobile': mobile})

        otp = OTP.objects.filter(mobile=mobile, code=code, is_used=False).last()

        if not otp or not otp.is_valid():
            cache.set(attempts_key, attempts + 1, timeout=600)
            return render(request, self.template_name, {'error': 'کد وارد شده اشتباه یا منقضی شده است','mobile': mobile})

        cache.delete(attempts_key)
        otp.is_used = True
        otp.save()

        # Register
        signup_data = request.session.get('signup_data')
        if signup_data and signup_data['mobile'] == mobile:
            user = CustomUser(
                mobile=mobile,
                first_name=signup_data.get('first_name', ''),
                last_name=signup_data.get('last_name', ''))
            user.password = signup_data['password_hash']  # already hashed
            user.save()

            del request.session['signup_data']
            old_session_key = request.session.session_key
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            merge_guest_cart(user, old_session_key)

            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            return redirect('catalog:index')

        # Forget Password
        reset_mobile = request.session.get('reset_mobile')
        if reset_mobile == mobile:
            request.session['verified_mobile'] = mobile
            return redirect('accounts:reset_password')
        return redirect('accounts:login')


class ResetPasswordView(View):
    template_name = 'accounts/reset-password.html'
    def get(self, request):
        if not request.session.get('verified_mobile'):
            return redirect('accounts:forgot_password')
        return render(request, self.template_name)

    def post(self, request):
        mobile = request.session.get('verified_mobile')
        if not mobile:
            return redirect('accounts:forgot_password')

        form = ResetPasswordForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'error': first_error(form)})

        user = get_object_or_404(CustomUser, mobile=mobile)
        user.set_password(form.cleaned_data['password'])
        user.save()

        del request.session['verified_mobile']
        return redirect('accounts:login')


# Profile
class ProfileInfoView(LoginRequiredMixin, View):
    template_name = 'accounts/profile-info.html'
    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        form = ProfileForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {'error': first_error(form)})

        user = request.user
        user.first_name = form.cleaned_data['first_name']
        user.last_name = form.cleaned_data['last_name']
        user.email = form.cleaned_data['email']
        user.bio = form.cleaned_data['bio']

        if form.cleaned_data.get('avatar'):
            user.avatar = form.cleaned_data['avatar']

        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        password_changed = False

        if current_password and new_password:
            if user.check_password(current_password):
                user.set_password(new_password)
                password_changed = True
            else:
                return render(request, self.template_name, {'error': 'رمز عبور فعلی اشتباه است'})

        user.save()

        # Keep the user logged in after the password change
        if password_changed:
            update_session_auth_hash(request, user)

        return render(request, self.template_name, {'success': 'اطلاعات با موفقیت ذخیره شد'})


class MyOrdersView(LoginRequiredMixin, View):
    def get(self, request):
        orders = request.user.orders.all().order_by('-created_at')
        return render(request, 'accounts/my-orders.html', {'orders': orders})


# Wishlist
class WishlistView(LoginRequiredMixin, View):
    def get(self, request):
        wishlist = request.session.get('wishlist', [])
        return render(request, 'accounts/wishlist.html', {'wishlist': wishlist})


class WishlistDrawerView(View):
    """Wishlist dropdown HTML for live refresh."""

    def get(self, request):
        return render(request, 'accounts/_wishlist_dropdown.html')


class WishlistToggleView(View):
    """One-click add/remove - filled/empty heart."""

    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'status': 'error', 'message': 'برای ذخیره علاقه‌مندی وارد شوید'}, status=401)

        item_id = str(request.POST.get('id', ''))
        if not item_id:
            return JsonResponse({'status': 'error'}, status=400)

        wishlist = request.session.get('wishlist', [])
        exists = any(str(i.get('id')) == item_id for i in wishlist)

        if exists:
            wishlist = [i for i in wishlist if str(i.get('id')) != item_id]
        else:
            wishlist.append({
                'id': item_id,
                'title': request.POST.get('title', ''),
                'price': request.POST.get('price', ''),
                'image': request.POST.get('image', ''),
                'slug': request.POST.get('slug', '')})

        request.session['wishlist'] = wishlist
        return JsonResponse({'status': 'ok', 'in_wishlist': not exists, 'count': len(wishlist)})


class WishlistAddView(LoginRequiredMixin, View):
    def post(self, request):
        item_id = request.POST.get('id')
        wishlist = request.session.get('wishlist', [])

        if not any(i['id'] == item_id for i in wishlist):
            wishlist.append({
                'id': item_id,
                'title': request.POST.get('title'),
                'price': request.POST.get('price'),
                'image': request.POST.get('image'),
                'size': request.POST.get('size', ''),
                'color': request.POST.get('color', ''),
                'slug': request.POST.get('slug', '')})
            request.session['wishlist'] = wishlist
        return JsonResponse({'status': 'ok','count': len(wishlist)})


class WishlistRemoveView(LoginRequiredMixin, View):
    def post(self, request):
        item_id = request.POST.get('id')
        wishlist = request.session.get('wishlist', [])
        wishlist = [i for i in wishlist if i['id'] != item_id]
        request.session['wishlist'] = wishlist

        return JsonResponse({
            'status': 'ok',
            'count': len(wishlist)
        })


# Addresses
class AddressesView(LoginRequiredMixin, View):
    def get(self, request):
        addresses = request.user.addresses.all()
        return render(request, 'accounts/addresses.html', {'addresses': addresses})


class AddressCreateView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'accounts/address-form.html')

    def post(self, request):
        form = AddressForm(request.POST)
        if not form.is_valid():
            return render(request, 'accounts/address-form.html', {'error': first_error(form)})

        address = form.save(commit=False)
        address.user = request.user
        address.save()
        return redirect('accounts:addresses')


class AddressEditView(LoginRequiredMixin, View):
    def get(self, request, pk):
        address = get_object_or_404(Address, pk=pk, user=request.user)
        return render(request, 'accounts/address-form.html', {'address': address})

    def post(self, request, pk):
        address = get_object_or_404(Address, pk=pk, user=request.user)
        form = AddressForm(request.POST, instance=address)
        if not form.is_valid():
            return render(request, 'accounts/address-form.html', {'address': address, 'error': first_error(form)})

        form.save()
        return redirect('accounts:addresses')


class AddressDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        address = get_object_or_404(Address, pk=pk, user=request.user)
        address.delete()
        return redirect('accounts:addresses')