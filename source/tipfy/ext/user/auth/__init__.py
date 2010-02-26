# -*- coding: utf-8 -*-
"""
    tipfy.ext.user.auth
    ~~~~~~~~~~~~~~~~~~~

    Base authentication utilities.

    This module derives from `Solace`_.

    :copyright: 2010 by tipfy.org.
    :license: BSD, see LICENSE.txt for more details.
"""
from tipfy import local, redirect_to, get_config, import_string, \
    cached_property, app, request


class BaseAuth(object):
    #: Used to identify the auth provider in user ids.
    auth_name = 'google'

    #: Set to True to indicate that this login system uses a password
    #: This will also affect the standard login form and the standard profile
    #: form.
    use_password = False

    #: If you don't want to see a register link in the user interface
    #: for this auth system, you can disable it here.
    show_register_link = False

    #: For auth systems that are managing the email externally this
    #: attributes has to set to `True`.  In that case the user will
    #: be unable to change the email from the profile.  (True for
    #: Google auth, possible OpenID support and more.)
    external_email = True

    #: Like `external_email` but for the password
    external_password = True

    #: Endpoint to the handler that creates a new user account.
    signup_endpoint = 'users/signup'

    #: Endpoint to the handler that logs in the user.
    login_endpoint = 'users/login'

    #: Endpoint to the handler that logs out the user.
    logout_endpoint = 'users/logout'

    @cached_property
    def user_model(self):
        """The configured user model."""
        return import_string(get_config('tipfy.ext.user', 'user_model'))

    @property
    def can_reset_password(self):
        """You can either override this property or leave the default
        implementation that should work most of the time.  By default
        the auth system can reset the password if the password is used and
        not externally managed.
        """
        return (self.use_password and not self.external_password)

    def create_signup_url(self, dest_url):
        """Returns the signup URL for this request and specified destination URL.

        :param dest_url:
            String that is the desired final destination URL for the user once
            signup is complete.
        :return:
            An URL to perform signup.
        """
        return url_for(self.signup_endpoint, redirect=dest_url, full=True)

    def create_login_url(self, dest_url):
        """Returns the login URL for this request and specified destination URL.

        :param dest_url:
            String that is the desired final destination URL for the user once
            login is complete.
        :return:
            An URL to perform login.
        """
        return url_for(self.login_endpoint, redirect=dest_url, full=True)

    def create_logout_url(self, dest_url):
        """Returns the logout URL for this request and specified destination
        URL.

        :param dest_url:
            String that is the desired final destination URL for the user once
            logout is complete.
        :return:
            An URL to perform logout.
        """
        return url_for(self.logout_endpoint, redirect=dest_url, full=True)

    def get_current_user(self):
        """Returns the currently logged in user or ``None``.

        :return:
            A :class:`User` entity, if the user for the current request is
            logged in, or ``None``.
        """
        return local.user

    def is_current_user_admin(self):
        """Returns ``True`` if the current user is an admin.

        :return:
            ``True`` if the user for the current request is an admin, ``False``
            otherwise.
        """
        if local.user is not None:
            return local.user.is_admin()

        return False

    def is_logged_in(self):
        """Returns ``True`` if the current user is logged in.

        :return:
            ``True`` if the user for the current request is authenticated,
            ``False`` otherwise.
        """
        raise NotImplementedError()

    def authenticate_with_session(self, request):
        raise NotImplementedError()

    def authenticate_with_form(self, username, password, remember=False):
        raise NotImplementedError()

    def get_user_id(self):
        """Returns the user id used by this authentication system The user id
        is in the format `auth_name|auth_unique_id`.

        :return:
            An user id.
        """
        if local.user_auth is None:
            return None

        return '%s|%s' % (self.auth_name, local.user_auth[0])

    def load_user(self):
        local.user_auth = self.authenticate_with_session(request)
        if local.user_auth is None:
            local.user = None
            return

        user = self.user_model.get_by_user_id(self.get_user_id())
        if user is None and app.rule.endpoint != self.signup_endpoint:
            # User is logged in but User entity is not already created:
            # redirect to the `users/signup` page.
            redirect = local.request.args.get('redirect', request.url)
            return redirect_to(self.signup_endpoint, redirect=redirect)

        local.user = user

    def create_user(self, username, **kwargs):
        """Saves a new user in the datastore for the currently logged in user,
        and returns it. If the username already exists, returns ``None``.

        :param username:
            The unique username for this user.
        :param kwargs:
            Extra keyword arguments accepted by
            :class:`tipfy.ext.user.models.User`.
        :return:
            The new :class:`tipfy.ext.user.models.User` entity, or ``None`` if
            the username already exists.
        """
        return self.user_model.create(username, user_id=self.get_user_id(),
            **kwargs)
