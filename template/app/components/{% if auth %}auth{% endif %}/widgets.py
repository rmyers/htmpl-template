from string.templatelib import Template

from .forms import LoginForm


def login_form(form: LoginForm, values: dict | None = None) -> Template:
    return t'''<!DOCTYPE html>
<html data-theme="dark">
<head><title>Login</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
</head>
<body class="container">
<article style="max-width: 600px; margin: 4rem auto;">
    <h2>htmpl Manager</h2>
    {form.render(values=values)}
</article>
</body>
</html>'''
