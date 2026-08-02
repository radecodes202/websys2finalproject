from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from decimal import Decimal
import random
from datetime import date, timedelta

from accounts.models import User
from category.models import Category
from product.models import Product, Alert
from supplier.models import Supplier, SupplierPayment
from customer.models import Customer
from product.models import PurchaseOrder, PurchaseOrderItem, StockReceipt, StockReceiptItem
from product.models import Sale, SaleItem, Payment


class Command(BaseCommand):
    help = 'Seed the database with demo data for testing and demonstration'

    def handle(self, *args, **options):
        self.stdout.write('Seeding demo data...')

        # Create demo users
        self.create_demo_users()

        # Create sample categories
        self.create_categories()

        # Create sample suppliers
        self.create_suppliers()

        # Create sample products
        self.create_products()

        # Create sample customers
        self.create_customers()

        # Create sample purchase orders and stock receipts
        self.create_purchase_orders()

        # Create sample sales
        self.create_sales()

        self.stdout.write(
            self.style.SUCCESS('Successfully seeded demo data!')
        )

    def create_demo_users(self):
        """Create demo users with specified roles and passwords"""
        User = get_user_model()

        demo_users = [
            {
                'username': 'admin',
                'email': 'admin@example.com',
                'role': 'admin',
                'password': 'Admin123!',
                'is_staff': True,
                'is_superuser': True,
                'is_approved': True,
            },
            {
                'username': 'manager',
                'email': 'manager@example.com',
                'role': 'manager',
                'password': 'Manager123!',
                'is_staff': True,
                'is_approved': True,
            },
            {
                'username': 'cashier',
                'email': 'cashier@example.com',
                'role': 'cashier',
                'password': 'Cashier123!',
                'is_approved': True,
            },
            {
                'username': 'inventory_staff',
                'email': 'inventory@example.com',
                'role': 'inventory_staff',
                'password': 'Staff123!',
                'is_approved': True,
            }
        ]

        for user_data in demo_users:
            password = user_data.pop('password')
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults=user_data
            )
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(f'Created user: {user.username}')
            else:
                # Update password if user exists
                user.set_password(password)
                user.save()
                self.stdout.write(f'Updated user: {user.username}')

    def create_categories(self):
        """Create sample categories"""
        categories_data = [
            {'name': 'Electronics', 'description': 'Electronic devices and gadgets'},
            {'name': 'Clothing', 'description': 'Apparel and fashion items'},
            {'name': 'Groceries', 'description': 'Food and beverage items'},
            {'name': 'Office Supplies', 'description': 'Stationery and office equipment'},
            {'name': 'Hardware', 'description': 'Tools and building materials'},
        ]

        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults=cat_data
            )
            if created:
                self.stdout.write(f'Created category: {category.name}')

    def create_suppliers(self):
        """Create sample suppliers"""
        suppliers_data = [
            {
                'name': 'TechSupply Inc.',
                'contact_person': 'John Smith',
                'email': 'john@techsupply.com',
                'phone': '555-0101',
                'address': '123 Tech Avenue',
                'city': 'San Francisco',
                'postal_code': '94105',
                'country': 'USA',
            },
            {
                'name': 'FashionWholesale Ltd.',
                'contact_person': 'Maria Garcia',
                'email': 'maria@fashionwholesale.com',
                'phone': '555-0102',
                'address': '456 Style Boulevard',
                'city': 'New York',
                'postal_code': '10001',
                'country': 'USA',
            },
            {
                'name': 'FreshFoods Distribution',
                'contact_person': 'David Chen',
                'email': 'david@freshfoods.com',
                'phone': '555-0103',
                'address': '789 Fresh Market',
                'city': 'Los Angeles',
                'postal_code': '90001',
                'country': 'USA',
            },
            {
                'name': 'OfficeDepot Supplies',
                'contact_person': 'Sarah Johnson',
                'email': 'sarah@officedepot.com',
                'phone': '555-0104',
                'address': '321 Office Park',
                'city': 'Chicago',
                'postal_code': '60601',
                'country': 'USA',
            }
        ]

        for sup_data in suppliers_data:
            supplier, created = Supplier.objects.get_or_create(
                name=sup_data['name'],
                defaults=sup_data
            )
            if created:
                self.stdout.write(f'Created supplier: {supplier.name}')

    def create_products(self):
        """Create sample products"""
        categories = list(Category.objects.all())
        suppliers = list(Supplier.objects.all())

        if not categories or not suppliers:
            self.stdout.write(self.style.WARNING('Categories or suppliers not found. Skipping products.'))
            return

        products_data = [
            {
                'name': 'Smartphone X1',
                'description': 'Latest generation smartphone with advanced features',
                'sku': 'SM-X1-001',
                'barcode': '1234567890123',
                'unit_price': Decimal('699.99'),
                'cost_price': Decimal('450.00'),
                'quantity_in_stock': 50,
                'reorder_level': 10,
                'unit_of_measure': 'pcs',
            },
            {
                'name': 'Laptop Pro 15"',
                'description': 'High-performance laptop for professionals',
                'sku': 'LP-PRO-001',
                'barcode': '1234567890124',
                'unit_price': Decimal('1299.99'),
                'cost_price': Decimal('850.00'),
                'quantity_in_stock': 30,
                'reorder_level': 5,
                'unit_of_measure': 'pcs',
            },
            {
                'name': 'Cotton T-Shirt',
                'description': 'Comfortable 100% cotton t-shirt',
                'sku': 'TS-CT-001',
                'barcode': '1234567890125',
                'unit_price': Decimal('19.99'),
                'cost_price': Decimal('8.00'),
                'quantity_in_stock': 100,
                'reorder_level': 20,
                'unit_of_measure': 'pcs',
            },
            {
                'name': 'Organic Apples',
                'description': 'Fresh organic apples from local farms',
                'sku': 'OA-001',
                'barcode': '1234567890126',
                'unit_price': Decimal('3.99'),
                'cost_price': Decimal('1.50'),
                'quantity_in_stock': 200,
                'reorder_level': 30,
                'unit_of_measure': 'lb',
                'expiration_date': date.today() + timedelta(days=7),
            },
            {
                'name': 'Wireless Mouse',
                'description': 'Ergonomic wireless mouse with long battery life',
                'sku': 'WM-BT-001',
                'barcode': '1234567890127',
                'unit_price': Decimal('29.99'),
                'cost_price': Decimal('12.00'),
                'quantity_in_stock': 75,
                'reorder_level': 15,
                'unit_of_measure': 'pcs',
            },
            {
                'name': 'A4 Paper (500 sheets)',
                'description': 'High-quality A4 paper for printing',
                'sku': 'PA-A4-001',
                'barcode': '1234567890128',
                'unit_price': Decimal('5.99'),
                'cost_price': Decimal('2.00'),
                'quantity_in_stock': 150,
                'reorder_level': 25,
                'unit_of_measure': 'box',
            },
            {
                'name': 'Bluetooth Speaker',
                'description': 'Portable Bluetooth speaker with superior sound quality',
                'sku': 'BS-BT-001',
                'barcode': '1234567890129',
                'unit_price': Decimal('79.99'),
                'cost_price': Decimal('35.00'),
                'quantity_in_stock': 40,
                'reorder_level': 8,
                'unit_of_measure': 'pcs',
            }
        ]

        for prod_data in products_data:
            # Assign random category and supplier
            prod_data['category'] = random.choice(categories)
            prod_data['preferred_supplier'] = random.choice(suppliers) if suppliers else None

            product, created = Product.objects.get_or_create(
                sku=prod_data['sku'],
                defaults=prod_data
            )
            if created:
                # Create alerts for the product
                product.create_alerts()
                self.stdout.write(f'Created product: {product.name}')
            else:
                self.stdout.write(f'Product already exists: {product.name}')

    def create_customers(self):
        """Create sample customers"""
        customers_data = [
            {
                'name': 'John Doe',
                'email': 'john.doe@email.com',
                'phone': '555-1001',
                'address': '123 Main Street',
                'city': 'Anytown',
                'postal_code': '12345',
                'country': 'USA',
            },
            {
                'name': 'Jane Smith',
                'email': 'jane.smith@email.com',
                'phone': '555-1002',
                'address': '456 Oak Avenue',
                'city': 'Somewhere',
                'postal_code': '67890',
                'country': 'USA',
            },
            {
                'name': 'Bob Johnson',
                'email': 'bob.johnson@email.com',
                'phone': '555-1003',
                'address': '789 Pine Road',
                'city': 'Elsewhere',
                'postal_code': '54321',
                'country': 'USA',
            }
        ]

        for cust_data in customers_data:
            customer, created = Customer.objects.get_or_create(
                email=cust_data['email'],
                defaults=cust_data
            )
            if created:
                self.stdout.write(f'Created customer: {customer.name}')

    def create_purchase_orders(self):
        """Create sample purchase orders and stock receipts"""
        suppliers = list(Supplier.objects.all())
        products = list(Product.objects.all())
        users = list(User.objects.filter(is_approved=True))

        if not suppliers or not products or not users:
            self.stdout.write(self.style.WARNING('Missing dependencies for purchase orders.'))
            return

        # Create 3 purchase orders
        for i in range(3):
            supplier = random.choice(suppliers)
            created_by = random.choice(users)

            po = PurchaseOrder.objects.create(
                supplier=supplier,
                expected_delivery_date=date.today() + timedelta(days=random.randint(5, 15)),
                created_by=created_by
            )

            # Add 2-4 items to each PO
            num_items = random.randint(2, 4)
            selected_products = random.sample(products, min(num_items, len(products)))

            for product in selected_products:
                quantity = random.randint(10, 50)
                unit_cost = product.cost_price * Decimal(str(random.uniform(0.9, 1.1)))  # Slight variance

                PurchaseOrderItem.objects.create(
                    purchase_order=po,
                    product=product,
                    quantity_ordered=quantity,
                    unit_cost=unit_cost.quantize(Decimal('0.01'))
                )

            self.stdout.write(f'Created Purchase Order: {po}')

            # Create stock receipt for this PO (simulate receiving goods)
            if random.choice([True, False]):  # 50% chance of having received stock
                receipt = StockReceipt.objects.create(
                    purchase_order=po,
                    received_by=random.choice(users)
                )

                # Receive quantities for each item
                for item in po.items.all():
                    # Receive 80-100% of ordered quantity
                    received_qty = random.randint(int(item.quantity_ordered * 0.8), item.quantity_ordered)

                    StockReceiptItem.objects.create(
                        stock_receipt=receipt,
                        purchase_order_item=item,
                        quantity_received=received_qty
                    )

                # Process the receipt to update stock and status
                receipt.receive()
                self.stdout.write(f'Created and processed Stock Receipt for: {po}')

    def create_sales(self):
        """Create sample sales"""
        products = list(Product.objects.all())
        users = list(User.objects.filter(role__in=['cashier', 'admin', 'manager']))
        customers = list(Customer.objects.all())

        if not products or not users:
            self.stdout.write(self.style.WARNING('Missing dependencies for sales.'))
            return

        # Create 5-10 sales over the past week
        for i in range(random.randint(5, 10)):
            cashier = random.choice(users)
            customer = random.choice(customers) if customers and random.choice([True, False]) else None

            # Create sale with random date in the past week
            days_ago = random.randint(0, 6)
            sale_date = date.today() - timedelta(days=days_ago)

            sale = Sale.objects.create(
                cashier=cashier,
                customer=customer,
                payment_method=random.choice(['cash', 'card', 'gcash']),
                date=sale_date
            )

            # Add 1-5 items to each sale
            num_items = random.randint(1, min(5, len(products)))
            selected_products = random.sample(products, num_items)

            total = Decimal('0.00')
            for product in selected_products:
                quantity = random.randint(1, min(5, product.quantity_in_stock + 10))  # Allow some oversell for demo
                unit_price = product.unit_price * Decimal(str(random.uniform(0.9, 1.1)))  # Slight variance

                SaleItem.objects.create(
                    sale=sale,
                    product=product,
                    quantity=quantity,
                    unit_price=unit_price.quantize(Decimal('0.01')),
                    subtotal=(unit_price * quantity).quantize(Decimal('0.01'))
                )

                total += (unit_price * quantity)

            # Calculate tax and discount
            tax = total * Decimal('0.08')  # 8% tax
            discount = total * Decimal('0.05') if random.choice([True, False]) else Decimal('0.00')  # 5% discount sometimes

            sale.subtotal = total
            sale.tax = tax.quantize(Decimal('0.01'))
            sale.discount = discount.quantize(Decimal('0.01'))
            sale.total = (total + tax - discount).quantize(Decimal('0.01'))
            sale.status = 'completed'
            sale.save()

            # Complete checkout to deduct stock and create payments
            try:
                sale.complete_checkout()

                # Create payment for the sale
                Payment.objects.create(
                    sale=sale,
                    amount=sale.total,
                    method=sale.payment_method,
                    reference_number=f'PAY-{sale.id:06d}',
                    change_given=Decimal('0.00')
                )

                self.stdout.write(f'Created sale: {sale} with total: ${sale.total}')
            except ValueError as e:
                # If insufficient stock, just skip this sale
                self.stdout.write(f'Skipped sale due to insufficient stock: {e}')
                sale.delete()