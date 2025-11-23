import os
import shutil
import django
from mycart.models import Product
from django.conf import settings
import sys

# Setup Django environment
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myshop.settings')
sys.path.insert(0, project_path)
django.setup()


# Ensure media products dir exists
media_products_dir = os.path.join(settings.BASE_DIR, 'media', 'products')
os.makedirs(media_products_dir, exist_ok=True)

# Static images to copy (source -> dest name)
static_dir = os.path.join(settings.BASE_DIR, 'static', 'phones')
sources = [
    ('mobilesfront.png', 'mobilesfront.png'),
    ('s24 snap.jpg', 's24_snap.jpg'),
]

created = []
for src_name, dest_name in sources:
    src = os.path.join(static_dir, src_name)
    dest = os.path.join(media_products_dir, dest_name)
    if os.path.exists(src):
        shutil.copyfile(src, dest)
        print(f'Copied {src} -> {dest}')
        # Create product entry
        # image field stores path relative to MEDIA_ROOT
        image_field_path = f'products/{dest_name}'
        prod_name = dest_name.replace('_', ' ').rsplit('.', 1)[0]
        p = Product.objects.create(
            name=prod_name.title(),
            price=9999,
            old_price=12999,
            image=image_field_path,
            description='Sample product created by seed script.'
        )
        created.append(p)
    else:
        print(f'Source not found: {src}')

print('Created products:', [p.id for p in created])
print('Done.')
