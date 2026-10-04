# MedAssist

MedAssist is a voice-medication reminder designed for people who cannot reliably read or remember written medicine instructions.

**See the medicine. Hear the reminder. Take the medicine.**

## How it works

1. Caregiver uploads a medicine package photo.
2. Gemma reads the medicine and brand name from the package.
3. Caregiver verifies and edits the information.
4. Caregiver sets the dose and reminder time.
5. Gemma creates a short, natural Hindi reminder.
6. ElevenLabs converts the reminder into Hindi speech.
7. At the scheduled time, the patient sees the medicine image and hears the reminder.
8. If multiple medicines are due together, they are shown one by one.

The medicine dose and schedule are always provided and verified by the caregiver. AI does not decide the dose or timing.

## Tech Stack

- Python
- FastAPI
- SQLite
- HTML, CSS, JavaScript
- Gemma
- ElevenLabs


## Setup

Clone the repository:

```bash
git clone https://github.com/me-hem/MedAssist
cd medassist
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it.

Linux/macOS:

```bash
source venv/bin/activate
```

Windows:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file:

```env
GEMINI_API_KEY=your_gemini_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
ELEVENLABS_VOICE_ID=your_elevenlabs_voice_id
```

Run the application:

```bash
uvicorn app:app --reload
```

Open:

```text
http://127.0.0.1:8000
```
