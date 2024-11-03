# urls.py
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home, name='home'),
    path('my-items/', views.my_items, name='my_items'),
    path('delete_ingredient/<int:ingredient_id>/', views.delete_ingredient, name='delete_ingredient'),
    path('generate-recipe/', views.generate_recipe, name='generate_recipe'),
    path('choose-diet/', views.choose_diet, name='choose_diet'),
    path('choose-servings/', views.choose_servings, name='choose_servings'),
    path('review/', views.review, name='review'),
    path('generate/', views.generate, name='generate'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('signup/', views.signup, name='signup'),
]