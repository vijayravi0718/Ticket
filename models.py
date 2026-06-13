from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class TicketType(str, Enum):
    BUG = "BUG"
    FEATURE = "FEATURE"
    SUPPORT = "SUPPORT"
    TASK = "TASK"
    INCIDENT = "INCIDENT"


class TicketStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class TicketCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255, example="Login button not working")
    description: str = Field(..., min_length=10, example="Users are unable to click the login button on the homepage. The button appears but does not respond to clicks.")
    created_by: str = Field(..., min_length=1, max_length=100, example="john.doe")
    ticket_type: TicketType = Field(..., example=TicketType.BUG)

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "Login button not working",
                "description": "Users are unable to click the login button on the homepage. The button appears but does not respond to clicks on Chrome v120.",
                "created_by": "john.doe",
                "ticket_type": "BUG"
            }
        }
    }


class TicketUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = Field(None, min_length=10)
    ticket_type: Optional[TicketType] = None
    status: Optional[TicketStatus] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "IN_PROGRESS",
                "description": "Updated description with more details."
            }
        }
    }


class TicketResponse(BaseModel):
    id: int
    ticket_number: str
    title: str
    description: str
    created_by: str
    created_date: datetime
    ticket_type: str
    status: str
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
