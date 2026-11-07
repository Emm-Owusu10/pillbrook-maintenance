import uuid

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
    csrf_token: str