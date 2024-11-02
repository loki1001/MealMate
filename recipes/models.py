from django.db import models

class Ingredient(models.Model):
    name = models.CharField(max_length=100)
    quantity = models.FloatField()
    unit = models.CharField(max_length=20)
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.quantity} {self.unit})"

class Recipe(models.Model):
    title = models.CharField(max_length=200)
    instructions = models.TextField()
    ingredients_used = models.ManyToManyField(Ingredient)
    date_generated = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title