from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.urls import reverse
from django.core.mail import send_mail  
import base64
from django.contrib.auth.decorators import login_required
from .models import Product, Cart, CartItem, Order, OrderItem
from django.db import IntegrityError
from django.core.paginator import Paginator
import time
from django.utils.http import urlencode

User = get_user_model()

# initial simple home removed; later `home` renders products

@login_required(login_url='login')
def order(request):
    """Show orders placed by the logged-in user with their items and timestamps."""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'order.html', {'orders': orders})

@login_required(login_url='login')
def sell(request):
    return render(request, "sell.html")


def mobiles(request):
    """Render the mobiles listing page stored at templates/items/mobiles.html."""
    product_list = Product.objects.all().order_by('-id')
    # paginate - 6 per page
    paginator = Paginator(product_list, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'items/mobiles.html', {'products': page_obj})

def signup(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        password = request.POST.get("password")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered!")
            return redirect("signup")
        
        if User.objects.filter(phone=phone).exists():
            messages.error(request, "Phone number already registered!")
            return redirect("signup")

        User.objects.create_user(
            email=email,
            username=username,
            phone=phone,
            password=password
        )
        messages.success(request, "Account created successfully! Please login.")
        return redirect("login")

    return render(request, "signup.html")

def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        # Check if email exists
        if not User.objects.filter(email=email).exists():
            messages.error(request, "No account found. Please signup first.")
            return redirect("login")

        # pass email as `username` so Django's authentication backend looks up by USERNAME_FIELD
        user = authenticate(request, username=email, password=password)

        if user:
            login(request, user)

            # Merge any anonymous session cart into the user's DB cart
            try:
                session_cart = request.session.get('cart', [])
                if session_cart:
                    cart_obj, _ = Cart.objects.get_or_create(user=user)
                    for pid in session_cart:
                        try:
                            ci, created = CartItem.objects.get_or_create(cart=cart_obj, product_id=int(pid))
                            if not created:
                                ci.quantity = ci.quantity + 1
                                ci.save()
                        except IntegrityError:
                            # skip malformed product ids
                            continue
                    # clear session cart after merging
                    try:
                        del request.session['cart']
                    except KeyError:
                        pass
            except Exception:
                # don't break login flow if merging fails
                pass

            # Handle redirect to 'next' page
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)

            return redirect("home")  # Default home page
        else:
            messages.error(request, "Incorrect password!")
            return redirect("login")

    return render(request, "login.html")


def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect("home")

def forgot_password(request):
    if request.method == "POST":
        phone = request.POST.get("phone")

        # user model must have phone field
        try:
            user = User.objects.get(username=phone)   # if phone is username
        except Exception:
            messages.error(request, "Mobile number not found!")
            return redirect("forgot_password")

        uid = base64.urlsafe_b64encode(str(user.id).encode()).decode()

        link = request.build_absolute_uri(reverse("reset_password", args=[uid]))

        # For now, print link in console (Free method)
        print("Password Reset Link:", link)

        messages.success(
            request,
            "Reset link sent! Check your console (or send via SMS API later)."
        )
        return redirect("forgot_password")

    return render(request, "forgot_password.html")


def reset_password(request, uid):
    try:
        user_id = int(base64.urlsafe_b64decode(uid).decode())
        user = User.objects.get(id=user_id)
    except Exception:
        messages.error(request, "Invalid or expired link.")
        return redirect("forgot_password")

    if request.method == "POST":
        newpass = request.POST.get("password")
        user.password = make_password(newpass)
        user.save()

        messages.success(request, "Password updated! You can now log in.")
        return redirect("login")

    return render(request, "reset_password.html", {"user": user})


def home(request):
    products = Product.objects.all()
    return render(request, "home.html", {"products": products})

def product_detail(request, id):
    product = get_object_or_404(Product, id=id)
    return render(request, "product_detail.html", {"product": product})


def search(request):
    """Search for a product by name. If found, redirect to that product's Buy Now page.

    If multiple matches exist, redirect to the first match. If none found, show an error and
    redirect back to the mobiles listing.
    """
    q = request.GET.get('q', '') or ''
    q = q.strip()
    if not q:
        messages.error(request, "Please enter a search term.")
        return redirect('mobiles')

    matches = Product.objects.filter(name__icontains=q)
    if matches.exists():
        p = matches.first()
        # Prefer showing the product image passed to buy page
        img = ''
        try:
            if p.image:
                img = p.image.url
        except Exception:
            img = ''

        if img:
            return redirect(f"{reverse('buy_now', args=[p.id])}?img={img}")
        return redirect('buy_now', p.id)

    messages.error(request, "Item is not there")
    return redirect('mobiles')

