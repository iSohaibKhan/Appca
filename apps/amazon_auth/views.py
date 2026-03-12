"""
Views for Amazon OAuth flow.
"""
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import redirect
from django.utils import timezone
from datetime import timedelta
from .models import AmazonAccount, AmazonAdsAuth, AmazonSPAuth
from .services.oauth_service import AmazonAdsOAuthService, AmazonSPOAuthService
from .serializers import AmazonAccountSerializer


class AmazonAdsOAuthInitiateView(generics.GenericAPIView):
    """
    Initiate Amazon Ads OAuth flow.
    Returns authorization URL.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Generate OAuth URL and return it to frontend.
        """
        state = request.data.get('state', '')
        auth_url = AmazonAdsOAuthService.get_authorization_url(state=state)
        
        return Response({
            'authorization_url': auth_url
        })


class AmazonAdsOAuthCallbackView(generics.GenericAPIView):
    """
    Handle OAuth callback and store tokens.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Handle OAuth callback.
        """
        code = request.GET.get('code')
        state = request.GET.get('state')
        
        if not code:
            return Response({'error': 'Missing authorization code'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Exchange code for tokens
            token_data = AmazonAdsOAuthService.exchange_code_for_tokens(code)
            
            # Resolve organization: state can carry organization_id, else use user's first org
            org = self._get_organization_for_callback(request, state)
            if not org:
                return Response(
                    {'error': 'No organization found. User must belong to an organization.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create or get AmazonAccount for this org (one advertiser account per org for MVP)
            account, account_created = AmazonAccount.objects.get_or_create(
                organization=org,
                account_type='advertiser',
                defaults={
                    'account_name': 'Amazon Ads Account',
                    'is_active': True,
                    'is_connected': False,
                },
            )
            account.is_connected = True
            account.save(update_fields=['is_connected', 'updated_at'])
            
            # Create or update AmazonAdsAuth with tokens
            expires_in = token_data.get('expires_in', 3600)
            expires_at = timezone.now() + timedelta(seconds=expires_in)
            scope = token_data.get('scope', '')
            refresh_token = token_data.get('refresh_token') or ''
            ads_auth, auth_created = AmazonAdsAuth.objects.get_or_create(
                account=account,
                defaults={
                    'access_token': token_data['access_token'],
                    'refresh_token': refresh_token or 'pending',
                    'token_type': token_data.get('token_type', 'bearer'),
                    'expires_at': expires_at,
                    'scope': scope,
                },
            )
            if not auth_created:
                ads_auth.access_token = token_data['access_token']
                ads_auth.token_type = token_data.get('token_type', 'bearer')
                ads_auth.expires_at = expires_at
                ads_auth.scope = scope
                if refresh_token:
                    ads_auth.refresh_token = refresh_token
                ads_auth.save()
            
            return Response({
                'message': 'Successfully connected Amazon Ads account',
                'account_id': account.id,
                'token_data': {
                    'expires_in': token_data.get('expires_in'),
                    'token_type': token_data.get('token_type'),
                }
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def _get_organization_for_callback(self, request, state):
        """Resolve organization from state (optional organization_id) or user's first org."""
        if state:
            try:
                org_id = int(state.strip())
                from apps.accounts.models import Organization
                org = Organization.objects.filter(id=org_id).first()
                if org and request.user.organizations.filter(id=org_id).exists():
                    return org
            except (ValueError, TypeError):
                pass
        return getattr(request.user, 'organizations', None) and request.user.organizations.first()


class AmazonAccountListView(generics.ListCreateAPIView):
    """
    List or create Amazon accounts.
    """
    serializer_class = AmazonAccountSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Get accounts for user's organizations
        user_orgs = self.request.user.organizations.all()
        return AmazonAccount.objects.filter(organization__in=user_orgs)


class AmazonAccountDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete an Amazon account.
    """
    serializer_class = AmazonAccountSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_orgs = self.request.user.organizations.all()
        return AmazonAccount.objects.filter(organization__in=user_orgs)

