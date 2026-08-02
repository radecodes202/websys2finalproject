"""
Unit tests for the audit-trail system.

Covers the four required scenarios:
1. A product update produces a correct field-level diff.
2. A deletion is logged (with a snapshot) before the object is removed.
3. A failed login is logged.
4. Audit logs cannot be edited or deleted via any code path.

Plus additional coverage for:
- CREATE actions are logged.
- Login / logout are logged.
- The log_activity() utility isolates errors (never breaks the main transaction).
- The viewer page is admin/manager-only.
- CSV export works.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_login_failed
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from audit.models import AuditLog
from audit.services import log_activity, model_diff, instance_snapshot
from category.models import Category
from product.models import Product

User = get_user_model()


class AuditLogModelTests(TestCase):
    """Tests for the AuditLog model's append-only behaviour."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='testpass123', role='admin', is_approved=True
        )

    def test_audit_log_can_be_created(self):
        """A new AuditLog entry can be saved (insert)."""
        entry = AuditLog(
            user=self.user,
            username_snapshot='testuser',
            action=AuditLog.ACTION_CREATE,
            description='Test entry',
        )
        entry.save()
        self.assertIsNotNone(entry.pk)

    def test_audit_log_cannot_be_modified(self):
        """An existing AuditLog entry cannot be saved (update)."""
        entry = AuditLog(
            user=self.user,
            username_snapshot='testuser',
            action=AuditLog.ACTION_CREATE,
            description='Original',
        )
        entry.save()

        entry.description = 'Tampered'
        with self.assertRaises(PermissionError):
            entry.save()

    def test_audit_log_cannot_be_deleted(self):
        """An AuditLog entry cannot be deleted via the ORM."""
        entry = AuditLog(
            user=self.user,
            username_snapshot='testuser',
            action=AuditLog.ACTION_CREATE,
            description='Test',
        )
        entry.save()

        with self.assertRaises(PermissionError):
            entry.delete()

    def test_audit_log_queryset_delete_blocked(self):
        """Bulk delete via queryset is also blocked by the model's delete()."""
        AuditLog.objects.create(
            user=self.user,
            username_snapshot='testuser',
            action=AuditLog.ACTION_CREATE,
            description='Test 1',
        )
        # QuerySet.delete() calls Model.delete() per instance in Django's
        # default collector, which raises PermissionError.
        with self.assertRaises(PermissionError):
            AuditLog.objects.all().delete()


