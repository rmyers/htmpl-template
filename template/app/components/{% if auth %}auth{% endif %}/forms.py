import re

from htmpl.forms import BaseForm
from pydantic import EmailStr, Field, SecretStr, field_validator

VALIDUSERNAME = re.compile(r"^[a-z0-9_-]$")


class LoginForm(BaseForm):
    username: str = Field(description="Enter your username")
    password: SecretStr = Field(description="Enter your password")


class RegistrationForm(BaseForm):
    name: str = Field(description="What do you want us to call you?")
    email: EmailStr
    username: str = Field(
        description="Pick a good one, no spaces or special chars",
        min_length=3,
        max_length=16,
    )
    password: SecretStr = Field(min_length=6, max_length=150)

    @field_validator("username", mode="after")
    @classmethod
    def username_valid(cls, username: str) -> str:
        _username = username.lower()
        if VALIDUSERNAME.match(_username):
            return _username

        raise ValueError(
            "Invalid username, only letters, numbers, '-', and '_' allowed"
        )
