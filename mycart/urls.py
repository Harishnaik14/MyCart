from django.urls import path
from .import views 

urlpatterns = [
  path('order/', views.order, name='order'),
  path('sell/', views.sell, name='sell'),
  
  path('signup/', views.signup, name='signup'),
  path('search/', views.search, name='search'),
  path('items/mobiles/', views.mobiles, name='mobiles'),
  path('login/', views.login_view, name='login'),
  path('logout/', views.logout_view, name='logout'),
    # Forgot password via phone number
  path("forgot-password/", views.forgot_password, name="forgot_password"),
  path("reset/<uid>/", views.reset_password, name="reset_password"),
  path('', views.home, name='home'),
  path('product/<int:id>/', views.product_detail, name='product_detail'),
  path('add-to-cart/<int:id>/', views.add_to_cart, name='add_to_cart'),
  path('remove-from-cart/<int:id>/', views.remove_from_cart, name='remove_from_cart'),
  path('cart/', views.cart, name='cart'),
  path('buy/<int:id>/', views.buy_now, name='buy_now'),
  path('address/', views.address, name='address'),
  path('place-order/', views.place_order, name='place_order'),
  path('order-qr/<str:order_id>/', views.order_qr, name='order_qr'),
  path('thanks/', views.thanks, name='thanks'),
  path("qr-scan/", views.qr_scanner, name="qr_scanner"),
  path("qr-result/", views.qr_result, name="qr_result"),
]

