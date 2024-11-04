# views.py
import json

from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Ingredient, Recipe, RecipeIngredient
import openai
import os
from django.contrib.auth import login, authenticate
from .forms import SignUpForm
from fractions import Fraction

def convert_to_decimal(quantity):
    try:
        # Convert the quantity to a decimal number
        return str(float(Fraction(quantity)))
    except ValueError:
        # Return the original value if conversion fails
        return quantity

def home(request):
    return render(request, 'recipes/home.html')

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Log the user in automatically after registration
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=user.username, password=raw_password)
            login(request, user)
            return redirect('home')
    else:
        form = SignUpForm()
    return render(request, 'recipes/signup.html', {'form': form})


@login_required(login_url='/login/')
def my_items(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        quantity = request.POST.get('quantity')
        unit = request.POST.get('unit')
        Ingredient.objects.create(
            user=request.user,
            name=name,
            quantity=quantity,
            unit=unit
        )
        return redirect('my_items')

    ingredients = Ingredient.objects.filter(user=request.user)
    return render(request, 'recipes/my_items.html', {'ingredients': ingredients})


@login_required(login_url='/login/')
def delete_ingredient(request, ingredient_id):
    try:
        ingredient = Ingredient.objects.get(id=ingredient_id, user=request.user)
        ingredient.delete()
        messages.success(request, 'Ingredient deleted successfully.')
    except Ingredient.DoesNotExist:
        messages.error(request, 'Ingredient not found.')
    return redirect('my_items')


@login_required(login_url='/login/')
def generate_recipe(request):
    ingredients = Ingredient.objects.filter(user=request.user)
    return render(request, 'recipes/generate_recipe.html', {'ingredients': ingredients})


@login_required(login_url='/login/')
def choose_diet(request):
    if request.method == 'POST':
        # Get database ingredients
        db_ingredients = request.POST.get('db_ingredients', '').split(',')
        db_ingredients = [id for id in db_ingredients if id]

        # Get temporary ingredients
        temp_ingredients_json = request.POST.get('temp_ingredients', '[]')
        try:
            temp_ingredients = json.loads(temp_ingredients_json)

            # Store both types of ingredients in session
            request.session['db_ingredients'] = db_ingredients
            request.session['temp_ingredients'] = temp_ingredients

            return render(request, 'recipes/choose_diet.html')
        except json.JSONDecodeError:
            messages.error(request, 'Error processing ingredients')
            return redirect('generate_recipe')
    return redirect('generate_recipe')


@login_required(login_url='/login/')
def choose_servings(request):
    if request.method == 'POST':
        diet_type = request.POST.get('diet_type')
        request.session['diet_type'] = diet_type
        return render(request, 'recipes/choose_servings.html')
    return redirect('choose_diet')


@login_required(login_url='/login/')
def review(request):
    if request.method == 'POST':
        servings = request.POST.get('servings')
        request.session['servings'] = servings

        # Get both types of ingredients from session
        db_ingredients = request.session.get('db_ingredients', [])
        temp_ingredients = request.session.get('temp_ingredients', [])
        diet_type = request.session.get('diet_type')

        # Get database ingredients
        db_ingredients_objects = Ingredient.objects.filter(id__in=db_ingredients)

        # Create temporary ingredient objects (without saving to database)
        temp_ingredients_objects = [
            {
                'name': ing['name'],
                'quantity': ing['quantity'],
                'unit': ing['unit']
            }
            for ing in temp_ingredients
        ]

        context = {
            'db_ingredients': db_ingredients_objects,
            'temp_ingredients': temp_ingredients_objects,
            'diet_type': diet_type,
            'servings': servings,
        }
        return render(request, 'recipes/review.html', context)
    return redirect('choose_servings')

client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
@login_required(login_url='/login/')
def generate(request):
    db_ingredients = request.session.get('db_ingredients', [])
    temp_ingredients = request.session.get('temp_ingredients', [])
    diet_type = request.session.get('diet_type')
    servings = request.session.get('servings')

    # Get database ingredients
    db_ingredients_list = Ingredient.objects.filter(id__in=db_ingredients)

    # Prepare ingredient texts for the prompt
    ingredients_text = ", ".join([
        f"{i.quantity} {i.unit} {i.name}" for i in db_ingredients_list
    ] + [
        f"{ing['quantity']} {ing['unit']} {ing['name']}" for ing in temp_ingredients
    ])

    prompt = f"""
        Create a {diet_type} recipe for {servings} people using these ingredients: {ingredients_text}.
        Please ensure all ingredient quantities are specified in decimal format and avoid using terms like "to taste" or "to preference."
        Return a JSON object with the following structure:
        {{
            "title": "Title of the dish",
            "ingredients": [
                {{"name": "ingredient_name", "quantity": "amount", "unit": "unit"}},
                ...
            ],
            "servings": "number of servings",
            "cook_time": "cooking time",
            "instructions": [
                "Step 1: instruction",
                ...
            ]
        }}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful chef who creates recipes based on available ingredients."},
                {"role": "user", "content": prompt}
            ]
        )
        response_content = response.choices[0].message.content
        recipe_data = json.loads(response_content)
        print(recipe_data)

        # Create the recipe without adding ingredients to user's owned ingredients
        recipe = Recipe.objects.create(
            user=request.user,
            title=recipe_data["title"],
            cook_time=recipe_data["cook_time"],
            diet_type=diet_type,
            servings=recipe_data["servings"],
            instructions="\n".join(recipe_data.get("instructions", []))
        )

        # Process ingredients specifically for the recipe
        for ing in recipe_data["ingredients"]:
            RecipeIngredient.objects.create(
                recipe=recipe,
                name=ing["name"],
                quantity=convert_to_decimal(ing["quantity"]),
                unit=ing["unit"]
            )

        return render(request, 'recipes/recipe_result.html', {'recipe': recipe})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Failed to decode response'}, status=500)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
