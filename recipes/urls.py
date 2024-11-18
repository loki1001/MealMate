# urls.py
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Home page route
    path('', views.home, name='home'),

    # Route for the user's items (e.g., ingredients, recipes)
    path('my-items/', views.my_items, name='my_items'),

    # Route for deleting an ingredient (identified by its ID)
    path('delete_ingredient/<int:ingredient_id>/', views.delete_ingredient, name='delete_ingredient'),

    # Route to generate a recipe based on selected ingredients and preferences
    path('generate-recipe/', views.generate_recipe, name='generate_recipe'),

    # Route for choosing the diet type (e.g., vegetarian, vegan)
    path('choose-diet/', views.choose_diet, name='choose_diet'),

    # Route for choosing the number of servings for the recipe
    path('choose-servings/', views.choose_servings, name='choose_servings'),

    # Route for reviewing the choices before generating the recipe
    path('review/', views.review, name='review'),

    # Route to actually generate the recipe after reviewing
    path('generate/', views.generate, name='generate'),

    # Login route, uses Django's built-in LoginView
    path('login/', auth_views.LoginView.as_view(), name='login'),

    # Logout route, uses Django's built-in LogoutView
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Sign-up route for creating a new account
    path('signup/', views.signup, name='signup'),

    # Route for viewing the details of a specific recipe
    path('recipe/<int:recipe_id>/', views.recipe_detail, name='recipe_detail'),

    # Route for accepting a recipe (e.g., for approval)
    path('accept_recipe/<int:recipe_id>/', views.accept_recipe, name='accept_recipe'),

    # Route for rejecting a recipe (e.g., for disapproval)
    path('recipe/<int:recipe_id>/reject/', views.reject_recipe, name='reject_recipe'),

    # Route for viewing the user's recipes
    path('my_recipes/', views.my_recipes, name='my_recipes'),

    # Route for deleting a specific recipe
    path('recipe/delete/<int:id>/', views.delete_recipe, name='delete_recipe'),

    # Chatbot route for interacting with a specific recipe
    path("chatbot/<int:recipe_id>/", views.chatbot, name="chatbot"),

    # Route for clearing the conversation history of the chatbot
    path('clear_conversation/<int:recipe_id>/', views.clear_conversation, name='clear_conversation'),

    # Route for generating a flexible recipe (e.g., based on preferences)
    path('generate-flexible/', views.generate_flexible, name='generate_flexible'),
]