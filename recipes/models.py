from django.db import models
from django.contrib.auth.models import User

# Ingredient model represents an ingredient associated with a user.
class Ingredient(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Links to the User who created the ingredient
    name = models.CharField(max_length=100)  # The name of the ingredient
    quantity = models.DecimalField(max_digits=10, decimal_places=2)  # Quantity of the ingredient
    unit = models.CharField(max_length=20)  # Unit of measurement (e.g., grams, liters)
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp when the ingredient was created

    def __str__(self):
        return f"{self.name} - {self.quantity} {self.unit}"

# Recipe model represents a recipe associated with a user.
class Recipe(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Links to the User who created the recipe
    title = models.CharField(max_length=200)  # The title of the recipe
    instructions = models.TextField()  # The cooking instructions
    cook_time = models.TextField()  # Cooking time
    diet_type = models.CharField(max_length=50)  # Diet type (e.g., vegetarian, gluten-free)
    servings = models.IntegerField()  # Number of servings the recipe yields
    accepted = models.BooleanField(default=False)  # Whether the recipe is accepted
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp when the recipe was created

    def __str__(self):
        return self.title

# RecipeIngredient model represents the ingredients used in a specific recipe.
class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='recipe_ingredients')  # Links to the Recipe this ingredient belongs to
    name = models.CharField(max_length=100)  # Name of the ingredient in the recipe
    quantity = models.DecimalField(max_digits=10, decimal_places=2)  # Quantity of the ingredient in the recipe
    unit = models.CharField(max_length=20)  # Unit of measurement for the ingredient

    def __str__(self):
        return f"{self.name} - {self.quantity} {self.unit} for {self.recipe.title}"