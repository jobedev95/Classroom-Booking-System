from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator, Field
from datetime import timedelta, date, time, datetime
from typing import Optional, List, Any
import random

app = FastAPI()

bookings: dict[int, dict[str, Any]] = {
    1: {"id": 1, "name": "Joel", "classroom": "A401", "booking_date": date(2024, 11, 12), "start_time": "08:30", "end_time": "10:00"},
    2: {"id": 2, "name": "Sami", "classroom": "C301", "booking_date": date(2024, 11, 12), "start_time": "08:30", "end_time": "10:00"},
    3: {"id": 3, "name": "Sami", "classroom": "B204", "booking_date": date(2024, 11, 12), "start_time": "08:30", "end_time": "10:00"},
    4: {"id": 4, "name": "Karin", "classroom": "A401", "booking_date": date(2024, 11, 12), "start_time": "10:00", "end_time": "15:00"},
}

# fmt: off
classrooms: list[str] = [
    "A101", "A102", "A103", "A104", "B101", "B102", "B103", "B104",
    "C101", "C102", "C103", "C104", "A201", "A202", "A203", "A204",
    "B201", "B202", "B203", "B204", "C201", "C202", "C203", "C204",
    "A301", "A302", "A303", "A304", "B301", "B302", "B303", "B304",
    "C301", "C302", "C303", "C304", "A401", "A402", "A403", "A404",
    "B401", "B402", "B403", "B404", "C401", "C402", "C403", "C404"
]
# fmt: on


class Booking(BaseModel):
    """BaseModel för att skapa nya bokningar."""

    id: Optional[int] = None  # Optional eftersom att ID:t kommer att genereras automatiskt vid skapandet av bokningen
    name: str
    classroom: str
    booking_date: date = Field(examples=["2024-11-07"])
    start_time: str = Field(examples=["07:00"])  # Sätter exempelvärde på starttiden till 07:00
    end_time: str = Field(examples=["14:00"])  # Sätter exempelvärde på starttiden till 14:00

    @field_validator("classroom")
    def validate_classroom(cls, value) -> str:
        """Validerar att det angivna klassrumsnamnet existerar i klassrumslistan och returnerar det i versaler."""

        if value.upper() not in classrooms:
            raise ValueError("Classroom does not exist.")
        return value.upper()

    @field_validator("booking_date")
    def validate_booking_date(cls, value) -> date:
        """Validerar att det angivna bokningsdatumet inte är ett datum som redan har passerat."""

        if value < date.today():
            raise ValueError("The booking date cannot be set earlier than the current date.")
        return value

    @field_validator("end_time")
    def validate_time_string(cls, value, info) -> str:
        """Validerar båda tidssträngarna för att säkerställa att de är i formatet 'HH:MM' samt att
        bokningen är minst 1 timme lång, inte är i det förflutna, och att det är inom skolans öppettider."""

        start_time = info.data.get("start_time")  # Hämtar starttiden

        # Validerar att tid-strängarna är i formatet 'HH:MM'
        convert_to_time_objects(start_time, value)

        # Hämtar bokningsdatumet (som vid en PUT-request också kan vara None)
        booking_date = info.data.get("booking_date")

        # Validerar att bokningen är minst 1 timme lång, inte är i det förflutna, och att det är inom skolans öppettider
        if booking_date is not None:
            validate_times(booking_date, start_time, value)

        return value


class UpdateBooking(Booking):
    """BaseModel för att ändra på en bokning. Den ärver alla attribut och validatorer från Booking-modellen."""

    id: Optional[int] = Field(default=None, exclude=True)  # ID exkluderas eftersom att den inte får ändras vid ändring av en bokning
    name: str = Field(default=None)
    classroom: str = Field(default=None)
    booking_date: date = Field(default=None)
    start_time: str = Field(default=None, examples=["07:00"])  # Sätter exempelvärde på starttiden till 07:00
    end_time: str = Field(default=None, examples=["14:00"])  # Sätter exempelvärde på starttiden till 14:00


def get_unavailable_classrooms(search_date: date, start_time_str: str, end_time_str: str, exclude_id: int | None = None) -> list[str]:
    """Returnerar en lista med klassrum som är bokade under ett angivet tidsintervall.
    Om ett ID anges som fjärde argument kommer den bokningen att exkluderas från listan."""

    # Konvertera start- och sluttidssträngarna till time-objekt
    start_time, end_time = convert_to_time_objects(start_time_str, end_time_str)

    unavailable_classrooms: list[str] = []  # Lista som ska lagra alla klassrum som bokats under det angivna tidsintervallet

    # Loopar igenom alla tillgängliga bokningar
    for id, existing_booking in bookings.items():
        # Hoppar över den bokning som matchar det angivna ID:t om ett exclude_id har angetts
        if exclude_id is not None:
            if exclude_id == id:
                continue

        # Kontrollerar om det finns en bokning under samma datum
        if existing_booking["booking_date"] == search_date:
            # Konverterar start- och sluttidssträngarna av existerande bokning till time-objekt
            existing_start_time, existing_end_time = convert_to_time_objects(existing_booking["start_time"], existing_booking["end_time"])

            # Lägger till klassrummet i listan 'unavailable_classrooms' om tidsintervallet överlappar med en existerande bokning
            if existing_end_time > start_time and existing_start_time < end_time:
                unavailable_classrooms.append(existing_booking["classroom"].upper())

    return unavailable_classrooms


