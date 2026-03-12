"""
Service for Stripe integration (Phase 5).
Set STRIPE_SECRET_KEY and STRIPE_PUBLISHABLE_KEY in settings to enable.
"""
# import stripe
# from django.conf import settings
# stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', None)


class StripeService:
    """
    Service for Stripe operations. All methods are stubs until keys are configured.
    """

    @staticmethod
    def create_customer(organization, email):
        """Create Stripe customer. Phase 5 - Implement when keys are set."""
        return None

    @staticmethod
    def create_subscription(customer_id, plan_id):
        """Create Stripe subscription. Phase 5 - Implement when keys are set."""
        return None

    @staticmethod
    def cancel_subscription(subscription_id):
        """Cancel Stripe subscription. Phase 5 - Implement when keys are set."""
        pass

    @staticmethod
    def change_plan(stripe_subscription_id, new_plan_stripe_price_id):
        """Change subscription plan (upgrade/downgrade). Phase 5 - Implement when keys are set."""
        return None

    @staticmethod
    def list_payment_methods(stripe_customer_id):
        """List payment methods for customer. Phase 5 - Implement when keys are set."""
        return []

    @staticmethod
    def attach_payment_method(stripe_customer_id, stripe_payment_method_id):
        """Attach payment method to customer. Phase 5 - Implement when keys are set."""
        return None

    @staticmethod
    def set_default_payment_method(stripe_customer_id, stripe_payment_method_id):
        """Set default payment method. Phase 5 - Implement when keys are set."""
        pass

    @staticmethod
    def detach_payment_method(stripe_payment_method_id):
        """Detach payment method. Phase 5 - Implement when keys are set."""
        pass

    @staticmethod
    def list_invoices(stripe_customer_id, limit=12):
        """List invoices for customer. Phase 5 - Implement when keys are set."""
        return []

    @staticmethod
    def get_invoice_pdf_url(stripe_invoice_id):
        """Get invoice PDF URL. Phase 5 - Implement when keys are set."""
        return None

