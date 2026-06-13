from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import databases
import sqlalchemy
from datetime import datetime
from typing import Optional
import os
from dotenv import load_dotenv

from models import (
    TicketCreate, TicketUpdate, TicketResponse,
    TicketType, TicketStatus
)

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

database = databases.Database(DATABASE_URL)

metadata = sqlalchemy.MetaData()

tickets_table = sqlalchemy.Table(
    "tickets",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("ticket_number", sqlalchemy.String(50), unique=True, nullable=False),
    sqlalchemy.Column("title", sqlalchemy.String(255), nullable=False),
    sqlalchemy.Column("description", sqlalchemy.Text, nullable=False),
    sqlalchemy.Column("created_by", sqlalchemy.String(100), nullable=False),
    sqlalchemy.Column("created_date", sqlalchemy.DateTime, default=datetime.utcnow),
    sqlalchemy.Column("ticket_type", sqlalchemy.String(50), nullable=False),
    sqlalchemy.Column("status", sqlalchemy.String(50), default="OPEN"),
    sqlalchemy.Column("updated_at", sqlalchemy.DateTime, nullable=True),
)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS tickets (
    id SERIAL PRIMARY KEY,
    ticket_number VARCHAR(50) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    created_by VARCHAR(100) NOT NULL,
    created_date TIMESTAMP DEFAULT NOW(),
    ticket_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'OPEN',
    updated_at TIMESTAMP
);
"""

@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    await database.execute(CREATE_TABLE_SQL)
    yield
    await database.disconnect()


app = FastAPI(
    title="Ticket Management API",
    description="REST API to manage support/work tickets with full CRUD operations.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def generate_ticket_number() -> str:
    date_str = datetime.utcnow().strftime("%Y%m%d")
    import random
    suffix = random.randint(1000, 9999)
    return f"TKT-{date_str}-{suffix}"


@app.post("/tickets", response_model=TicketResponse, status_code=201, tags=["Tickets"])
async def create_ticket(ticket: TicketCreate):
    ticket_number = generate_ticket_number()
    query = tickets_table.insert().values(
        ticket_number=ticket_number,
        title=ticket.title,
        description=ticket.description,
        created_by=ticket.created_by,
        created_date=datetime.utcnow(),
        ticket_type=ticket.ticket_type.value,
        status=TicketStatus.OPEN.value,
        updated_at=None,
    )
    ticket_id = await database.execute(query)
    return await get_ticket(ticket_id)


@app.get("/tickets", response_model=list[TicketResponse], tags=["Tickets"])
async def list_tickets(
    ticket_type: Optional[TicketType] = None,
    status: Optional[TicketStatus] = None,
    created_by: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    query = tickets_table.select()
    if ticket_type:
        query = query.where(tickets_table.c.ticket_type == ticket_type.value)
    if status:
        query = query.where(tickets_table.c.status == status.value)
    if created_by:
        query = query.where(tickets_table.c.created_by == created_by)
    query = query.order_by(tickets_table.c.created_date.desc()).limit(limit).offset(offset)
    rows = await database.fetch_all(query)
    return [dict(row) for row in rows]


@app.get("/tickets/{ticket_id}", response_model=TicketResponse, tags=["Tickets"])
async def get_ticket(ticket_id: int):
    query = tickets_table.select().where(tickets_table.c.id == ticket_id)
    row = await database.fetch_one(query)
    if not row:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    return dict(row)


@app.get("/tickets/number/{ticket_number}", response_model=TicketResponse, tags=["Tickets"])
async def get_ticket_by_number(ticket_number: str):
    query = tickets_table.select().where(tickets_table.c.ticket_number == ticket_number)
    row = await database.fetch_one(query)
    if not row:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_number} not found")
    return dict(row)


@app.put("/tickets/{ticket_id}", response_model=TicketResponse, tags=["Tickets"])
async def update_ticket(ticket_id: int, ticket: TicketUpdate):
    existing = await database.fetch_one(
        tickets_table.select().where(tickets_table.c.id == ticket_id)
    )
    if not existing:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    update_data = {k: v for k, v in ticket.model_dump(exclude_unset=True).items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update")
    if "ticket_type" in update_data:
        update_data["ticket_type"] = update_data["ticket_type"].value
    if "status" in update_data:
        update_data["status"] = update_data["status"].value
    update_data["updated_at"] = datetime.utcnow()
    await database.execute(
        tickets_table.update().where(tickets_table.c.id == ticket_id).values(**update_data)
    )
    return await get_ticket(ticket_id)


@app.delete("/tickets/{ticket_id}", tags=["Tickets"])
async def delete_ticket(ticket_id: int):
    existing = await database.fetch_one(
        tickets_table.select().where(tickets_table.c.id == ticket_id)
    )
    if not existing:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    await database.execute(
        tickets_table.delete().where(tickets_table.c.id == ticket_id)
    )
    return {"message": f"Ticket {ticket_id} deleted successfully"}


@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
