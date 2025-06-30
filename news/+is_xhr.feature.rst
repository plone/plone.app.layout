plone_layout view: Add is_ajax property.

Add the new property `is_ajax` to the Plone layout view.

`is_ajax`: Returns True, if an AJAX request is detected. This is done by
checking if the `HTTP_X_REQUESTED_WITH` request header is set to
`XMLHttpRequest`.

Note: This is an unreliable way to detect AJAX requests. While many client-side
libraries (like jQuery) add this request header automatically, the Fetch API
does not. When using fetch, it is recommended to wrap it with a helper function
that adds this header to each request.

[thet]
