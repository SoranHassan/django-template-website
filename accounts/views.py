import random
from datetime import timedelta
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.http import JsonResponse
from django.views import View
from .models import CustomUser, OTP, Address
from .tasks import send_otp_sms




# AUTHENTICATION
class LoginView(View):
    template_name = 'accounts/login.html'
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('catalog:index')
        return render(request, self.template_name)

    def post(self, request):
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        user = authenticate(request, username=mobile, password=password)

        if user:
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            next_url = request.GET.get('next', 'catalog:index')
            return redirect(next_url)
        return render(request, self.template_name, {'error': 'شماره موبایل یا رمز عبور اشتباه است'})


class SignupView(View):
    template_name = 'accounts/signup.html'
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('catalog:index')
        return render(request, self.template_name)

    def post(self, request):
        mobile = request.POST.get('mobile')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')


        if password != confirm_password:
            return render(request, self.template_name, {'error': 'رمز عبور و تکرار آن یکسان نیستند'})

        if CustomUser.objects.filter(mobile=mobile).exists():
            return render(request, self.template_name, {'error': 'این شماره موبایل قبلاً ثبت شده است'})

        request.session['signup_data'] = {
            'mobile': mobile,
            'first_name': first_name,
            'last_name': last_name,
            'password': password,
        }

        _send_otp(mobile)
        
        return redirect('accounts:verify_otp')


class LogoutView(LoginRequiredMixin, View):
    def get(self, request):
        logout(request)
        return redirect('catalog:index')


class ForgotPasswordView(View):
    template_name = 'accounts/forgot-password.html'
    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        mobile = request.POST.get('mobile')

        if not CustomUser.objects.filter(mobile=mobile).exists():
            return render(request, self.template_name, {'error': 'کاربری با این شماره موبایل یافت نشد'})

        request.session['reset_mobile'] = mobile
        _send_otp(mobile)
        return redirect('accounts:verify_otp')


# OTP
def _send_otp(mobile):
    """
        Create & Send OTP With Celery
    """

    # Limit On Otp For 5 Min
    recent_otps = OTP.objects.filter(mobile=mobile, created_at__gte=timezone.now() - timedelta(minutes=10)).count()

    if recent_otps >= 5:
        raise Exception('تعداد درخواست‌های OTP بیش از حد مجاز است')

    code = str(random.randint(100000, 999999))
    expires_at = timezone.now() + timedelta(minutes=2)

    OTP.objects.create(mobile=mobile,code=code,expires_at=expires_at)

    # Send Async With Celery
    send_otp_sms.delay(mobile, code)

    return code


class SendOTPView(View):
    def post(self, request):
        mobile = request.POST.get('mobile')
        if mobile:
            _send_otp(mobile)
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
        otp = OTP.objects.filter(mobile=mobile, code=code, is_used=False).last()

        if not otp or not otp.is_valid():
            return render(request, self.template_name, {'error': 'کد وارد شده اشتباه یا منقضی شده است','mobile': mobile})

        otp.is_used = True
        otp.save()

        # Register
        signup_data = request.session.get('signup_data')
        if signup_data and signup_data['mobile'] == mobile:
            user = CustomUser.objects.create_user(
                mobile=mobile,
                password=signup_data['password'],
                first_name=signup_data.get('first_name', ''),
                last_name=signup_data.get('last_name', ''))
            del request.session['signup_data']
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
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

        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            return render(request, self.template_name, {'error': 'رمز عبور و تکرار آن یکسان نیستند'})

        user = get_object_or_404(CustomUser, mobile=mobile)
        user.set_password(password)
        user.save()

        del request.session['verified_mobile']
        return redirect('accounts:login')


# Profile
class ProfileInfoView(LoginRequiredMixin, View):
    template_name = 'accounts/profile-info.html'
    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.bio = request.POST.get('bio', '')

        if request.FILES.get('avatar'):
            user.avatar = request.FILES['avatar']

        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')

        if current_password and new_password:
            if user.check_password(current_password):
                user.set_password(new_password)
            else:
                return render(request, self.template_name, {'error': 'رمز عبور فعلی اشتباه است'})

        user.save()
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
        Address.objects.create(user=request.user, first_name=request.POST.get('first_name'), last_name=request.POST.get('last_name'),
            email=request.POST.get('email', ''), phone=request.POST.get('phone'), address1=request.POST.get('address1'),
            address2=request.POST.get('address2', ''),
            city=request.POST.get('city'), zip=request.POST.get('zip'), is_default=request.POST.get('is_default') == 'on')
        return redirect('accounts:addresses')


class AddressEditView(LoginRequiredMixin, View):
    def get(self, request, pk):
        address = get_object_or_404(Address, pk=pk, user=request.user)
        return render(request, 'accounts/address-form.html', {'address': address})

    def post(self, request, pk):
        address = get_object_or_404(Address, pk=pk, user=request.user)
        address.first_name = request.POST.get('first_name')
        address.last_name = request.POST.get('last_name')
        address.email = request.POST.get('email', '')
        address.phone = request.POST.get('phone')
        address.address1 = request.POST.get('address1')
        address.address2 = request.POST.get('address2', '')
        address.city = request.POST.get('city')
        address.zip = request.POST.get('zip')
        address.is_default = request.POST.get('is_default') == 'on'
        address.save()
        return redirect('accounts:addresses')


class AddressDeleteView(LoginRequiredMixin, View):
    def get(self, request, pk):
        address = get_object_or_404(Address, pk=pk, user=request.user)
        address.delete()
        return redirect('accounts:addresses')