def convert_to_time_objects(start_time_str: str, end_time_str: str) -> tuple[time, time]:
    """Konverterar start- och sluttidssträngar i formatet "HH:MM" till time-objekt.
    Returnerar en tuple med de två time-objekten. Resulterar det i HTTPExc 422 om tiderna är i fel format."""

    # Försöker konvertera tidsträngarna till time-objekt i formatet "HH:MM"
    try:
        start_time = datetime.strptime(start_time_str, "%H:%M").time()
        end_time = datetime.strptime(end_time_str, "%H:%M").time()
    except (ValueError, TypeError):
        # Om tiden inte är i det förväntade formatet 'HH:MM' resulterar det i HTTPExc 422
        raise HTTPException(status_code=422, detail="The time must be a string specified in the format 'HH:MM' and be a valid time.")
    return (start_time, end_time)


def validate_times(search_date: date, start_time_str: str, end_time_str: str) -> None:
    """Validerar att bokningen är minst en timme lång och att tiderna inte redan passerat
    om bokningen görs samma dag. Validerar också att tiderna är inom tillåtna tidsramar.
    Misslyckad validering resulterar i HTTPExc 422."""

    # Konverterar start- och sluttidssträngarna till time-objekt
    start_time, end_time = convert_to_time_objects(start_time_str, end_time_str)

    # Skapar time-objekt med skolans öppettider
    school_start = time(7, 0)
    school_end = time(18, 0)

    # Kontrollerar att start- och sluttiden är inom skolans öppettider
    if start_time < school_start or end_time > school_end:
        raise HTTPException(
            status_code=422,
            detail="The start and end time must be within the operational hours of the school, between 07:00-18:00.",
        )

    # Kontrollerar att angivna tider är precis på hel- eller halvtimme
    if not ((start_time.minute == 0 or start_time.minute == 30) and (end_time.minute == 0 or end_time.minute == 30)):
        raise HTTPException(status_code=422, detail="The given times must be entered at hour or half-hour intervals ('xx:00' or 'xx:30')")

    # Kontrollerar att start- och sluttiden inte redan har passerat om bokningsdatumet är dagens datum
    if search_date == date.today():
        if start_time < datetime.now().time() or end_time < datetime.now().time():
            raise HTTPException(status_code=422, detail="The start time or end time cannot be set earlier than the current time.")

    # Skapar två datetime-objekt av start- och sluttiden genom att kombinera datum + starttid, samt datum + sluttid
    start_datetime = datetime.combine(search_date, start_time)
    end_datetime = datetime.combine(search_date, end_time)

    # Beräknar tidslängden och sparar den som ett timedelta-objekt
    duration = end_datetime - start_datetime

    # Kontrollerar att tidslängden är minst 1 timme lång
    if duration < timedelta(hours=1):
        raise HTTPException(status_code=422, detail="The time interval must be at least one hour long.")


# * GET: HÄMTAR ALLA KLASSRUMSNAMN FRÅN LISTAN
@app.get("/classrooms")
async def get_classrooms() -> list[str]:
    """Hämtar listan på alla klassrum i skolan."""

    return classrooms


# * GET: VISA TILLGÄNGLIGA KLASSRUM FÖR ETT ANGIVET TIDSINTERVALL
@app.get("/available-classrooms")
async def get_available_classrooms(search_date: date, start_time_str: str, end_time_str: str):
    """Visar alla tillgängliga och otillgängliga klassrum för ett angivet tidsintervall."""

    # Kontrollerar att sökdatumet inte är ett datum som redan har passerat
    if search_date < date.today():
        raise HTTPException(status_code=422, detail="The search date cannot be in the past. It must be current date or later.")

    # Validerar att sökningen är minst 1 timme lång, inte är i det förflutna, och att det är inom skolans öppettider
    validate_times(search_date, start_time_str, end_time_str)

    # Skapar en lista med alla bokade klassrum för det angivna tidsintervallet
    unavailable_classrooms = get_unavailable_classrooms(search_date, start_time_str, end_time_str)

    # Skapar en lista med alla tillgängliga klassrum
    available_classrooms = []
    for classroom in classrooms:  # Loopar genom alla klassrum
        # Om ett klassrum inte är bokat läggs det till i 'available_classroooms'-listan
        if classroom.upper() not in unavailable_classrooms:
            available_classrooms.append(classroom.upper())

    return {"available_classrooms": available_classrooms, "unavailable_classrooms": unavailable_classrooms}


