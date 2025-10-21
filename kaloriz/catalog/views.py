from django.shortcuts import render

def home(request):
    return render(request, "catalog/index.html")

def menu(request):
    return render(request, "catalog/menu.html")

def about(request):
    return render(request, "catalog/about.html")

def book(request):
    return render(request, "catalog/book.html")
from django.shortcuts import render

def home(request):  return render(request, "catalog/index.html")
def menu(request):  return render(request, "catalog/menu.html")
def about(request): return render(request, "catalog/about.html")
def book(request):  return render(request, "catalog/book.html")
