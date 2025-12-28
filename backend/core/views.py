from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from allauth.socialaccount.models import SocialAccount
from core.models import SiteWarning
from django.shortcuts import redirect
from django.conf import settings
from django.views import View
from urllib.parse import urlencode

User = get_user_model()


class GetWarningsView(APIView):
    """Get site warnings"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        warnings = SiteWarning.objects.filter(is_visible=True)
        return Response([{'text': w.text} for w in warnings])


class CurrentUserView(APIView):
    """Get current authenticated user information"""
    permission_classes = [AllowAny]  # Allow any to check if user is authenticated
    
    def get(self, request):
        if request.user.is_authenticated:
            # Get Discord account info if available
            discord_account = None
            try:
                social_account = SocialAccount.objects.get(
                    user=request.user,
                    provider='discord'
                )
                discord_account = {
                    'id': social_account.uid,
                    'username': social_account.extra_data.get('username', ''),
                    'discriminator': social_account.extra_data.get('discriminator', ''),
                    'avatar': social_account.extra_data.get('avatar', None),
                }
            except SocialAccount.DoesNotExist:
                pass
            
            return Response({
                'is_authenticated': True,
                'user': {
                    'id': request.user.id,
                    'username': request.user.username,
                    'email': request.user.email,
                    'discord': discord_account,
                }
            })
        else:
            return Response({
                'is_authenticated': False,
                'user': None
            })


class LogoutView(APIView):
    """Logout the current user"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Django session logout
        from django.contrib.auth import logout
        logout(request)
        return Response({'message': 'Successfully logged out'}, status=status.HTTP_200_OK)


class DirectDiscordLoginView(View):
    """
    View that redirects directly to Discord OAuth, skipping the allauth login page.
    Preserves the 'next' parameter to redirect back to the original page after login.
    """
    def get(self, request):
        # Get the 'next' parameter from the request (where to redirect after login)
        next_url = request.GET.get('next', '')
        
        # Build the Discord login URL with process=login to skip the intermediate page
        discord_login_url = '/api/accounts/discord/login/?process=login'
        
        # If we have a next URL, preserve it through the OAuth flow
        # We'll store it in the session so it's available after OAuth callback
        if next_url:
            request.session['login_redirect_url'] = next_url
        
        # Redirect directly to Discord OAuth (this will skip the allauth login page)
        return redirect(discord_login_url)
