from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [

    # Auth
    path('login/', views.LoginView.as_view(), name='login'),
    path('signup/', views.SignupView.as_view(), name='signup'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('forgot-password/', views.ForgotPasswordView.as_view(), name='forgot_password'),

    # OTP
    path('send-otp/', views.SendOTPView.as_view(), name='send_otp'),
    path('verify-otp/', views.VerifyOTPView.as_view(), name='verify_otp'),
    path('reset-password/', views.ResetPasswordView.as_view(), name='reset_password'),

    # Profile
    path('profile/', views.ProfileInfoView.as_view(), name='profile_info'),
    path('my-orders/', views.MyOrdersView.as_view(), name='my_orders'),
    path('wishlist/', views.WishlistView.as_view(), name='wishlist'),

    # Wishlist
    path('wishlist/add/', views.WishlistAddView.as_view(), name='wishlist_add'),
    path('wishlist/remove/', views.WishlistRemoveView.as_view(), name='wishlist_remove'),

    # Addresses
    path('addresses/', views.AddressesView.as_view(), name='addresses'),
    path('addresses/create/', views.AddressCreateView.as_view(), name='addresses_create'),
    path('addresses/edit/<int:pk>/', views.AddressEditView.as_view(), name='addresses_edit'),
    path('addresses/delete/<int:pk>/', views.AddressDeleteView.as_view(), name='addresses_delete'),
]