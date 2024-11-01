from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional, List, Any
import random

app = FastAPI()

bookings: dict[int, dict[str, Any]] = {
    1: {"id": 1, "name": "Joel", "classroom": "A401", "start_time": "2024-10-23T08:30:00Z", "end_time": "2024-10-23T10:00:00Z"},
    2: {"id": 2, "name": "Sami", "classroom": "C301", "start_time": "2024-10-23T08:30:00Z", "end_time": "2024-10-23T10:00:00Z"},
    3: {"id": 3, "name": "Sami", "classroom": "B204", "start_time": "2024-10-23T08:30:00Z", "end_time": "2024-10-23T10:00:00Z"},
    4: {"id": 4, "name": "Karin", "classroom": "A401", "start_time": "2024-10-23T10:00:00Z", "end_time": "2024-10-23T15:00:00Z"},
}


# fmt: off
classrooms = [
    "A101", "A102", "A103", "A104", "B101", "B102", "B103", "B104",
    "C101", "C102", "C103", "C104", "A201", "A202", "A203", "A204",
    "B201", "B202", "B203", "B204", "C201", "C202", "C203", "C204",
    "A301", "A302", "A303", "A304", "B301", "B302", "B303", "B304",
    "C301", "C302", "C303", "C304", "A401", "A402", "A403", "A404",
    "B401", "B402", "B403", "B404", "C401", "C402", "C403", "C404"
]
# fmt: on


# Modell för att skapa en ny bokning
class Booking(BaseModel):
    id: Optional[int] = None  # Optional eftersom att ID:t kommer att skapas automatiskt vid skapandet av bokningen
    name: str
    classroom: str
    start_time: datetime
    end_time: datetime


# Modell för att skapa en uppdatering av en bokning (slås sedan ihop med vanliga modellen efter validering)
class UpdateBooking(BaseModel):
    name: Optional[str] = None
    classroom: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


# * GET: HÄMTAR ALLA KLASSRUMSNAMN FRÅN LISTAN
@app.get("/classrooms", response_model=List[str])
async def get_classrooms():
    """Hämtar listan på alla klassrum."""
    return classrooms


# * GET: VISA TILLGÄNGLIGA KLASSRUM FÖR ETT ANGIVET TIDSINTERVALL
@app.get("/available-classrooms")
async def get_available_classrooms(start_time: datetime, end_time: datetime):
    """Visar alla tillgängliga klassrum för ett angivet tidsintervall."""

    # Kontrollerar att tidsintervallet på bokningen är minst en timme lång
    duration = end_time - start_time
    if duration < timedelta(hours=1):
        raise HTTPException(status_code=422, detail="Booking must be at least one hour long!")

    # Loopar genom alla existerande bokningar
    booked_classrooms = []
    for existing_booking in bookings.values():
        # Skapar datetime objekt av datum-strängarna i den existerande bokningen
        existing_start_time = datetime.fromisoformat(existing_booking["start_time"])
        existing_end_time = datetime.fromisoformat(existing_booking["end_time"])

        # Kontrollerar att nya datan inte överlappar med en existerande bokning
        # Skapar en lista av alla klassrum som är bokade på den angivna tiden
        if not (existing_end_time <= start_time or existing_start_time >= end_time):
            booked_classrooms.append(existing_booking["classroom"])

    # Skapar listan med alla tillgängliga klassrum
    available_classrooms = []
    for classroom in classrooms:  # Loopar genom alla klassrum
        if classroom not in booked_classrooms:  # Om ett klassrum inte är ett bokat klassrum läggs den till i available_classroooms listan
            available_classrooms.append(classroom)

    return {"available_classrooms": available_classrooms, "booked classrooms": booked_classrooms}


# * GET: HÄMTA EN BOKNING
@app.get("/bookings/{booking_id}")
async def get_booking(booking_id: int, name: str):
    """Hämtar bokningsinformationen för ett angivet boknings-id."""
    # Raisar HTTPExc 404 om bokningen inte existerar
    if booking_id not in bookings:
        raise HTTPException(status_code=404, detail="Booking ID does not exist!")
    # Raisar HTTPExc 403 om namnet inte stämmer överens med namnet på bokningen
    elif not bookings[booking_id]["name"].lower() == name.lower():
        raise HTTPException(status_code=403, detail="You do not have permission to view this booking.")

    return bookings[booking_id]