class ProductUpdateDiffTests(TestCase):
    """A product update must produce a correct field-level diff."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='admin', password='testpass123', role='admin', is_approved=True
        )
        self.category = Category.objects.create(name='Electronics')
        self.product = Product.objects.create(
            name='Sony WH-1000XM5',
            category=self.category,
            sku='SONY-WH1000',
            unit_price='349.99',
            quantity_in_stock=50,
            reorder_level=10,
        )
        # Clear audit logs created during setUp (CREATE signals).
        # We can't delete them (append-only), so we filter them out in tests.
        self.create_log_count = AuditLog.objects.filter(
            action=AuditLog.ACTION_CREATE,
            content_type__model='product',
        ).count()

    def test_product_update_produces_correct_diff(self):
        """Updating a product logs only the changed fields with old/new values."""
        old_stock = self.product.quantity_in_stock
        old_price = self.product.unit_price

        self.product.quantity_in_stock = 45
        self.product.unit_price = '329.99'
        self.product.save()

        # Find the UPDATE audit log for this product.
        update_logs = AuditLog.objects.filter(
            action=AuditLog.ACTION_UPDATE,
            content_type__model='product',
            object_id=str(self.product.pk),
        )
        self.assertTrue(update_logs.exists(), 'No UPDATE audit log was created.')

        changes = update_logs.first().changes
        # quantity_in_stock should be in the diff with old=50, new=45.
        self.assertIn('quantity_in_stock', changes)
        self.assertEqual(changes['quantity_in_stock']['old'], old_stock)
        self.assertEqual(changes['quantity_in_stock']['new'], 45)

        # unit_price should be in the diff.
        self.assertIn('unit_price', changes)
        self.assertEqual(changes['unit_price']['old'], str(old_price))
        self.assertEqual(changes['unit_price']['new'], '329.99')

        # name should NOT be in the diff (it didn't change).
        self.assertNotIn('name', changes)


class ProductDeletionTests(TestCase):
    """A deletion must be logged with a snapshot before the object is removed."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='admin', password='testpass123', role='admin', is_approved=True
        )
        self.category = Category.objects.create(name='Electronics')
        self.product = Product.objects.create(
            name='Test Product',
            category=self.category,
            sku='TEST-001',
            unit_price='10.00',
            quantity_in_stock=5,
        )

    def test_deletion_is_logged_with_snapshot(self):
        """Deleting a product creates a DELETE audit log with the object's data."""
        product_pk = self.product.pk
        product_name = self.product.name
        product_sku = self.product.sku

        self.product.delete()

        delete_logs = AuditLog.objects.filter(
            action=AuditLog.ACTION_DELETE,
            content_type__model='product',
            object_id=str(product_pk),
        )
        self.assertTrue(delete_logs.exists(), 'No DELETE audit log was created.')

        log = delete_logs.first()
        self.assertEqual(log.severity, AuditLog.SEVERITY_WARNING)
        self.assertIn(product_name, log.object_repr)

        # The snapshot should contain the product's field values.
        snapshot = log.changes
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.get('name'), product_name)
        self.assertEqual(snapshot.get('sku'), product_sku)


class FailedLoginTests(TestCase):
    """A failed login attempt must be logged."""

    def test_failed_login_is_logged(self):
        """A failed login via the login view creates a LOGIN_FAILED audit log."""
        # Create a user so the username exists (but we'll use a wrong password).
        User.objects.create_user(
            username='realuser', password='correctpass123', role='cashier', is_approved=True
        )

        client = Client()
        response = client.post(
            reverse('accounts:login'),
            {'username': 'realuser', 'password': 'wrongpassword'},
        )

        # The login should fail (redirects back to login page or shows error).
        self.assertEqual(response.status_code, 200)

        # A LOGIN_FAILED audit log should exist.
        failed_logs = AuditLog.objects.filter(action=AuditLog.ACTION_LOGIN_FAILED)
        self.assertTrue(failed_logs.exists(), 'No LOGIN_FAILED audit log was created.')

        log = failed_logs.first()
        self.assertEqual(log.severity, AuditLog.SEVERITY_WARNING)
        self.assertIn('realuser', log.description)

    def test_failed_login_signal_directly(self):
        """Sending the user_login_failed signal directly creates a log."""
        from django.contrib.auth.signals import user_login_failed

        request = RequestFactory().post('/login/', {'username': 'ghost'})
        user_login_failed.send(
            sender=User,
            credentials={'username': 'ghost'},
            request=request,
        )

        failed_logs = AuditLog.objects.filter(
            action=AuditLog.ACTION_LOGIN_FAILED,
            username_snapshot='',
        )
        self.assertTrue(failed_logs.exists())


