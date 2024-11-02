from django.urls import path
from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('add-ingredient/', views.AddIngredientView.as_view(), name='add_ingredient'),
    path('generate-recipe/', views.generate_recipe, name='generate_recipe'),
    path('recipe/<int:pk>/', views.RecipeDetailView.as_view(), name='recipe_detail'),
]