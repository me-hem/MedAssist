import os
import sqlite3
from pathlib import Path
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types
from elevenlabs.client import ElevenLabs

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "medassist.db"

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

elevenlabs = ElevenLabs(
    api_key=os.getenv("ELEVENLABS_API_KEY")
)

AUDIO_DIR = BASE_DIR / "audio"
AUDIO_DIR.mkdir(exist_ok=True)

def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = get_connection()

    connection.execute("""
    CREATE TABLE IF NOT EXISTS medicines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        medicine_name_english TEXT NOT NULL,
        brand_name_english TEXT NOT NULL,
        medicine_name_hindi TEXT NOT NULL,
        brand_name_hindi TEXT NOT NULL,
        image_path TEXT NOT NULL,
        verified INTEGER NOT NULL DEFAULT 0
    )
    """)

    connection.execute("""
    CREATE TABLE IF NOT EXISTS schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        medicine_id INTEGER NOT NULL,
        time TEXT NOT NULL,
        dose_text TEXT NOT NULL,
        enabled INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY (medicine_id) REFERENCES medicines(id)
    )
    """)

    connection.commit()
    connection.close()

def add_medicine(medicine_name, brand_name, medicine_name_hindi,brand_name_hindi,image_path,):
    connection = get_connection()

    cursor = connection.execute(
        """
        INSERT INTO medicines
        (medicine_name_english, brand_name_english, medicine_name_hindi, brand_name_hindi, image_path, verified)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            medicine_name,
            brand_name,
            medicine_name_hindi,
            brand_name_hindi,
            image_path,
            1,
        ),
    )

    connection.commit()
    medicine_id = cursor.lastrowid
    connection.close()

    return medicine_id

def add_schedule(medicine_id, time, dose_text):
    connection = get_connection()

    cursor = connection.execute(
        """
        INSERT INTO schedules
        (medicine_id, time, dose_text, enabled)
        VALUES (?, ?, ?, ?)
        """,
        (
            medicine_id,
            time,
            dose_text,
            1,
        ),
    )

    connection.commit()
    schedule_id = cursor.lastrowid
    connection.close()

    return schedule_id

def create_hindi_reminder_text(
    medicine_name_hindi,
    dose_text,
    time,
):
    prompt = f"""
        Create one short, natural Hindi sentence for a medication reminder.
        These values have already been verified by the caregiver:

        Medicine name: {medicine_name_hindi}
        Dose: {dose_text}
        Time: {time}

        Rules:
        - Do NOT change the medicine name.
        - Do NOT change the dose.
        - Do NOT change the time.
        - Do NOT give medical advice.
        - Do NOT add any information.
        - Convert English numbers into natural Hindi words.
        - Convert English medicine units into natural Hindi speech.
        - For example, "1 Tablet" should become "एक टैबलेट".
        - Convert a 24-hour time such as "09:00" into natural spoken Hindi such as "सुबह के नौ बजे".
        - "21:30" should become natural spoken Hindi such as "रात के साढ़े नौ बजे".
        - Return ONLY the Hindi sentence.
        - Do not use quotation marks.
        """

    response = client.models.generate_content(
        model="gemma-4-26b-a4b-it",
        contents=prompt,
    )

    return response.text.strip()

def generate_reminder_audio(schedule_id, medicine_name_hindi,dose_text, time,):
    reminder_text = create_hindi_reminder_text(
        medicine_name_hindi=medicine_name_hindi,
        dose_text=dose_text,
        time=time,
    )

    audio = elevenlabs.text_to_speech.convert(
        text=reminder_text,
        voice_id=os.getenv("ELEVENLABS_VOICE_ID"),
        model_id="eleven_flash_v2_5",
        output_format="mp3_44100_128",
    )

    audio_path = AUDIO_DIR / f"schedule_{schedule_id}.mp3"

    with open(audio_path, "wb") as audio_file:
        for chunk in audio:
            audio_file.write(chunk)

    return audio_path

def analyze_medicine(image_path):
    with open(image_path, "rb") as image_file:
        image_bytes = image_file.read()

    response = client.models.generate_content(
        model="gemma-4-26b-a4b-it",
        contents=[
            types.Part.from_bytes(
                data=image_bytes,
                mime_type="image/jpeg",
            ),
            """
            Analyze this medicine package image.

            Extract the medicine information visibly printed on the package.

            Return ONLY valid JSON.
            Do not use markdown or code fences.

            The JSON must contain exactly these fields:

            {
                "medicine_name_english": "",
                "brand_name_english": "",
                "medicine_name_hindi": "",
                "brand_name_hindi": ""
            }

            medicine_name_english:
            The generic/active medicine name printed on the package.
            For combination medicines, include all active medicine names.

            brand_name_english:
            The commercial/brand name printed on the package.

            medicine_name_hindi:
            Write the medicine_name_english in Hindi script.
            Do not change the medical identity or meaning.

            brand_name_hindi:
            Write the brand_name_english in Hindi script.
            Do not invent a different brand name.

            Use only information visibly printed on the package for the English fields.
            Do not infer dosage, timing, medical advice, or treatment instructions.
            If something is not readable, return an empty string.
            """
        ],
    )

    text = response.text.strip()

    if text.startswith("```"):
        text = text.replace("```json", "", 1)
        text = text.replace("```", "", 1)
        text = text.strip()

    return json.loads(text)

