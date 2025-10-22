from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.db.models import F
from django.utils import timezone
from decimal import Decimal
import uuid

from .models import Cart, CartItem, Order, OrderItem, UserProfile
from catalog.models import Product


# Cart Views
@login_required
def cart_view(request):
    """Display user's shopping cart"""
    cart, created = Cart.objects.get_or_create(user=request.user)
    context = {
        'cart': cart,
    }
    return render(request, 'core/cart.html', context)


@login_required
def add_to_cart(request, product_id):
    """Add product to cart"""
    product = get_object_or_404(Product, id=product_id, available=True)
    cart, created = Cart.objects.get_or_create(user=request.user)

    # Check stock
    quantity = int(request.POST.get('quantity', 1))
    if product.stock < quantity:
        messages.error(request, f'Stok {product.name} tidak mencukupi.')
        return redirect('catalog:product_detail', slug=product.slug)

    # Add or update cart item
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': quantity}
    )

    if not created:
        # Update quantity if item already exists
        new_quantity = cart_item.quantity + quantity
        if product.stock >= new_quantity:
            cart_item.quantity = new_quantity
            cart_item.save()
        else:
            messages.error(request, f'Stok {product.name} tidak mencukupi.')
            return redirect('catalog:product_detail', slug=product.slug)

    messages.success(request, f'{product.name} berhasil ditambahkan ke keranjang.')
    return redirect('core:cart')


@login_required
def update_cart_item(request, item_id):
    """Update cart item quantity"""
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    quantity = int(request.POST.get('quantity', 1))

    if quantity > 0:
        if cart_item.product.stock >= quantity:
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, 'Keranjang berhasil diperbarui.')
        else:
            messages.error(request, f'Stok {cart_item.product.name} tidak mencukupi.')
    else:
        cart_item.delete()
        messages.success(request, 'Item berhasil dihapus dari keranjang.')

    return redirect('core:cart')


@login_required
def remove_from_cart(request, item_id):
    """Remove item from cart"""
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    product_name = cart_item.product.name
    cart_item.delete()
    messages.success(request, f'{product_name} berhasil dihapus dari keranjang.')
    return redirect('core:cart')


@login_required
def clear_cart(request):
    """Clear all items from cart"""
    cart = get_object_or_404(Cart, user=request.user)
    cart.items.all().delete()
    messages.success(request, 'Keranjang berhasil dikosongkan.')
    return redirect('core:cart')


# Checkout Views
@login_required
def checkout(request):
    """Checkout page"""
    cart = get_object_or_404(Cart, user=request.user)

    if not cart.items.exists():
        messages.error(request, 'Keranjang Anda kosong.')
        return redirect('core:cart')

    # Get user profile for pre-filling form
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = None

    context = {
        'cart': cart,
        'profile': profile,
    }
    return render(request, 'core/checkout.html', context)


@login_required
def place_order(request):
    """Process order placement"""
    if request.method != 'POST':
        return redirect('core:checkout')

    cart = get_object_or_404(Cart, user=request.user)

    if not cart.items.exists():
        messages.error(request, 'Keranjang Anda kosong.')
        return redirect('core:cart')

    # Validate stock availability
    for item in cart.items.all():
        if item.product.stock < item.quantity:
            messages.error(request, f'Stok {item.product.name} tidak mencukupi.')
            return redirect('core:cart')

    # Create order
    order_number = f'ORD-{uuid.uuid4().hex[:8].upper()}'
    shipping_cost = Decimal('10000.00')  # Fixed shipping cost

    order = Order.objects.create(
        user=request.user,
        order_number=order_number,
        full_name=request.POST.get('full_name'),
        email=request.POST.get('email'),
        phone=request.POST.get('phone'),
        address=request.POST.get('address'),
        city=request.POST.get('city'),
        postal_code=request.POST.get('postal_code'),
        notes=request.POST.get('notes', ''),
        subtotal=cart.get_total(),
        shipping_cost=shipping_cost,
        total=cart.get_total() + shipping_cost,
    )

    # Create order items and update stock
    for item in cart.items.all():
        OrderItem.objects.create(
            order=order,
            product=item.product,
            product_name=item.product.name,
            product_price=item.product.get_display_price(),
            quantity=item.quantity,
            subtotal=item.get_subtotal(),
        )

        # Update product stock
        item.product.stock = F('stock') - item.quantity
        item.product.save()

    # Clear cart
    cart.items.all().delete()

    messages.success(request, f'Pesanan berhasil dibuat! Nomor pesanan: {order_number}')
    return redirect('core:order_detail', order_number=order_number)


# Order Views
@login_required
def order_list(request):
    """List user's orders"""
    orders = Order.objects.filter(user=request.user)
    context = {
        'orders': orders,
    }
    return render(request, 'core/order_list.html', context)


@login_required
def order_detail(request, order_number):
    """Order detail page"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    context = {
        'order': order,
    }
    return render(request, 'core/order_detail.html', context)


# Authentication Views
def register_view(request):
    """User registration"""
    if request.user.is_authenticated:
        return redirect('catalog:home')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create user profile
            UserProfile.objects.create(user=user)
            # Log the user in
            login(request, user)
            messages.success(request, 'Akun berhasil dibuat!')
            return redirect('catalog:home')
    else:
        form = UserCreationForm()

    context = {'form': form}
    return render(request, 'core/register.html', context)


def login_view(request):
    """User login"""
    if request.user.is_authenticated:
        return redirect('catalog:home')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Selamat datang, {username}!')
                next_url = request.GET.get('next', 'catalog:home')
                return redirect(next_url)
    else:
        form = AuthenticationForm()

    context = {'form': form}
    return render(request, 'core/login.html', context)


@login_required
def logout_view(request):
    """User logout"""
    logout(request)
    messages.success(request, 'Anda berhasil logout.')
    return redirect('catalog:home')


# Profile Views
@login_required
def profile_view(request):
    """User profile page"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        profile.phone = request.POST.get('phone', '')
        profile.address = request.POST.get('address', '')
        profile.city = request.POST.get('city', '')
        profile.postal_code = request.POST.get('postal_code', '')
        profile.save()
        messages.success(request, 'Profil berhasil diperbarui.')
        return redirect('core:profile')

    context = {
        'profile': profile,
    }
    return render(request, 'core/profile.html', context)
