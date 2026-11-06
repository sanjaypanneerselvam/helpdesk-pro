from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """
    Make every error look like {"detail": "..."}.

    DRF already does this for 401/403/404. Validation errors (400) are
    different: field errors stay as {"field": ["msg"]} (the web forms need
    them), but general errors are flattened into {"detail": "msg"}.
    """
    response = exception_handler(exc, context)
    if response is None:
        return response

    # Don't leak internals ("No Ticket matches the given query.") - and a customer
    # probing someone else's ticket should see exactly what they'd see for a missing one.
    if response.status_code == 404:
        response.data = {"detail": "Not found."}
        return response

    data = response.data
    if isinstance(data, list):
        response.data = {"detail": " ".join(str(m) for m in data)}
    elif isinstance(data, dict) and list(data.keys()) == ["non_field_errors"]:
        response.data = {"detail": " ".join(str(m) for m in data["non_field_errors"])}
    return response