# * POST: SKAPA EN NY BOKNING
@app.post("/create_booking")
async def create_booking(booking: Booking):
    """Skapar en ny bokning."""

    # Kontrollerar att tidsintervallet på bokningen är minst en timme lång
    duration = booking.end_time - booking.start_time
    if duration < timedelta(hours=1):
        raise HTTPException(status_code=422, detail="Booking must be at least one hour long!")

    # Kontrollera överlappande bokningar i samma klassrum
    for existing_booking in bookings.values():
        if existing_booking["classroom"] == booking.classroom:
            existing_start_time = datetime.fromisoformat(existing_booking["start_time"])
            existing_end_time = datetime.fromisoformat(existing_booking["end_time"])
            # Kolla om tidsintervallet överlappar
            if not (existing_end_time <= booking.start_time or existing_start_time >= booking.end_time):
                raise HTTPException(status_code=409, detail="The classroom is already booked during the specified time.")

    # Generera ett slumpmässigt unikt 8-siffrigt boknings-ID
    booking_id = random.randint(10000000, 99999999)
    while booking_id in bookings:
        booking_id = random.randint(10000000, 99999999)

    booking_id = booking_id = random.randint(10000000, 99999999)  # Genererar ett slumpmässigt åttasiffrigt boknings-id

    # Sparar bokningen i 'bookings'-dictionaryn
    bookings[booking_id] = {
        "id": booking_id,
        "name": booking.name,
        "classroom": booking.classroom,
        "start_time": booking.start_time.isoformat(),  # Konverterar till string eftersom att det är ett datetime värde
        "end_time": booking.end_time.isoformat(),  # Konverterar till string eftersom att det är ett datetime värde
    }

    return bookings[booking_id]


# * PUT: ÄNDRA EN BOKNING
@app.put("/bookings/{booking_id}/change_booking")
async def change_booking(booking_id: int, updated_booking: UpdateBooking):
    """Ändra bokningsinformationen för en bokning."""
    # Raisar HTTPExc 404 om bokningen inte existerar
    if not bookings[booking_id]:
        raise HTTPException(status_code=404, detail="Booking does not exist!")

    # Konverterar datan till dictionary data och exkluderar null values så att de inte skriver över existerande bokningsdata med None
    new_data = updated_booking.model_dump(exclude_unset=True)

    # Slår ihop gamla datan med nya datan för att validera det
    merged_booking = bookings[booking_id].copy()  # Skapar en kopia av den gamla bokningen
    merged_booking.update(new_data)  # Uppdaterar kopian med nya datan

    # Validerar den nya datan
    merged_start_time: datetime = merged_booking["end_time"]
    merged_end_time: datetime = merged_booking["start_time"]

    # Kontrollerar att tidsintervallet på nya datan är minst en timme lång
    duration = merged_start_time - merged_end_time
    if duration < timedelta(hours=1):
        raise HTTPException(status_code=422, detail="Booking must be at least one hour long!")

    # Loopar genom alla existerande bokningar
    for id, existing_booking in bookings.items():
        # If sats som utesluter id:t som hanteras samt filtrerar fram alla bokningar som gjorts i samma klassrum
        if id != booking_id and existing_booking["classroom"] == merged_booking["classroom"]:
            other_start_time = datetime.fromisoformat(existing_booking["start_time"])  # Sparar tidigare boknings starttid
            other_end_time = datetime.fromisoformat(existing_booking["end_time"])  # Sparar tidigare boknings sluttid

            # Kontrollerar att nya datan inte överlappar med en annan bokning, raisar HTTPExc 409 om den överlappar
            if not (merged_start_time <= other_start_time or merged_end_time >= other_end_time):
                raise HTTPException(status_code=409, detail="Classroom already booked during the specified time.")

    bookings[booking_id].update(new_data)  # Lägger till den uppdaterade datan om valideringen gick bra
    return bookings[booking_id]


# * DELETE: TA BORT EN BOKNING
@app.delete("/bookings/{booking_id}")
async def delete_booking(booking_id: int):
    """Tar bort en bokning."""
    # Raisar HTTPExc 404 om bokningen inte existerar
    if booking_id not in bookings:
        raise HTTPException(status_code=404, detail="Booking ID does not exist!")

    del bookings[booking_id]
