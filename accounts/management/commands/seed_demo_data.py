from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from category.models import Category
from customer.models import Customer
from product.models import Product, Alert
from supplier.models import Supplier

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed the database with basic demo data for the inventory app.'

    def handle(self, *args, **options):
        User.objects.filter(username='admin').delete()
        User.objects.filter(username='manager').delete()
        User.objects.filter(username='cashier').delete()

        admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='Admin123!',
            role='admin',
            is_approved=True,
            is_staff=True,
            is_superuser=True,
        )
        manager = User.objects.create_user(
            username='manager',
            email='manager@example.com',
            password='Manager123!',
            role='manager',
            is_approved=True,
        )
        cashier = User.objects.create_user(
            username='cashier',
            email='cashier@example.com',
            password='Cashier123!',
            role='cashier',
            is_approved=True,
        )

        category = Category.objects.create(name='Hardware', description='Hardware tools')
        supplier = Supplier.objects.create(
            name='Demo Supplier',
            contact_person='Jane Supplier',
            email='supplier@example.com',
            phone='5551234',
            address='123 Demo Street',
            city='Manila',
            postal_code='1000',
            country='Philippines',
        )
        customer = Customer.objects.create(
            name='Walk-in Customer',
            email='customer@example.com',
            phone='5559876',
            address='456 Demo Avenue',
        )
        product = Product.objects.create(
            name='Hammer',
            description='Standard hammer',
            category=category,
            sku='SKU-DEM-001',
            unit_price=Decimal('25.00'),
            quantity_in_stock=5,
            reorder_level=2,
            is_active=True,
        )
        product.create_alerts()

        self.stdout.write(self.style.SUCCESS('Demo data seeded successfully.'))
