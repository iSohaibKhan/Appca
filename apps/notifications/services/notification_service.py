"""
Service for sending notifications.
"""
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from ..models import Notification, NotificationPreference


class NotificationService:
    """
    Service for creating and sending notifications.
    
    TODO: Phase 4 - Implement email sending
    TODO: Phase 4 - Implement notification templates
    """
    
    @staticmethod
    def create_notification(
        user,
        title,
        message,
        notification_type='info',
        organization=None,
        entity_type=None,
        entity_id=None,
        send_email=False
    ):
        """
        Create an in-app notification.
        
        TODO: Phase 4 - Add email sending logic
        """
        notification = Notification.objects.create(
            user=user,
            organization=organization,
            type=notification_type,
            title=title,
            message=message,
            entity_type=entity_type or '',
            entity_id=entity_id or ''
        )
        
        # Send email if requested and user has preference enabled
        if send_email:
            NotificationService._send_email_notification(user, title, message, notification_type)
        
        return notification
    
    @staticmethod
    def _send_email_notification(user, title, message, notification_type):
        """
        Send email notification.
        
        TODO: Phase 4 - Implement email templates
        """
        preferences = NotificationPreference.objects.filter(user=user).first()
        
        if not preferences:
            return
        
        # Check if user wants email notifications for this type
        # Simplified logic - expand in Phase 4
        if notification_type in ['warning', 'error']:
            send_mail(
                subject=f"Appca: {title}",
                message=message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.email],
                fail_silently=True
            )
    
    @staticmethod
    def notify_autopilot_action(user, account, action_description):
        """
        Notify user about autopilot action.
        """
        preferences = NotificationPreference.objects.filter(user=user).first()
        
        if preferences and preferences.in_app_autopilot_actions:
            NotificationService.create_notification(
                user=user,
                title="Autopilot Action",
                message=action_description,
                notification_type='info',
                entity_type='autopilot_execution',
                send_email=preferences.email_autopilot_actions
            )
    
    @staticmethod
    def notify_low_inventory(user, account, product, stock_level):
        """
        Notify user about low inventory.
        """
        preferences = NotificationPreference.objects.filter(user=user).first()
        
        if preferences and preferences.in_app_low_inventory:
            NotificationService.create_notification(
                user=user,
                title="Low Inventory Alert",
                message=f"Product {product.asin} has low stock: {stock_level} units",
                notification_type='warning',
                entity_type='product',
                entity_id=str(product.id),
                send_email=preferences.email_low_inventory
            )

