# 🎧 AI Fitness Coach - Audio Workout Generator

This is a FastAPI-powered AI Fitness Coach that generates personalized audio-based workout plans using [GROQ LLM](https://groq.com) and Microsoft Edge TTS. Users provide a fitness profile and receive a structured workout plan along with an audio file they can play or download directly.

---

## 🚀 Features

- 🧠 Generates smart, LLaMA-3-based workout plans via GROQ API.
- 🔊 Converts workouts into motivational audio with Microsoft Edge TTS.
- 📥 Downloadable `.mp3` files for offline use.
- 🎧 Play audio directly from browser (via Swagger `/docs` or API).
- 🔄 Temporary audio file cleanup utility.
- 🧪 Ready-to-use API testing via Swagger UI.

---

## 🛠️ Setup & Installation

### Prerequisites

- Python 3.10+
- Git
- A valid [GROQ API Key](https://console.groq.com/)
  
### Clone the Repository

```bash
git clone https://github.com/adibmahmud007/ai-fitness-agent.git
cd ai-fitness-agent
```
### Create .env File
Create a .env file in the root directory and add your GROQ API key:
```bash
GROQ_API_KEY=your_groq_api_key_here
```
🔐 You can get your key from: https://console.groq.com/

### Run the FastAPI Server
Run the app using uvicorn:
```bash
uvicorn main:app --reload --port 9000
```
Then open your browser and go to:
👉 http://localhost:9000/docs to test the endpoints via Swagger UI.

### Sample Input
POST /generate-plan

json
```bash
{
  "mission": "Build-Strength",
  "time_commitment": "15 minute",
  "gear": "Dumbbells",
  "squad": "Warrior"
}
```
### Sample Output
json
```bash
{
  "status": "success",
  "workout_plan": [
    "Step 1: Do 3 sets of 10 push-ups",
    "Step 2: Perform 3 sets of 15 squats",
    "Step 3: Finish with a 1-minute plank"
  ],
  "motivational_text": "Great job! You're getting stronger every day!",
  "audio_info": {
    "filename": "workout_Build-Strength_15-minute_abcd1234.mp3",
    "download_url": "/download-audio/workout_Build-Strength_15-minute_abcd1234.mp3",
    "play_url": "/play-audio/workout_Build-Strength_15-minute_abcd1234.mp3"
  },
  "formatted_text": "Your 15 minute build strength workout:\n\nFirst, we'll do 3 sets of 10 push-ups...\n\nMotivation for today:\nGreat job! You're getting stronger every day!"
}
```
## ⚙️ How It Works 

1. You send a `POST` request to `/generate-plan` with your workout preferences (goal, time, gear, squad).
2. The app uses GROQ's LLaMA3 model to create a personalized workout plan and motivational message(Shown in the ***Sample Output***).
3. It converts that plan to audio using Microsoft Edge TTS (Shown in the `audio-info` in the ***Sample Output***.
4. The response includes a generated audio filename and two URLs:
   - `/play-audio/{filename}` → to **play** the audio in browser
   - `/download-audio/{filename}` → to **download** the `.mp3` file
5. We need to pass the filename (obtained from the `POST API` response in the `audio-info` section) to the `/play-audio` and `/download-audio` APIs, which utilize `GET` requests, allowing us to ***hear and download*** the audio.
6. Formatted_Text is not mentioned in the requirement, but I have used it so that we get a clearly formatted text to generate the audio seamlessly.