# * GET: HÄMTA EN BOKNING
@app.get("/bookings/{booking_id}")
async def get_booking(booking_id: int, name: str):
    """Hämtar bokningsinformationen för ett angivet boknings-id."""

    # Om bokningen inte existerar resulterar det i HTTPExc 404
    if not bookings.get(booking_id):
        raise HTTPException(status_code=404, detail="Booking ID does not exist.")

    # Om namnet inte stämmer överens med namnet på bokningen resulterar det i HTTPExc 403
    elif not bookings[booking_id]["name"].lower() == name.lower():
        raise HTTPException(status_code=403, detail="You do not have permission to view this booking.")

    return bookings[booking_id]


# * POST: SKAPA EN NY BOKNING
@app.post("/create_booking")
async def create_booking(booking: Booking):
    """Skapar en ny bokning."""

    # Skapar en lista med alla bokade klassrum för det angivna tidsintervallet
    unavailable_classrooms: List[str] = get_unavailable_classrooms(booking.booking_date, booking.start_time, booking.end_time)

    # Kontrollerar ifall klassrummet som anges i bokningen redan är upptaget
    if booking.classroom.upper() in unavailable_classrooms:
        raise HTTPException(status_code=409, detail="The classroom is already booked during the specified time.")

    # Genererar ett slumpmässigt unikt 8-siffrigt boknings-ID
    booking_id = random.randint(10000000, 99999999)
    while booking_id in bookings:
        booking_id = random.randint(10000000, 99999999)

    # Sparar bokningen i 'bookings'-dictionaryn
    bookings[booking_id] = {
        "id": booking_id,
        "name": booking.name,
        "classroom": booking.classroom,
        "booking_date": booking.booking_date,
        "start_time": booking.start_time,
        "end_time": booking.end_time,
    }

    return bookings[booking_id]


# * PUT: ÄNDRA EN BOKNING
@app.put("/bookings/{booking_id}/change_booking")
async def change_booking(booking_id: int, updated_booking: UpdateBooking, name: str):
    """Ändra bokningsinformationen för en bokning."""

    # Om bokningen inte existerar resulterar det i HTTPExc 404
    if not bookings.get(booking_id):
        raise HTTPException(status_code=404, detail="Booking ID does not exist.")

    # Om namnet inte stämmer överens med namnet på bokningen resulterar det i HTTPExc 403
    elif not bookings[booking_id]["name"].lower() == name.lower():
        raise HTTPException(status_code=403, detail="You do not have permission to view this booking.")

    # Konverterar datan till dictionary data och exkluderar None-värden så att de inte skriver över existerande bokningsdata med None
    new_data = updated_booking.model_dump(exclude_unset=True)

    # Slår ihop gamla datan med nya datan för att förbereda det för validering
    new_booking = bookings[booking_id].copy()  # Skapar en kopia av den gamla bokningen
    new_booking.update(new_data)  # Uppdaterar kopian med nya datan

    # Validerar att bokningen är minst 1 timme lång, inte är i det förflutna, och att det är inom skolans öppettider
    validate_times(new_booking["booking_date"], new_booking["start_time"], new_booking["end_time"])

    # Skapar en lista med alla bokade klassrum för det angivna tidsintervallet men exkluderar den aktuella bokningen som ska uppdateras
    unavailable_classrooms: list[str] = get_unavailable_classrooms(
        new_booking["booking_date"], new_booking["start_time"], new_booking["end_time"], exclude_id=booking_id
    )

    # Kontrollerar ifall klassrummet som anges i den uppdaterade bokningen redan är upptaget
    if new_booking["classroom"].upper() in unavailable_classrooms:
        raise HTTPException(status_code=409, detail="Classroom already booked during the specified time.")

    bookings[booking_id].update(new_data)  # Lägger till den uppdaterade datan om valideringen går bra
    return bookings[booking_id]


# * DELETE: TA BORT EN BOKNING
@app.delete("/bookings/{booking_id}")
async def delete_booking(booking_id: int, name: str):
    """Tar bort en bokning."""

    # Om bokningen inte existerar resulterar det i HTTPExc 404
    if not bookings.get(booking_id):
        raise HTTPException(status_code=404, detail="Booking ID does not exist!")

    # Om namnet inte stämmer överens med namnet på bokningen resulterar det i HTTPExc 403
    if bookings[booking_id]["name"].lower() != name.lower():
        raise HTTPException(status_code=403, detail="You do not have permission to delete this booking.")

    del bookings[booking_id]
