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


@login_required
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


@login_required
def generate_recipe(request):
    ingredients = Ingredient.objects.filter(user=request.user)
    return render(request, 'recipes/generate_recipe.html', {'ingredients': ingredients})


@login_required
def choose_diet(request):
    if request.method == 'POST':
        selected_ingredients = request.POST.getlist('ingredients')
        request.session['selected_ingredients'] = selected_ingredients
        return render(request, 'recipes/choose_diet.html')
    return redirect('generate_recipe')


@login_required
def choose_servings(request):
    if request.method == 'POST':
        diet_type = request.POST.get('diet_type')
        request.session['diet_type'] = diet_type
        return render(request, 'recipes/choose_servings.html')
    return redirect('choose_diet')


@login_required
def review(request):
    if request.method == 'POST':
        servings = request.POST.get('servings')
        request.session['servings'] = servings

        selected_ingredients = request.session.get('selected_ingredients', [])
        diet_type = request.session.get('diet_type')

        context = {
            'ingredients': Ingredient.objects.filter(id__in=selected_ingredients),
            'diet_type': diet_type,
            'servings': servings,
        }
        return render(request, 'recipes/review.html', context)
    return redirect('choose_servings')


@login_required
def generate(request):
    ingredients = request.session.get('selected_ingredients', [])
    diet_type = request.session.get('diet_type')
    servings = request.session.get('servings')

    # Call ChatGPT API
    ingredients_list = Ingredient.objects.filter(id__in=ingredients)
    ingredients_text = ", ".join([f"{i.quantity} {i.unit} {i.name}" for i in ingredients_list])

    prompt = f"Create a {diet_type} recipe for {servings} people using these ingredients: {ingredients_text}"

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        recipe_text = response.choices[0].message.content

        # Save recipe
        recipe = Recipe.objects.create(
            user=request.user,
            title=f"{diet_type.capitalize()} Recipe",
            instructions=recipe_text,
            diet_type=diet_type,
            servings=servings
        )
        recipe.ingredients.set(ingredients_list)

        return render(request, 'recipes/recipe_result.html', {'recipe': recipe})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)