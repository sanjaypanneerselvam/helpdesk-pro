from rest_framework.authentication import TokenAuthentication


class BearerTokenAuthentication(TokenAuthentication):
    """
    DRF's TokenAuthentication expects:  Authorization: Token <key>
    Postman's "Bearer Token" option sends: Authorization: Bearer <key>
    Changing the keyword makes both the web screens and Postman use "Bearer".
    """

    keyword = "Bearer"
