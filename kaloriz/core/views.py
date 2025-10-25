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
from shipping.models import District, Address, Shipment
from shipping.views import calculate_shipping_cost, validate_shipping_data
from shipping.forms import AddressForm


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
    """Checkout page with shipping integration"""
    cart = get_object_or_404(Cart, user=request.user)

    if not cart.items.exists():
        messages.error(request, 'Keranjang Anda kosong.')
        return redirect('core:cart')

    # Get user profile for pre-filling form
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = None

    # Get user's saved addresses
    user_addresses = Address.objects.filter(user=request.user).select_related('district')

    # Get default address if exists
    default_address = user_addresses.filter(is_default=True).first()

    # Get all active districts for shipping
    districts = District.objects.filter(is_active=True).order_by('name')

    # Address form for adding new address
    address_form = AddressForm()

    context = {
        'cart': cart,
        'profile': profile,
        'user_addresses': user_addresses,
        'default_address': default_address,
        'districts': districts,
        'address_form': address_form,
    }
    return render(request, 'core/checkout.html', context)


@login_required
def place_order(request):
    """Process order placement with shipping integration"""
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

    # Validate shipping data (JANGAN PERCAYA DATA DARI CLIENT!)
    district_id = request.POST.get('district_id')
    service = request.POST.get('shipping_service')  # 'REG' or 'EXP'

    try:
        is_valid, error_message = validate_shipping_data(district_id, service)
        if not is_valid:
            messages.error(request, f'Data pengiriman tidak valid: {error_message}')
            return redirect('core:checkout')

        # Re-lookup shipping cost from database (SERVER-SIDE VALIDATION)
        subtotal = cart.get_total()
        shipping_cost, eta, district_name = calculate_shipping_cost(
            district_id, service, subtotal
        )

    except Exception as e:
        messages.error(request, f'Terjadi kesalahan dalam perhitungan ongkir: {str(e)}')
        return redirect('core:checkout')

    # Create order
    order_number = f'ORD-{uuid.uuid4().hex[:8].upper()}'

    order = Order.objects.create(
        user=request.user,
        order_number=order_number,
        full_name=request.POST.get('full_name'),
        email=request.POST.get('email'),
        phone=request.POST.get('phone'),
        address=request.POST.get('street'),  # Use 'street' from shipping form
        city='Makassar',  # Fixed city
        postal_code=request.POST.get('postal_code'),
        notes=request.POST.get('notes', ''),
        subtotal=subtotal,
        shipping_cost=shipping_cost,
        total=subtotal + shipping_cost,
    )

    # Create shipment record (snapshot of shipping data)
    Shipment.objects.create(
        order=order,
        full_name=request.POST.get('full_name'),
        phone=request.POST.get('phone'),
        street=request.POST.get('street'),
        district_name=district_name,
        postal_code=request.POST.get('postal_code'),
        service=service,
        cost=shipping_cost,
        eta=eta,
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
    """User registration with email verification"""
    if request.user.is_authenticated:
        return redirect('catalog:home')

    if request.method == 'POST':
        form = CustomUserRegistrationForm(request.POST)
        if form.is_valid():
            # Save user and profile
            user = form.save()

            # Create verification code
            ip_address = request.META.get('REMOTE_ADDR')
            verification = EmailVerification.create_verification(user, ip_address)

            # Send verification email
            if send_verification_email(user, verification):
                # Store user_id in session for verification step
                request.session['pending_verification_user_id'] = user.id
                request.session['verification_id'] = verification.id
                messages.success(request, f'Akun berhasil dibuat! Kode verifikasi telah dikirim ke {user.email}')
                return redirect('core:verify_email')
            else:
                messages.error(request, 'Gagal mengirim kode verifikasi. Silakan hubungi admin.')
                # Still allow registration to complete
                send_welcome_email(user)
                login(request, user)
                return redirect('catalog:home')
    else:
        form = CustomUserRegistrationForm()

    context = {'form': form}
    return render(request, 'core/register.html', context)


def login_view(request):
    """User login"""
    if request.user.is_authenticated:
        return redirect('catalog:home')

    if request.method == 'POST':
        # Try to authenticate with username or email
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
            login(request, user)
            messages.success(request, f'Selamat datang, {user.first_name or user.username}!')
            next_url = request.GET.get('next', 'catalog:home')
            return redirect(next_url)
        else:
            messages.error(request, 'Username/email atau password salah.')

    form = AuthenticationForm()
    context = {'form': form}
    return render(request, 'core/login.html', context)


def verify_email_view(request):
    """Verify email with OTP code after registration"""
    # Check if there's a pending verification
    user_id = request.session.get('pending_verification_user_id')
    verification_id = request.session.get('verification_id')

    if not user_id or not verification_id:
        messages.error(request, 'Sesi verifikasi tidak valid. Silakan daftar kembali.')
        return redirect('core:register')

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

                    # Send welcome email after successful verification
                    send_welcome_email(user)

                    # Log the user in
                    login(request, user)

                    # Clear session data
                    del request.session['pending_verification_user_id']
                    del request.session['verification_id']

                    messages.success(request, f'Email berhasil diverifikasi! Selamat datang, {user.first_name}!')
                    return redirect('catalog:home')
                else:
                    messages.error(request, 'Kode verifikasi salah. Silakan coba lagi.')
            else:
                messages.error(request, 'Kode verifikasi sudah kadaluarsa. Silakan minta kode baru.')
                # Don't delete session, allow resend

        except EmailVerification.DoesNotExist:
            messages.error(request, 'Verifikasi tidak ditemukan. Silakan daftar kembali.')
            return redirect('core:register')

    # Get user email for display
    from django.contrib.auth.models import User
    user = User.objects.get(id=user_id)
    masked_email = user.email[:3] + '***@' + user.email.split('@')[1]

    context = {
        'masked_email': masked_email,
        'is_registration': True,
    }
    return render(request, 'core/verify_email.html', context)


def resend_verification_code(request):
    """Resend verification code for email verification"""
    user_id = request.session.get('pending_verification_user_id')

    if not user_id:
        messages.error(request, 'Sesi verifikasi tidak valid.')
        return redirect('core:register')

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

    return redirect('core:verify_email')


@login_required
def logout_view(request):
    """User logout"""
    logout(request)
    messages.success(request, 'Anda berhasil logout.')
    return redirect('catalog:home')


# Profile Views
@login_required
def profile_view(request):
    """User profile page with address information"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    # Get primary shipping address
    address = Address.objects.filter(user=request.user, is_primary=True).first()

    context = {
        'profile': profile,
        'user': request.user,
        'address': address,
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


@login_required
def profile_address_edit(request):
    """Edit primary shipping address for RajaOngkir integration"""
    addr = Address.objects.filter(user=request.user, is_primary=True).first()
    if not addr:
        addr = Address(
            user=request.user,
            full_name=request.user.get_full_name() or request.user.username
        )

    if request.method == 'POST':
        form = AddressForm(request.POST, instance=addr)
        if form.is_valid():
            obj = form.save(commit=False)
            # Untuk sekarang provinsi kita set manual ke Sulawesi Selatan
            if not obj.province_name:
                obj.province_name = 'Sulawesi Selatan'
            obj.user = request.user
            obj.is_primary = True
            obj.save()
            messages.success(request, 'Alamat pengiriman berhasil diperbarui.')
            return redirect('core:profile')
    else:
        form = AddressForm(instance=addr)

    context = {
        'form': form,
        'address': addr,
    }
    return render(request, 'core/profile_address_edit.html', context)


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