def add_to_cart(request, id):
    """Add product id to session cart (allows duplicates for quantity).

    Uses session key 'cart' which stores a list of product ids.
    Redirects to the cart page.
    """
    # read optional overrides from query params
    q_name = request.GET.get('name')
    q_price = request.GET.get('price')
    q_img = request.GET.get('img')

    if request.user.is_authenticated:
        # persist in DB cart
        cart_obj, _ = Cart.objects.get_or_create(user=request.user)
        ci, created = CartItem.objects.get_or_create(cart=cart_obj, product_id=int(id))
        if not created:
            ci.quantity += 1
            ci.save()

        # store any display overrides in session so cart view can pick them up
        if q_name or q_price or q_img:
            overrides = request.session.get('overrides', {})
            overrides[str(id)] = {}
            if q_name:
                overrides[str(id)]['name'] = q_name
            if q_price:
                try:
                    overrides[str(id)]['price'] = int(q_price)
                except Exception:
                    overrides[str(id)]['price'] = q_price
            if q_img:
                overrides[str(id)]['img'] = q_img
            request.session['overrides'] = overrides

        messages.success(request, "Product added to your cart.")
        return redirect('cart')

    # anonymous session cart: store list of entries (either int product_id or dict with overrides)
    cart = request.session.get("cart", [])
    entry = {'product_id': int(id)}
    if q_name:
        entry['name'] = q_name
    if q_price:
        try:
            entry['price'] = int(q_price)
        except Exception:
            entry['price'] = q_price
    if q_img:
        entry['img'] = q_img

    cart.append(entry)
    request.session["cart"] = cart
    messages.success(request, "Product added to cart.")
    return redirect("cart")


def cart(request):
    """Render a Bootstrap cart page showing products, quantities and totals.

    The session 'cart' contains a list of product ids; duplicates indicate quantity.
    """
    if request.user.is_authenticated:
        # load from DB
        cart_obj = None
        try:
            cart_obj = request.user.cart
        except Cart.DoesNotExist:
            cart_obj = None

        cart_items = []
        total = 0
        if cart_obj:
            items = cart_obj.items.select_related('product').all()
            overrides = request.session.get('overrides', {})
            for it in items:
                # apply override price/name/img if present in session
                override = overrides.get(str(it.product.id), {})
                display_price = override.get('price') if override.get('price') is not None else it.product.price
                subtotal = int(display_price) * it.quantity
                total += subtotal
                # create a lightweight display product with override fields
                display_product = it.product
                display_product.display_name = override.get('name', it.product.name)
                display_product.display_img = override.get('img', getattr(it.product.image, 'url', ''))
                display_product.display_price = display_price
                cart_items.append({"product": display_product, "quantity": it.quantity, "subtotal": subtotal})

        return render(request, "cart.html", {"cart_items": cart_items, "total": total})

    # anonymous session cart
    # anonymous session cart may contain dict entries with overrides
    cart_entries = request.session.get("cart", [])
    counts = {}
    overrides = {}
    for e in cart_entries:
        if isinstance(e, dict):
            pid = int(e.get('product_id'))
            counts[pid] = counts.get(pid, 0) + 1
            # prefer last override for that product id
            overrides[pid] = {}
            if 'name' in e:
                overrides[pid]['name'] = e['name']
            if 'price' in e:
                overrides[pid]['price'] = e['price']
            if 'img' in e:
                overrides[pid]['img'] = e['img']
        else:
            try:
                pid = int(e)
                counts[pid] = counts.get(pid, 0) + 1
            except Exception:
                continue

    products = Product.objects.filter(id__in=counts.keys()) if counts else Product.objects.none()

    cart_items = []
    total = 0
    for p in products:
        qty = counts.get(p.id, 0)
        override = overrides.get(p.id, {})
        display_price = override.get('price') if override.get('price') is not None else p.price
        subtotal = int(display_price) * qty
        total += subtotal
        # set display fields on the product for template use
        p.display_name = override.get('name', p.name)
        p.display_img = override.get('img', getattr(p.image, 'url', ''))
        p.display_price = display_price
        cart_items.append({"product": p, "quantity": qty, "subtotal": subtotal})

    return render(request, "cart.html", {"cart_items": cart_items, "total": total})


