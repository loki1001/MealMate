from django.shortcuts import render, redirect
from django.views.generic import ListView, CreateView, DetailView
from .models import Ingredient, Recipe
import openai
from django.conf import settings
from django.http import JsonResponse


class HomeView(ListView):
    template_name = 'recipes/home.html'
    model = Recipe
    context_object_name = 'recipes'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ingredients'] = Ingredient.objects.all()
        return context


class AddIngredientView(CreateView):
    model = Ingredient
    fields = ['name', 'quantity', 'unit']
    template_name = 'recipes/add_ingredient.html'
    success_url = '/'


class RecipeDetailView(DetailView):
    model = Recipe
    template_name = 'recipes/recipe_detail.html'
    context_object_name = 'recipe'


client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

def generate_recipe(request):
    if request.method == 'POST':
        selected_ingredients = request.POST.getlist('ingredients')
        must_use_ingredient = request.POST.get('must_use')
        additional_ingredient = request.POST.get('additional')

        # Get all selected ingredients
        ingredients = Ingredient.objects.filter(id__in=selected_ingredients)
        ingredient_list = [i.name for i in ingredients]

        # Prepare prompt for ChatGPT
        prompt = f"Generate a recipe using these ingredients: {', '.join(ingredient_list)}"
        if must_use_ingredient:
            prompt += f"\nMust use: {must_use_ingredient}"
        if additional_ingredient:
            prompt += f"\nAlso include: {additional_ingredient}"

        try:
            # Call ChatGPT API
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system",
                     "content": "You are a helpful chef who creates recipes based on available ingredients."},
                    {"role": "user", "content": prompt}
                ]
            )

            recipe_text = response.choices[0].message.content

            # Create new recipe
            recipe = Recipe.objects.create(
                title=f"Recipe with {', '.join(ingredient_list[:3])}...",
                instructions=recipe_text
            )
            recipe.ingredients_used.set(ingredients)

            return redirect('recipe_detail', pk=recipe.pk)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return redirect('home')

'''
from django.shortcuts import render, redirect

from MealMate import settings
from .models import Item, Recipe
from .forms import ItemForm
import openai

def main_screen(request):
    return render(request, 'recipes/main_screen.html')

def add_item(request):
    if request.method == 'POST':
        form = ItemForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('main_screen')
    else:
        form = ItemForm()
    return render(request, 'recipes/add_item.html', {'form': form})

client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

def generate_recipes(request):
    items = Item.objects.all()  # Fetch all items in the inventory
    recipes = ""  # Initialize an empty string for recipes

    if request.method == 'POST':
        selected_ingredient = request.POST.get('ingredient', '')
        additional_ingredient = request.POST.get('additional_ingredient', '')

        # Construct the prompt for ChatGPT
        prompt = f"Generate a recipe using {selected_ingredient}"
        if additional_ingredient:
            prompt += f", and include {additional_ingredient} as well."

        try:
            # Use the updated method for generating chat completions
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300
            )

            # Get cleaned response
            recipes = response.choices[0].message.content.strip()
        except Exception as e:
            recipes = f"Error generating recipes: {str(e)}"

    return render(request, 'recipes/generate_recipes.html', {'items': items, 'recipes': recipes})
'''