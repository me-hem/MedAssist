import shutil
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from datetime import datetime
from fastapi.responses import FileResponse
from pathlib import Path
from service import (
    init_db,
    add_medicine,
    add_schedule,
    analyze_medicine,
    generate_reminder_audio,
)

app = FastAPI(title="MedAssist")

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR),
    name="static",
)


AUDIO_DIR = BASE_DIR / "audio"
AUDIO_DIR.mkdir(exist_ok=True)

app.mount(
    "/audio",
    StaticFiles(directory=AUDIO_DIR),
    name="audio",
)

app.mount(
    "/uploads",
    StaticFiles(directory=UPLOAD_DIR),
    name="uploads",
)

init_db()


@app.get("/")
def home():
    return FileResponse(BASE_DIR / "index.html")

@app.post("/analyze")
def analyze_uploaded_medicine(image: UploadFile = File(...)):
    image_path = UPLOAD_DIR / image.filename

    with image_path.open("wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    result = analyze_medicine(image_path)

    return {
        "image": str(image_path),
        "analysis": result,
    }

@app.post("/medicines/save")
def save_medicine(
    medicine_name_english: str = Form(...),
    brand_name_english: str = Form(...),
    medicine_name_hindi: str = Form(...),
    brand_name_hindi: str = Form(...),
    image_path: str = Form(...),
    time: str = Form(...),
    dose_text: str = Form(...),
):
    from service import add_medicine, add_schedule

    medicine_id = add_medicine(
        medicine_name=medicine_name_english,
        brand_name=brand_name_english,
        medicine_name_hindi=medicine_name_hindi,
        brand_name_hindi=brand_name_hindi,
        image_path=image_path,
    )

    schedule_id = add_schedule(
        medicine_id=medicine_id,
        time=time,
        dose_text=dose_text,
    )

    audio_path = generate_reminder_audio(
        schedule_id=schedule_id,
        medicine_name_hindi=medicine_name_hindi,
        dose_text=dose_text,
        time=time,
    )

    return {
        "success": True,
        "medicine_id": medicine_id,
        "schedule_id": schedule_id,
        "audio": f"/audio/{audio_path.name}",
    }

@app.get("/patient/current")
def patient_current():
    from service import get_connection

    current_time = datetime.now().strftime("%H:%M")

    connection = get_connection()

    rows = connection.execute(
        """
        SELECT
            s.id AS schedule_id,
            s.time,
            s.dose_text,
            m.id AS medicine_id,
            m.medicine_name_english,
            m.brand_name_english,
            m.medicine_name_hindi,
            m.brand_name_hindi,
            m.image_path
        FROM schedules s
        JOIN medicines m
            ON m.id = s.medicine_id
        WHERE s.enabled = 1
          AND s.time = ?
        ORDER BY s.id ASC
        """,
        (current_time,),
    ).fetchall()

    connection.close()

    if not rows:
        return {
            "due": False,
            "time": current_time,
            "medicines": [],
        }

    medicines = []

    for row in rows:
        image_filename = Path(row["image_path"]).name

        medicines.append(
            {
                "schedule_id": row["schedule_id"],
                "medicine_id": row["medicine_id"],
                "medicine_name_english": row["medicine_name_english"],
                "brand_name_english": row["brand_name_english"],
                "medicine_name_hindi": row["medicine_name_hindi"],
                "brand_name_hindi": row["brand_name_hindi"],
                "dose_text": row["dose_text"],
                "time": row["time"],
                "image": f"/uploads/{image_filename}",
                "audio": f"/audio/schedule_{row['schedule_id']}.mp3",
            }
        )

    return {
        "due": True,
        "time": current_time,
        "medicines": medicines,
    }