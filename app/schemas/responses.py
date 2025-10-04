from typing import Literal

from pydantic import BaseModel, Field


class UserCreateOut(BaseModel):
    id: str = Field(..., description="The id of the user")
    email: str = Field(..., description="The email of the user")


class AcceptedOut(BaseModel):
    status: Literal["accepted"] = "accepted"
