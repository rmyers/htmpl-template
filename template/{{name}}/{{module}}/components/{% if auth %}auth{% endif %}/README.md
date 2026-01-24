# Authentication Components

This module will allow you to display common login and registration forms.

## Usage

```python
from fastapi import RedirectResponse
from htmpl import render_html
from htmpl.forms import ParsedForm, use_form
from ..components.auth import LoginForm, login_form


@app.get('/login')
@app.post('/login')  # The dependency 'use_form' handles post request validation
async def login(
    page: Annotated[Any, use_component(AppPage)],
    form: Annotated[ParsedForm[LoginForm], use_form(LoginForm)],
):
    # First check if there are any errors in the form and re-render the form
    if form.errors:
        return await render_html(t"<{page}>{login_form(form)}</{page}>")

    # Check if the form has been processed and 'valid'
    if form.data is not None:
        # Optionally do something else with data first
        # if form.data.remeber_me:
        #     store_username(form.data.username)
        return RedirectResponse('/')

    # Else if there was no errors or data show the form for the user.
    # Either display the blank form or use some async functions to fetch data
    # Simple example:
    #  * Store the username in a cookie and retrieve it on next attempt
    username = await get_saved_username()
    values = {"username": username} if username else {}
    return await render_html(t"<{page}>{login_form(form, values)}</{page}>")
```
