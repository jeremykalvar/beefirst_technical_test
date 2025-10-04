from pydantic import BaseModel, Field


class UserCreateIn(BaseModel):
    email: str = Field(..., description="The email of the user", max_length=255)
    password: str = Field(..., description="The password of the user", min_length=4)
