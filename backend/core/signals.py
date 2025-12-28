"""
Signal handlers for django-allauth to handle redirects after social login.
"""
from django.dispatch import receiver
from allauth.account.signals import user_logged_in
from allauth.socialaccount.signals import social_account_added, pre_social_login
from django.conf import settings
from django.shortcuts import redirect


@receiver(user_logged_in)
def redirect_after_login(sender, request, user, **kwargs):
    """
    Redirect to frontend after login, preserving the 'next' parameter.
    """
    # Check if this is a social login by looking for the redirect URL in session
    redirect_url = request.session.get('login_redirect_url')
    if redirect_url:
        # Clear it from session
        del request.session['login_redirect_url']
        # Store it for the view to use
        request.session['_redirect_after_login'] = redirect_url


@receiver(pre_social_login)
def store_redirect_url(sender, request, sociallogin, **kwargs):
    """
    Store the redirect URL before social login is processed.
    """
    # Get next URL from query params or session
    next_url = request.GET.get('next') or request.session.get('login_redirect_url')
    if next_url:
        request.session['login_redirect_url'] = next_url

