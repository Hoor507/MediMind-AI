# MediMind AI — Smart Symptom & Emergency Assistant

A local educational web application demonstrating a Groq-powered symptom conversation, structured response validation, basic emergency warning checks, and a responsive dark dashboard.

> **Medical safety:** This project is not a medical device and does not provide a diagnosis. It is not clinically validated. If you suspect an emergency, call your local emergency number immediately. In Pakistan, Rescue 1122 may be available. Do not delay urgent care to use this application.

## Features

- Flask/Python backend with the official Groq SDK.
- Premium dark responsive UI with symptom examples, loading animation, and subtle magnetic buttons.
- Structured JSON response: urgency, possible explanations, uncertainties, warning signs, first-aid guidance, care recommendation, follow-up questions.
- Backend emergency override for selected critical warning phrases.
- Basic input validation and per-IP request limit.
- No database and no deliberate permanent storage of symptom records.
- API key kept in `.env` on the backend.
- Linux and Windows instructions below.

## Project structure

```text
MediMind-AI/
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── templates/
│   └── index.html
├── static/
│   ├── css/style.css
│   └── js/app.js
└── tests/
    └── test_app.py
```

## Requirements

- Python 3.10+ recommended.
- Internet access for the Groq API.
- A Groq API key from the official console: https://console.groq.com/keys
- A model currently enabled for your Groq account. The default is `openai/gpt-oss-120b`; if Groq changes availability, check its model catalog at https://console.groq.com/docs/models and change `GROQ_MODEL` in `.env`.

## Linux setup (Ubuntu/Zorin OS)

Open a terminal and run:

```bash
mkdir -p ~/Projects/MediMind-AI
cd ~/Projects/MediMind-AI
```

Extract the ZIP here, or change to the folder where you extracted the project. Then:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Open `.env` in VS Code and replace `your_groq_api_key_here` with your real key. Keep the key private and never paste it into frontend files or commit `.env` to Git. You can create a key at https://console.groq.com/keys.

Run:

```bash
python app.py
```

Open http://127.0.0.1:5000 in your browser. Stop the server with `Ctrl+C`. To restart, activate the environment again (`source .venv/bin/activate`), return to the project directory, and run `python app.py`.

If `venv` creation fails on Debian/Ubuntu/Zorin, install the venv package with `sudo apt install python3-venv`, then retry.

## Windows setup (PowerShell)

Open PowerShell in the extracted `MediMind-AI` folder:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and add your Groq key, then run:

```powershell
python app.py
```

Visit http://127.0.0.1:5000. Stop with `Ctrl+C`. If PowerShell blocks activation, use Command Prompt instead:

```bat
py -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
python app.py
```

## Configuration

`.env` values:

```dotenv
GROQ_API_KEY=your_real_key
GROQ_MODEL=openai/gpt-oss-120b
FLASK_SECRET_KEY=replace_with_a_long_random_local_secret
```

The backend reads these variables only. Never expose the Groq key to browser JavaScript. If the model is unsupported, visit the current Groq model catalog and set `GROQ_MODEL` to an available chat model. The app returns an error if the API is unavailable; it does not fabricate an assessment.

## Tests

Install dependencies and run:

```bash
python -m unittest discover -s tests -v
```

Tests cover empty input, invalid request format, emergency override, invalid urgency levels, and missing API key behavior. They do not validate medical accuracy or replace clinical testing.

## 3–5 minute university demo plan

Use fictional, educational test scenarios only. These are not medically validated test cases, and the model response may vary.

1. **Mild scenario:** “I've had a mild sore throat and runny nose since yesterday. I can breathe normally and can drink fluids.”
2. **Needs prompt assessment scenario:** “I have a fever that has lasted several days and I feel increasingly weak.”
3. **Emergency override demonstration:** “I have severe difficulty breathing right now.” The backend should show its emergency warning even if the model call fails. Do not use a real emergency as a demo.

Show the landing page, click a sample chip, enter optional context, submit, explain the urgency card and possible explanations, then show the How MediMind Works section and describe the backend safety override.

## Privacy and limitations

- No database is used. The app does not intentionally save symptom assessments permanently; limited conversation context is held in Flask's signed browser session cookie for follow-up. Clearing the assessment clears the app's session context but does not delete third-party records or server/browser infrastructure logs.
- When Analyze is used, symptom text and selected optional context are sent to Groq for processing. Review Groq's terms and privacy documentation before entering sensitive information.
- This is a demonstration-level keyword override, not comprehensive emergency detection. It can miss emergencies or flag terms without context. Do not rely on it to rule out urgent illness.
- The local Flask development server binds to `127.0.0.1`; do not expose it publicly.
- The UI's animated processing stages are illustrative and do not mean that a separate medical database was queried.
- No personalized medication dosing, antibiotics, or prescription regimens are provided intentionally.

## Troubleshooting

- **API key needed:** check `.env` exists in the project root and `GROQ_API_KEY` has a valid key.
- **Authentication error:** create/check your key in the Groq console.
- **Model error:** update `GROQ_MODEL` to a currently supported model in the Groq catalog.
- **Rate limit:** wait and retry later.
- **Backend unavailable:** ensure the terminal running `python app.py` is still open.
- **Port in use:** set `PORT=5001` in `.env`, then open `http://127.0.0.1:5001`.

## Safety note

MediMind AI is an educational project only. It cannot confirm or exclude diseases. Seek professional advice for health concerns and emergency care for severe or rapidly worsening symptoms.
