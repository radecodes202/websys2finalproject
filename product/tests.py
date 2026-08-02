from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from category.models import Category
from product.models import (
    Alert,
    Product,
    PurchaseOrder,
    PurchaseOrderItem,
    Sale,
    SaleItem,
    Payment,
    StockMovement,
    StockReceipt,
    StockReceiptItem,
)
from supplier.models import Supplier

User = get_user_model()


class ProductReceivingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='admin_user',
            email='admin@example.com',
            password='StrongPass123',
            role='admin',
            is_approved=True,
        )
        self.category = Category.objects.create(name='Hardware', description='Hardware supplies')
        self.supplier = Supplier.objects.create(
            name='Acme Supplies',
            contact_person='Jane Doe',
            email='supplier@example.com',
            phone='123456789',
            address='123 Main St',
            city='Manila',
            postal_code='1000',
            country='Philippines',
        )
        self.product = Product.objects.create(
            name='Hammer',
            description='Standard hammer',
            category=self.category,
            sku='SKU-001',
            unit_price=Decimal('25.00'),
            quantity_in_stock=0,
            reorder_level=2,
            is_active=True,
        )

    def test_stock_receipt_increases_inventory_and_creates_stock_movement(self):
        purchase_order = PurchaseOrder.objects.create(
            supplier=self.supplier,
            expected_delivery_date=timezone.now().date(),
            status='pending',
            created_by=self.user,
        )
        purchase_order_item = PurchaseOrderItem.objects.create(
            purchase_order=purchase_order,
            product=self.product,
            quantity_ordered=5,
            unit_cost=Decimal('18.00'),
        )

        stock_receipt = StockReceipt.objects.create(
            purchase_order=purchase_order,
            received_by=self.user,
        )
        StockReceiptItem.objects.create(
            stock_receipt=stock_receipt,
            purchase_order_item=purchase_order_item,
            quantity_received=3,
        )

        stock_receipt.receive()

        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity_in_stock, 3)
        self.assertTrue(StockMovement.objects.filter(product=self.product, type='purchase').exists())
        self.assertEqual(purchase_order.status, 'partial')

    def test_stock_receipt_marks_purchase_order_received_when_all_items_are_received(self):
        purchase_order = PurchaseOrder.objects.create(
            supplier=self.supplier,
            expected_delivery_date=timezone.now().date(),
            status='pending',
            created_by=self.user,
        )
        purchase_order_item = PurchaseOrderItem.objects.create(
            purchase_order=purchase_order,
            product=self.product,
            quantity_ordered=3,
            unit_cost=Decimal('18.00'),
        )

        stock_receipt = StockReceipt.objects.create(
            purchase_order=purchase_order,
            received_by=self.user,
        )
        StockReceiptItem.objects.create(
            stock_receipt=stock_receipt,
            purchase_order_item=purchase_order_item,
            quantity_received=3,
        )

        stock_receipt.receive()

        purchase_order.refresh_from_db()
        self.assertEqual(purchase_order.status, 'received')


class SaleCheckoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='cashier_user',
            email='cashier@example.com',
            password='StrongPass123',
            role='cashier',
            is_approved=True,
        )
        self.category = Category.objects.create(name='Hardware', description='Hardware supplies')
        self.product = Product.objects.create(
            name='Hammer',
            description='Standard hammer',
            category=self.category,
            sku='SKU-002',
            unit_price=Decimal('25.00'),
            quantity_in_stock=10,
            reorder_level=2,
            is_active=True,
        )
        self.client.force_login(self.user)

    def test_sale_completion_deducts_stock_and_creates_sale_movement(self):
        sale = Sale.objects.create(
            cashier=self.user,
            payment_method='cash',
            subtotal=Decimal('75.00'),
            tax=Decimal('0.00'),
            discount=Decimal('0.00'),
            total=Decimal('75.00'),
            status='pending',
        )
        SaleItem.objects.create(
            sale=sale,
            product=self.product,
            quantity=3,
            unit_price=Decimal('25.00'),
            subtotal=Decimal('75.00'),
        )
        Payment.objects.create(
            sale=sale,
            amount=Decimal('75.00'),
            method='cash',
            reference_number='RCPT-001',
            change_given=Decimal('0.00'),
        )

        sale.complete_checkout()

        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity_in_stock, 7)
        self.assertTrue(StockMovement.objects.filter(product=self.product, type='sale').exists())

    def test_checkout_failure_rolls_back_stock_and_status_changes(self):
        sale = Sale.objects.create(
            cashier=self.user,
            payment_method='cash',
            subtotal=Decimal('25.00'),
            tax=Decimal('0.00'),
            discount=Decimal('0.00'),
            total=Decimal('25.00'),
            status='pending',
        )
        SaleItem.objects.create(
            sale=sale,
            product=self.product,
            quantity=3,
            unit_price=Decimal('25.00'),
            subtotal=Decimal('75.00'),
        )
        Payment.objects.create(
            sale=sale,
            amount=Decimal('25.00'),
            method='cash',
            reference_number='RCPT-002',
            change_given=Decimal('0.00'),
        )

        with patch('product.models.StockMovement.objects.create', side_effect=RuntimeError('boom')):
            with self.assertRaises(RuntimeError):
                sale.complete_checkout()

        self.product.refresh_from_db()
        sale.refresh_from_db()
        self.assertEqual(self.product.quantity_in_stock, 10)
        self.assertEqual(sale.status, 'pending')
        self.assertFalse(StockMovement.objects.exists())


class POSCheckoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='cashier_user',
            email='cashier@example.com',
            password='StrongPass123',
            role='cashier',
            is_approved=True,
        )
        self.category = Category.objects.create(name='Hardware', description='Hardware supplies')
        self.product = Product.objects.create(
            name='Hammer',
            description='Standard hammer',
            category=self.category,
            sku='SKU-004',
            unit_price=Decimal('25.00'),
            quantity_in_stock=10,
            reorder_level=2,
            is_active=True,
        )
        self.client.force_login(self.user)

    def test_pos_page_renders_for_cashier(self):
        response = self.client.get(reverse('product:pos'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hammer')

    def test_pos_checkout_creates_sale_and_receipt(self):
        add_response = self.client.post(reverse('product:pos'), {
            'action': 'add_to_cart',
            'product_id': self.product.pk,
            'quantity': 2,
        })
        self.assertEqual(add_response.status_code, 302)

        checkout_response = self.client.post(reverse('product:pos'), {
            'action': 'checkout',
            'payment_method': 'cash',
            'amount_tendered': '60.00',
            'discount': '0.00',
        })
        self.assertEqual(checkout_response.status_code, 302)

        sale = Sale.objects.get(status='completed')
        self.assertEqual(sale.items.count(), 1)
        self.assertEqual(sale.payments.count(), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity_in_stock, 8)

        receipt_response = self.client.get(reverse('product:receipt', args=[sale.pk]))
        self.assertEqual(receipt_response.status_code, 200)
        self.assertContains(receipt_response, 'Receipt')


class AlertTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='manager_user',
            email='manager@example.com',
            password='StrongPass123',
            role='manager',
            is_approved=True,
        )
        self.category = Category.objects.create(name='Hardware', description='Hardware supplies')
        self.product = Product.objects.create(
            name='Hammer',
            description='Standard hammer',
            category=self.category,
            sku='SKU-003',
            unit_price=Decimal('25.00'),
            quantity_in_stock=1,
            reorder_level=2,
            is_active=True,
        )
        self.client.force_login(self.user)

    def test_low_stock_and_expiration_alerts_are_created(self):
        self.product.expiration_date = timezone.now().date() + timedelta(days=5)
        self.product.save(update_fields=['expiration_date'])

        self.product.create_alerts()

        self.assertTrue(Alert.objects.filter(product=self.product, type='low_stock').exists())
        self.assertTrue(Alert.objects.filter(product=self.product, type='expiring').exists())


class ProductCRUDTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='admin_user',
            email='admin@example.com',
            password='StrongPass123',
            role='admin',
            is_approved=True,
        )
        self.category = Category.objects.create(name='Hardware', description='Hardware supplies')
        self.client.force_login(self.user)

    def test_product_create_and_list(self):
        create_response = self.client.post(
            reverse('product:product-create'),
            {
                'name': 'Hammer',
                'description': 'Standard hammer',
                'category': self.category.pk,
                'sku': 'SKU-001',
                'unit_price': '25.00',
                'quantity_in_stock': 10,
                'reorder_level': 2,
                'is_active': True,
            },
            follow=True,
        )

        self.assertEqual(create_response.status_code, 200)
        self.assertTrue(Product.objects.filter(name='Hammer').exists())

        list_response = self.client.get(reverse('product:product-list'))
        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, 'Hammer')

    def test_product_detail_and_filtering_support_new_fields(self):
        supplier = Supplier.objects.create(
            name='Acme Supplies',
            contact_person='Jane Doe',
            email='supplier@example.com',
            phone='123456789',
            address='123 Main St',
            city='Manila',
            postal_code='1000',
            country='Philippines',
        )
        parent_category = Category.objects.create(name='Tools', description='Tooling')
        child_category = Category.objects.create(name='Hand Tools', description='Hand tools', parent=parent_category)

        product = Product.objects.create(
            name='Hammer',
            description='Standard hammer',
            category=child_category,
            sku='SKU-002',
            unit_price=Decimal('25.00'),
            cost_price=Decimal('18.00'),
            unit_of_measure='pcs',
            code='HAM-001',
            barcode='1234567890123',
            preferred_supplier=supplier,
            quantity_in_stock=1,
            reorder_level=2,
            is_active=True,
        )

        detail_response = self.client.get(reverse('product:product-detail', args=[product.pk]))
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, 'HAM-001')

        filter_response = self.client.get(reverse('product:product-list'), {'category': child_category.pk, 'stock_status': 'low'})
        self.assertEqual(filter_response.status_code, 200)
        self.assertContains(filter_response, 'Hammer')
        self.assertContains(filter_response, 'Hand Tools')
