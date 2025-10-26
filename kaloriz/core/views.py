from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.db.models import F
from django.utils import timezone
from django.utils.formats import number_format
from decimal import Decimal
import uuid

from .models import Cart, CartItem, Order, OrderItem, UserProfile, Watchlist, EmailVerification
from catalog.models import Product
from .forms import CustomUserRegistrationForm
from .utils import send_verification_email, send_welcome_email
from shipping.models import District, Address, Shipment
from shipping.views import calculate_shipping_cost, validate_shipping_data
from shipping.forms import AddressForm

from django.http import JsonResponse
from django.views.decorators.http import require_POST

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
    from django.http import JsonResponse

    product = get_object_or_404(Product, id=product_id, available=True)
    cart, created = Cart.objects.get_or_create(user=request.user)

    # Check stock
    quantity = int(request.POST.get('quantity', 1))
    if product.stock < quantity:
        if request.POST.get('buy_now'):
            return JsonResponse({'success': False, 'message': 'Stok tidak mencukupi'})
        messages.error(request, f'Stok {product.name} tidak mencukupi.')
        return redirect('catalog:product_detail', slug=product.slug)

    # Check if this is a "Buy Now" request
    is_buy_now = request.POST.get('buy_now') == 'true'

    if is_buy_now:
        # Unselect all current items
        cart.items.all().update(is_selected=False)

    # Add or update cart item
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': quantity, 'is_selected': True}
    )

    if not created:
        # Update quantity if item already exists
        if is_buy_now:
            # For buy now, replace quantity instead of adding
            cart_item.quantity = quantity
        else:
            new_quantity = cart_item.quantity + quantity
            if product.stock < new_quantity:
                if request.POST.get('buy_now'):
                    return JsonResponse({'success': False, 'message': 'Stok tidak mencukupi'})
                messages.error(request, f'Stok {product.name} tidak mencukupi.')
                return redirect('catalog:product_detail', slug=product.slug)
            cart_item.quantity = new_quantity

        cart_item.is_selected = True
        cart_item.save()

    if is_buy_now:
        return JsonResponse({'success': True})

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


