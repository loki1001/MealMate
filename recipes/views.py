import json

from django.conf import settings
from django.core.checks import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Ingredient, Recipe
import openai
import os
from django.contrib.auth import login, authenticate
from .forms import SignUpForm


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

    # Combine ingredients texts
    ingredients_text = ", ".join([
                                     f"{i.quantity} {i.unit} {i.name}" for i in db_ingredients_list
                                 ] + [
                                     f"{i['quantity']} {i['unit']} {i['name']}" for i in temp_ingredients
                                 ])

    prompt = f"Create a {diet_type} recipe for {servings} people using these ingredients: {ingredients_text}"

    print(prompt)
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system",
                 "content": "You are a helpful chef who creates recipes based on available ingredients."},
                {"role": "user", "content": prompt}
            ]
        )
        recipe_text = response.choices[0].message.content

        # Save recipe (only with database ingredients)
        recipe = Recipe.objects.create(
            user=request.user,
            title=f"{diet_type.capitalize()} Recipe",
            instructions=recipe_text,
            diet_type=diet_type,
            servings=servings
        )
        recipe.ingredients.set(db_ingredients_list)

        return render(request, 'recipes/recipe_result.html', {
            'recipe': recipe,
            'temp_ingredients': temp_ingredients  # Pass temp ingredients to template
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)