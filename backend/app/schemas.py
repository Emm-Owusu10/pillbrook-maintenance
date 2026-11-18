import uuid

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LoginIn(BaseModel):
    # Generous limits only stop absurdly large bodies. The real rules are applied in the login code.
    email: str = Field(max_length=320)
    password: str = Field(max_length=1024)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    name: str
    email: str
    role: str


class AuthOut(BaseModel):
    user: UserOut
    permissions: list[str]
    must_change_password: bool
    csrf_token: str



class RegisterIn(BaseModel):
    # Generous limits only stop absurdly large bodies. The real rules are applied in the registration code.
    name: str = Field(max_length=200)
    email: str = Field(max_length=320)
    password: str = Field(max_length=1024)
    access_code: str = Field(max_length=64)


class RegisterOut(BaseModel):
    verification_required: bool
    verification_email_sent: bool


class VerifyIn(BaseModel):
    token: str = Field(max_length=200)


class VerifiedOut(BaseModel):
    verified: bool


class ResendIn(BaseModel):
    email: str = Field(max_length=320)


class MessageOut(BaseModel):
    message: str



class ChangePasswordIn(BaseModel):
    current_password: str = Field(max_length=1024)
    new_password: str = Field(max_length=1024)


class ForgotIn(BaseModel):
    email: str = Field(max_length=320)


class ResetIn(BaseModel):
    token: str = Field(max_length=200)
    new_password: str = Field(max_length=1024)


class OptionsOut(BaseModel):
    email_reset_available: bool


class AdminResetIn(BaseModel):
    email: str = Field(max_length=320)


class TemporaryPasswordOut(BaseModel):
    name: str
    email: str
    temporary_password: str
    expires_at: datetime