plone_layout view: Add is_xhr and use_ajax methods.

Add two new methods to the Plone layout view:

- `is_xhr`: Returns True, if an AJAX request is detected. This is done by
  checking if the `HTTP_X_REQUESTED_WITH` request header is set to
  `XMLHttpRequest`. This is set by many JavaScript libraries. Bare `fetch`
  requests do not set this without any other intercention, though. So, `is_xhr`
  is not guaranteed to really detect every and all XHR requests.

- `use_ajax`: Returns True, if `is_xhr` returns True, `ajax_load` is unset or
  not `False` and the `plone.use_ajax` registry parameter is set to True. This
  can be used to automatically switch to the ajax main template for XHR requests
  instead of manually setting `ajax_load`, for Plone 6.2.
  Manually setting the `ajax_load` query parameter always takes precedence.

[thet]
