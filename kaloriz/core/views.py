from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.db.models import F
from django.utils import timezone
from decimal import Decimal
import uuid

from .models import Cart, CartItem, Order, OrderItem, UserProfile, Watchlist, EmailVerification
from catalog.models import Product
from .forms import CustomUserRegistrationForm
from .utils import send_verification_email, send_welcome_email


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
    """User registration with custom form"""
    if request.user.is_authenticated:
        return redirect('catalog:home')

    if request.method == 'POST':
        form = CustomUserRegistrationForm(request.POST)
        if form.is_valid():
            # Save user and profile
            user = form.save()

            # Send welcome email
            send_welcome_email(user)

            # Log the user in automatically
            login(request, user)
            messages.success(request, f'Selamat datang, {user.first_name}! Akun Anda berhasil dibuat.')
            return redirect('catalog:home')
    else:
        form = CustomUserRegistrationForm()

    context = {'form': form}
    return render(request, 'core/register.html', context)


def login_view(request):
    """User login with email verification"""
    if request.user.is_authenticated:
        return redirect('catalog:home')

    if request.method == 'POST':
        # Step 1: Authenticate username and password
        username_or_email = request.POST.get('username')
        password = request.POST.get('password')

        # Try to find user by username or email
        from django.contrib.auth.models import User
        try:
            if '@' in username_or_email:
                user = User.objects.get(email=username_or_email)
                username = user.username
            else:
                username = username_or_email
        except User.DoesNotExist:
            messages.error(request, 'Username atau email tidak ditemukan.')
            return render(request, 'core/login.html', {'form': AuthenticationForm()})

        # Authenticate
        user = authenticate(username=username, password=password)

        if user is not None:
            # Step 2: Create verification code and send email
            ip_address = request.META.get('REMOTE_ADDR')
            verification = EmailVerification.create_verification(user, ip_address)

            # Send verification code via email
            if send_verification_email(user, verification):
                # Store user_id in session for verification step
                request.session['pending_login_user_id'] = user.id
                request.session['verification_id'] = verification.id
                messages.info(request, f'Kode verifikasi telah dikirim ke {user.email}')
                return redirect('core:verify_login')
            else:
                messages.error(request, 'Gagal mengirim kode verifikasi. Silakan coba lagi.')
        else:
            messages.error(request, 'Username/email atau password salah.')

    form = AuthenticationForm()
    context = {'form': form}
    return render(request, 'core/login.html', context)


def verify_login_view(request):
    """Verify OTP code for login"""
    # Check if there's a pending login
    user_id = request.session.get('pending_login_user_id')
    verification_id = request.session.get('verification_id')

    if not user_id or not verification_id:
        messages.error(request, 'Sesi verifikasi tidak valid. Silakan login kembali.')
        return redirect('core:login')

    if request.method == 'POST':
        code = request.POST.get('code', '').strip()

        try:
            verification = EmailVerification.objects.get(id=verification_id)

            if verification.is_valid():
                if verification.code == code:
                    # Code is correct, mark as used
                    verification.mark_as_used()

                    # Log the user in
                    from django.contrib.auth.models import User
                    user = User.objects.get(id=user_id)
                    login(request, user)

                    # Clear session data
                    del request.session['pending_login_user_id']
                    del request.session['verification_id']

                    messages.success(request, f'Selamat datang, {user.first_name or user.username}!')
                    next_url = request.GET.get('next', 'catalog:home')
                    return redirect(next_url)
                else:
                    messages.error(request, 'Kode verifikasi salah. Silakan coba lagi.')
            else:
                messages.error(request, 'Kode verifikasi sudah kadaluarsa atau sudah digunakan. Silakan login ulang.')
                del request.session['pending_login_user_id']
                del request.session['verification_id']
                return redirect('core:login')

        except EmailVerification.DoesNotExist:
            messages.error(request, 'Verifikasi tidak ditemukan. Silakan login kembali.')
            return redirect('core:login')

    # Get user email for display
    from django.contrib.auth.models import User
    user = User.objects.get(id=user_id)
    masked_email = user.email[:3] + '***@' + user.email.split('@')[1]

    context = {
        'masked_email': masked_email,
    }
    return render(request, 'core/verify_login.html', context)


def resend_verification_code(request):
    """Resend verification code"""
    user_id = request.session.get('pending_login_user_id')

    if not user_id:
        messages.error(request, 'Sesi verifikasi tidak valid.')
        return redirect('core:login')

    from django.contrib.auth.models import User
    user = User.objects.get(id=user_id)

    # Create new verification code
    ip_address = request.META.get('REMOTE_ADDR')
    verification = EmailVerification.create_verification(user, ip_address)

    # Send email
    if send_verification_email(user, verification):
        # Update session with new verification_id
        request.session['verification_id'] = verification.id
        messages.success(request, 'Kode verifikasi baru telah dikirim ke email Anda.')
    else:
        messages.error(request, 'Gagal mengirim kode verifikasi. Silakan coba lagi.')

    return redirect('core:verify_login')


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

    context = {
        'profile': profile,
        'user': request.user,
    }
    return render(request, 'core/profile.html', context)


@login_required
def profile_settings(request):
    """User profile settings page"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        # Update user info
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        request.user.email = request.POST.get('email', '')
        request.user.save()

        # Update profile info
        profile.phone = request.POST.get('phone', '')
        profile.address = request.POST.get('address', '')
        profile.city = request.POST.get('city', '')
        profile.postal_code = request.POST.get('postal_code', '')
        profile.gender = request.POST.get('gender', '')

        birth_date = request.POST.get('birth_date', '')
        if birth_date:
            profile.birth_date = birth_date

        profile.save()
        messages.success(request, 'Profil berhasil diperbarui.')
        return redirect('core:profile_settings')

    context = {
        'profile': profile,
        'user': request.user,
    }
    return render(request, 'core/profile_settings.html', context)


# Watchlist Views
@login_required
def watchlist_view(request):
    """Display user's watchlist"""
    watchlist_items = Watchlist.objects.filter(user=request.user).select_related('product')

    context = {
        'watchlist_items': watchlist_items,
    }
    return render(request, 'core/watchlist.html', context)


@login_required
def add_to_watchlist(request, product_id):
    """Add product to watchlist"""
    product = get_object_or_404(Product, id=product_id)

    watchlist_item, created = Watchlist.objects.get_or_create(
        user=request.user,
        product=product
    )

    if created:
        messages.success(request, f'{product.name} berhasil ditambahkan ke watchlist.')
    else:
        messages.info(request, f'{product.name} sudah ada di watchlist Anda.')

    return redirect(request.META.get('HTTP_REFERER', 'catalog:home'))


@login_required
def remove_from_watchlist(request, watchlist_id):
    """Remove item from watchlist"""
    watchlist_item = get_object_or_404(Watchlist, id=watchlist_id, user=request.user)
    product_name = watchlist_item.product.name
    watchlist_item.delete()
    messages.success(request, f'{product_name} berhasil dihapus dari watchlist.')
    return redirect('core:watchlist')
