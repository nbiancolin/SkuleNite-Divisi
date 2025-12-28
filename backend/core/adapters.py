from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Custom account adapter that redirects to the frontend after login.
    """
    
    def get_login_redirect_url(self, request):
        """
        Returns the URL to redirect to after login.
        """
        # Check for redirect URL in session (set during login)
        redirect_url = request.session.get('login_redirect_url')
        if redirect_url:
            # Clear it from session
            del request.session['login_redirect_url']
            return redirect_url
        
        # Check for 'next' parameter in request
        next_url = request.GET.get('next') or request.POST.get('next')
        if next_url:
            return next_url
        
        # Default to frontend homepage
        return getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom adapter that redirects to the frontend after social login,
    preserving the 'next' parameter from the session.
    """
    
    def get_connect_redirect_url(self, request, socialaccount):
        """
        Returns the URL to redirect to after a social account is connected.
        """
        # Get the redirect URL from session (set during login)
        redirect_url = request.session.get('login_redirect_url')
        if redirect_url:
            # Clear it from session
            del request.session['login_redirect_url']
            return redirect_url
        
        # Default to frontend homepage
        return getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
    
    def pre_social_login(self, request, sociallogin):
        """
        Called before a social login is processed.
        We can use this to store the redirect URL in the session.
        """
        # The 'next' parameter should already be in the session from DirectDiscordLoginView
        # But we can also check the request for it
        next_url = request.GET.get('next') or request.session.get('login_redirect_url')
        if next_url:
            request.session['login_redirect_url'] = next_url