class LoginLogoutTests(TestCase):
    """Successful login and logout must be logged."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='loginuser', password='testpass123', role='admin', is_approved=True
        )

    def test_successful_login_is_logged(self):
        """A successful login creates a LOGIN audit log."""
        client = Client()
        client.post(
            reverse('accounts:login'),
            {'username': 'loginuser', 'password': 'testpass123'},
        )

        login_logs = AuditLog.objects.filter(
            action=AuditLog.ACTION_LOGIN,
            username_snapshot='loginuser',
        )
        self.assertTrue(login_logs.exists())

    def test_logout_is_logged(self):
        """A logout creates a LOGOUT audit log."""
        client = Client()
        client.login(username='loginuser', password='testpass123')
        client.get(reverse('accounts:logout'))

        logout_logs = AuditLog.objects.filter(
            action=AuditLog.ACTION_LOGOUT,
            username_snapshot='loginuser',
        )
        self.assertTrue(logout_logs.exists())


class LogActivityErrorIsolationTests(TestCase):
    """log_activity() must never raise — it isolates errors."""

    def test_log_activity_returns_none_on_failure(self):
        """If the audit write fails, log_activity returns None (no exception)."""
        # Pass a non-JSON-serializable object as changes to force a
        # serialization error inside the JSONField.
        class NotSerializable:
            pass

        result = log_activity(
            action=AuditLog.ACTION_OTHER,
            description='This should fail gracefully',
            changes={'bad': NotSerializable()},
        )
        self.assertIsNone(result)

    def test_log_activity_with_valid_data(self):
        """log_activity creates an entry with valid data."""
        result = log_activity(
            action=AuditLog.ACTION_OTHER,
            description='Manual test entry',
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.description, 'Manual test entry')


class AuditViewerAccessTests(TestCase):
    """The audit viewer page is admin/manager-only."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin', password='testpass123', role='admin', is_approved=True
        )
        self.cashier = User.objects.create_user(
            username='cashier', password='testpass123', role='cashier', is_approved=True
        )

    def test_admin_can_access_audit_list(self):
        """Admin role can access the audit log list page."""
        client = Client()
        client.login(username='admin', password='testpass123')
        response = client.get(reverse('audit:audit-log-list'))
        self.assertEqual(response.status_code, 200)

    def test_cashier_cannot_access_audit_list(self):
        """Cashier role gets 403 (or redirect) when accessing audit log."""
        client = Client()
        client.login(username='cashier', password='testpass123')
        response = client.get(reverse('audit:audit-log-list'))
        # RoleRequiredMixin returns 403 for authenticated users with wrong role.
        self.assertIn(response.status_code, (403, 302))

    def test_anonymous_redirected_to_login(self):
        """Anonymous user is redirected to login."""
        client = Client()
        response = client.get(reverse('audit:audit-log-list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_csv_export_works_for_admin(self):
        """Admin can export audit logs to CSV."""
        client = Client()
        client.login(username='admin', password='testpass123')
        response = client.get(reverse('audit:audit-log-export'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment', response['Content-Disposition'])


class ModelDiffUtilityTests(TestCase):
    """Tests for the model_diff() and instance_snapshot() utilities."""

    def setUp(self):
        self.category = Category.objects.create(name='TestCat')

    def test_model_diff_detects_changes(self):
        """model_diff returns only changed fields."""
        p1 = Product(
            name='A', category=self.category, sku='A1', unit_price='10.00', quantity_in_stock=5
        )
        p2 = Product(
            name='A', category=self.category, sku='A1', unit_price='15.00', quantity_in_stock=5
        )
        diff = model_diff(p1, p2)
        self.assertIn('unit_price', diff)
        self.assertNotIn('name', diff)
        self.assertNotIn('quantity_in_stock', diff)

    def test_model_diff_with_none_old(self):
        """model_diff with old=None reports all fields as new."""
        p = Product(
            name='B', category=self.category, sku='B1', unit_price='20.00', quantity_in_stock=3
        )
        diff = model_diff(None, p)
        self.assertIn('name', diff)
        self.assertIsNone(diff['name']['old'])
        self.assertEqual(diff['name']['new'], 'B')

    def test_instance_snapshot_captures_fields(self):
        """instance_snapshot returns a JSON-safe dict of field values."""
        p = Product(
            name='C', category=self.category, sku='C1', unit_price='30.00', quantity_in_stock=7
        )
        snapshot = instance_snapshot(p)
        self.assertEqual(snapshot['name'], 'C')
        self.assertEqual(snapshot['sku'], 'C1')
        self.assertEqual(snapshot['unit_price'], '30.00')