def remove_from_cart(request, id):
    """Remove one occurrence of product id from session cart or from DB cart if authenticated."""
    if request.user.is_authenticated:
        try:
            cart_obj = request.user.cart
        except Cart.DoesNotExist:
            cart_obj = None

        if cart_obj:
            try:
                ci = CartItem.objects.get(cart=cart_obj, product_id=int(id))
                if ci.quantity > 1:
                    ci.quantity -= 1
                    ci.save()
                else:
                    ci.delete()
                messages.success(request, "Item removed from your cart.")
            except CartItem.DoesNotExist:
                messages.error(request, "Item not found in your cart.")

        return redirect('cart')

    cart = request.session.get("cart", [])
    removed = False
    # cart entries may be ints or dicts
    for i, e in enumerate(cart):
        if isinstance(e, dict):
            if int(e.get('product_id')) == int(id):
                cart.pop(i)
                removed = True
                break
        else:
            try:
                if int(e) == int(id):
                    cart.pop(i)
                    removed = True
                    break
            except Exception:
                continue

    if removed:
        request.session["cart"] = cart
        messages.success(request, "Item removed from cart.")
    else:
        messages.error(request, "Item not found in cart.")

    return redirect("cart")

def buy_now(request, id):
    # store the product id being purchased and show a dedicated Buy Now page
    request.session["buy_id"] = int(id)
    product = get_object_or_404(Product, id=id)
    # derive display fields from query params if provided so the template is simple
    display_name = request.GET.get('name') or product.name
    display_price = request.GET.get('price')
    try:
        display_price = int(display_price) if display_price is not None else product.price
    except Exception:
        display_price = product.price

    display_img = request.GET.get('img') or (product.image.url if product.image else '')

    return render(request, 'buy_now.html', {
        'product': product,
        'display_name': display_name,
        'display_price': display_price,
        'display_img': display_img,
    })

def address(request):
    # If user came from Buy Now, show the product and amount on the address page
    buy_id = request.session.get('buy_id')
    product = None
    if buy_id:
        try:
            product = Product.objects.get(id=buy_id)
        except Product.DoesNotExist:
            product = None
    # allow display overrides via query params (name/price)
    display_name = request.GET.get('name') if request.GET.get('name') else (product.name if product else None)
    display_price = request.GET.get('price') if request.GET.get('price') else (product.price if product else None)
    return render(request, "add_details.html", {"product": product, "display_name": display_name, "display_price": display_price})


def place_order(request):
    # User reaches here after entering address/pincode and clicking Place Order
    if request.method != 'POST':
        return redirect('address')

    buy_id = request.session.get('buy_id')
    if not buy_id:
        # nothing to buy
        messages.error(request, 'Nothing to buy. Please select a product first.')
        return redirect('mobiles')
    # Create a persistent Order and OrderItem
    product = get_object_or_404(Product, id=buy_id)

    order_id = str(int(time.time()))
    name = request.POST.get('name', '')
    address = request.POST.get('address', '')
    pincode = request.POST.get('pincode', '')
    # if the checkout passed a display_price (from mobiles/buy flow), prefer it
    display_price = request.POST.get('display_price')
    try:
        if display_price is not None:
            display_price = int(display_price)
    except Exception:
        display_price = None

    order = Order.objects.create(
        order_id=order_id,
        user=request.user if request.user.is_authenticated else None,
        name=name,
        address=address,
        pincode=pincode,
        total=display_price if display_price is not None else product.price,
    )

    OrderItem.objects.create(
        order=order,
        product=product,
        quantity=1,
        price=display_price if display_price is not None else product.price,
    )

    # Store minimal last order info in session for backward compatibility
    request.session['last_order'] = {'order_id': order.order_id, 'product_id': buy_id}

    return redirect('order_qr', order_id=order.order_id)


def order_qr(request, order_id):
    # Build a URL that the QR will point to; scanning it will open a thank-you page.
    thanks_url = request.build_absolute_uri(reverse('thanks'))
    # include order id as query string
    full_url = f"{thanks_url}?{urlencode({'order': order_id})}"

    # Use a public QR generator (no server-side dependency required)
    qr_src = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={full_url}"
    return render(request, 'order_qr.html', {'qr_src': qr_src, 'order_id': order_id})


def thanks(request):
    order_id = request.GET.get('order')
    return render(request, 'thanks.html', {'order_id': order_id})

def qr_scanner(request):
    return render(request, "qr_scanner.html")

def qr_result(request):
    data = request.GET.get("data", "")
    return render(request, "qr_result.html", {"data": data})