@login_required
def toggle_cart_item_selection(request, item_id):
    """Toggle cart item selection for checkout"""
    from django.http import JsonResponse
    import json

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid method'})

    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)

    try:
        data = json.loads(request.body)
        is_selected = data.get('is_selected', True)
        cart_item.is_selected = is_selected
        cart_item.save()

        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def delete_selected_cart_items(request):
    """Delete selected cart items"""
    from django.http import JsonResponse
    import json

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid method'})

    try:
        data = json.loads(request.body)
        item_ids = data.get('item_ids', [])

        if not item_ids:
            return JsonResponse({'success': False, 'message': 'No items selected'})

        # Delete items that belong to current user
        deleted_count = CartItem.objects.filter(
            id__in=item_ids,
            cart__user=request.user
        ).delete()[0]

        return JsonResponse({
            'success': True,
            'message': f'{deleted_count} item berhasil dihapus'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


# Checkout Views
@login_required
def checkout(request):
    """Modern multi-step checkout - Step 1: Select Address"""
    cart = get_object_or_404(Cart, user=request.user)

    # Check if there are any selected items
    selected_items = cart.items.filter(is_selected=True)

    if not selected_items.exists():
        messages.error(request, 'Pilih minimal 1 item untuk checkout.')
        return redirect('core:cart')

    # Get user profile for pre-filling form
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = None

    user_addresses = list(
        Address.objects.filter(user=request.user)
        .select_related('district')
        .order_by('-is_default', '-created_at')
    )

    default_address = next((addr for addr in user_addresses if addr.is_default), None)

    checkout_data = request.session.get('checkout', {})
    selected_address_id = checkout_data.get('address_id')
    active_address = None

    if selected_address_id:
        active_address = next(
            (addr for addr in user_addresses if addr.id == selected_address_id),
            None,
        )
        if not active_address and user_addresses:
            # Selected address no longer available; clear stale session state
            for key in ['address_id', 'shipping_method', 'shipping_cost', 'eta']:
                checkout_data.pop(key, None)
            request.session['checkout'] = checkout_data
            request.session.modified = True
            messages.warning(
                request,
                'Alamat aktif Anda sudah tidak tersedia. Silakan pilih alamat lain.',
            )

    if not active_address:
        active_address = default_address or (user_addresses[0] if user_addresses else None)

    districts = District.objects.filter(is_active=True).order_by('name')

    context = {
        'cart': cart,
        'selected_items': selected_items,
        'profile': profile,
        'user_addresses': user_addresses,
        'default_address': default_address,
        'active_address_id': active_address.id if active_address else None,
        'selected_shipping_method': checkout_data.get('shipping_method'),
        'districts': districts,
    }
    return render(request, 'core/checkout_address.html', context)


@login_required
def place_order(request):
    """Process order placement with shipping integration - only selected items"""
    if request.method != 'POST':
        return redirect('core:checkout')

    cart = get_object_or_404(Cart, user=request.user)

    # Get only selected items
    selected_items = cart.items.filter(is_selected=True)

    if not selected_items.exists():
        messages.error(request, 'Pilih minimal 1 item untuk checkout.')
        return redirect('core:cart')

    # Validate stock availability for selected items only
    for item in selected_items:
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
        # Use selected items total only
        subtotal = cart.get_selected_total()
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

    # Create order items and update stock - only for selected items
    for item in selected_items:
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

    # Clear only selected items from cart
    selected_items.delete()

    messages.success(request, f'Pesanan berhasil dibuat! Nomor pesanan: {order_number}')
    return redirect('core:order_detail', order_number=order_number)


@login_required
def place_order_from_address(request):
    """Place order from new multi-step checkout"""
    if request.method != 'POST':
        # Get data from POST or sessionStorage
        # For now, redirect to checkout
        return redirect('core:checkout')

    cart = get_object_or_404(Cart, user=request.user)

    # Get only selected items
    selected_items = cart.items.filter(is_selected=True)

    if not selected_items.exists():
        messages.error(request, 'Pilih minimal 1 item untuk checkout.')
        return redirect('core:cart')

    # Validate stock availability for selected items only
    for item in selected_items:
        if item.product.stock < item.quantity:
            messages.error(request, f'Stok {item.product.name} tidak mencukupi.')
            return redirect('core:cart')

    # Get shipping data from POST
    address_id = request.POST.get('address_id')
    service = request.POST.get('courier_service')

    try:
        # Get address
        address = get_object_or_404(Address, id=address_id, user=request.user)

        # Validate shipping data
        is_valid, error_message = validate_shipping_data(address.district.id, service)
        if not is_valid:
            messages.error(request, f'Data pengiriman tidak valid: {error_message}')
            return redirect('core:checkout')

        # Calculate shipping cost from database
        subtotal = cart.get_selected_total()
        shipping_cost, eta, district_name = calculate_shipping_cost(
            address.district.id, service, subtotal
        )

    except Exception as e:
        messages.error(request, f'Terjadi kesalahan: {str(e)}')
        return redirect('core:checkout')

    # Create order
    order_number = f'ORD-{uuid.uuid4().hex[:8].upper()}'

    order = Order.objects.create(
        user=request.user,
        order_number=order_number,
        full_name=address.full_name,
        email=request.user.email,
        phone=address.phone,
        address=address.get_full_address(),
        city=address.city,
        postal_code=address.postal_code,
        shipping_address=address,
        selected_courier=service,
        notes=request.POST.get('notes', ''),
        subtotal=subtotal,
        shipping_cost=shipping_cost,
        total=subtotal + shipping_cost,
    )

    # Create shipment record
    Shipment.objects.create(
        order=order,
        full_name=address.full_name,
        phone=address.phone,
        street=address.get_full_address(),
        district_name=district_name,
        postal_code=address.postal_code,
        service=service,
        cost=shipping_cost,
        eta=eta,
    )

    # Create order items and update stock - only for selected items
    for item in selected_items:
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

    # Clear only selected items from cart
    selected_items.delete()

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

    # Get all shipping addresses
    user_addresses = Address.objects.filter(user=request.user).select_related('district').order_by('-is_default', '-created_at')

    # Get all districts for the add address modal
    districts = District.objects.filter(is_active=True).order_by('name')

    context = {
        'profile': profile,
        'user': request.user,
        'user_addresses': user_addresses,
        'districts': districts,
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

        # Handle photo upload
        if request.FILES.get('photo'):
            # Delete old photo if exists
            if profile.photo:
                profile.photo.delete()
            profile.photo = request.FILES['photo']

        # Handle photo removal
        if request.POST.get('remove_photo') == '1':
            if profile.photo:
                profile.photo.delete()
                profile.photo = None

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
def change_password(request):
    """Change user password"""
    from django.contrib.auth import update_session_auth_hash

    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')

        # Check old password
        if not request.user.check_password(old_password):
            messages.error(request, 'Password lama salah.')
            return redirect('core:profile_settings')

        # Check if new passwords match
        if new_password1 != new_password2:
            messages.error(request, 'Password baru tidak cocok.')
            return redirect('core:profile_settings')

        # Check password length
        if len(new_password1) < 8:
            messages.error(request, 'Password baru minimal 8 karakter.')
            return redirect('core:profile_settings')

        # Update password
        request.user.set_password(new_password1)
        request.user.save()

        # Update session to prevent logout
        update_session_auth_hash(request, request.user)

        messages.success(request, 'Password berhasil diubah.')
        return redirect('core:profile_settings')

    return redirect('core:profile_settings')


@login_required
def profile_address_edit(request):
    """Edit primary shipping address for RajaOngkir integration"""
    addr = Address.objects.filter(user=request.user, is_default=True).first()
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
            obj.is_default = True
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

@login_required
@require_POST
def set_shipping_method(request):
    """
    Hitung biaya kirim berdasarkan alamat & metode pengiriman,
    lalu simpan hasilnya ke session checkout.
    """
    import json
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'success': False, 'message': 'Invalid JSON'}, status=400)

    method = str(data.get('method', '')).upper()
    address_id = data.get('address_id')

    if method not in {'REG', 'EXP'} or not address_id:
        return JsonResponse({'success': False, 'message': 'Metode atau alamat tidak valid.'}, status=400)

    try:
        address = Address.objects.select_related('district').get(
            id=address_id,
            user=request.user,
        )
    except Address.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Alamat tidak ditemukan.'}, status=404)

    district = address.district
    if not district or not district.is_active:
        return JsonResponse({'success': False, 'message': 'Kecamatan tidak aktif.'}, status=400)

    if method == 'EXP':
        shipping_cost = Decimal(district.exp_cost or 0)
        eta = district.eta_exp
    else:
        method = 'REG'
        shipping_cost = Decimal(district.reg_cost or 0)
        eta = district.eta_reg

    cart = Cart.objects.filter(user=request.user).first()
    subtotal = Decimal(cart.get_selected_total() if cart else 0)
    total = subtotal + shipping_cost

    checkout_data = request.session.get('checkout', {})
    checkout_data.update({
        'address_id': address.id,
        'shipping_method': method,
        'shipping_cost': float(shipping_cost),
        'eta': eta,
    })
    request.session['checkout'] = checkout_data
    request.session.modified = True

    def format_rupiah(value: Decimal) -> str:
        value = Decimal(value or 0)
        return f"Rp {number_format(value, decimal_pos=0, force_grouping=True)}"

    return JsonResponse({
        'success': True,
        'method': method,
        'shipping_cost': float(shipping_cost),
        'subtotal': float(subtotal),
        'total': float(total),
        'eta': eta,
        'shipping_cost_display': format_rupiah(shipping_cost),
        'subtotal_display': format_rupiah(subtotal),
        'total_display': format_rupiah(total),
    })