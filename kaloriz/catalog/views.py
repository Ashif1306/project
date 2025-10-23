from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Product, Category, Testimonial


def home(request):
    """Homepage with featured products"""
    featured_products = Product.objects.filter(available=True)[:8]
    categories = Category.objects.all()[:6]

    context = {
        'featured_products': featured_products,
        'categories': categories,
    }
    return render(request, 'catalog/home.html', context)


def product_list(request):
    """List all available products with filtering and search"""
    products = Product.objects.filter(available=True)
    categories = Category.objects.all()

    # Filter by category
    category_slug = request.GET.get('category')
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)

    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Filter by price range
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)

    # Sort
    sort_by = request.GET.get('sort', '-created_at')
    if sort_by in ['price', '-price', 'name', '-name', '-created_at']:
        products = products.order_by(sort_by)

    context = {
        'products': products,
        'categories': categories,
        'current_category': category_slug,
        'search_query': search_query,
    }
    return render(request, 'catalog/product_list.html', context)


def product_detail(request, slug):
    """Product detail page"""
    product = get_object_or_404(Product, slug=slug, available=True)
    related_products = Product.objects.filter(
        category=product.category,
        available=True
    ).exclude(id=product.id)[:4]

    # Get approved testimonials for this product
    testimonials = Testimonial.objects.filter(
        product=product,
        is_approved=True
    ).select_related('user')[:10]

    context = {
        'product': product,
        'related_products': related_products,
        'testimonials': testimonials,
    }
    return render(request, 'catalog/product_detail.html', context)


def category_detail(request, slug):
    """Category page showing all products in category"""
    category = get_object_or_404(Category, slug=slug)
    products = Product.objects.filter(category=category, available=True)

    context = {
        'category': category,
        'products': products,
    }
    return render(request, 'catalog/category_detail.html', context)


def search(request):
    """Search products"""
    query = request.GET.get('q', '')
    products = Product.objects.filter(available=True)

    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(category__name__icontains=query)
        )

    context = {
        'products': products,
        'query': query,
    }
    return render(request, 'catalog/search_results.html', context)


def about(request):
    """About us page"""
    return render(request, 'catalog/about.html')


def contact(request):
    """Contact us page"""
    from django.http import JsonResponse

    if request.method == 'POST':
        # Handle contact form submission
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        subject = request.POST.get('subject')
        message = request.POST.get('message')

        # Here you can add logic to save to database or send email
        # For now, just return success
        messages.success(request, f'Terima kasih {name}! Pesan Anda telah diterima.')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})

        return redirect('catalog:contact')

    return render(request, 'catalog/contact.html')
