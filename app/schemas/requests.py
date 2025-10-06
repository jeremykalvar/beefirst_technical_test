from pydantic import BaseModel, EmailStr, Field


class UserCreateIn(BaseModel):
    email: EmailStr = Field(..., description="The email of the user", max_length=255)
    password: str = Field(..., description="The password of the user", min_length=4)


class UserActivateIn(BaseModel):
    code: str = Field(..., min_length=4, max_length=4)
