🏎️ F1 Race Vision

A real-time Formula 1 race replay simulator built using Python, Pygame, and FastF1, designed to visualize telemetry data and recreate dynamic Grand Prix action.

📌 Overview

F1 Race Vision brings Formula 1 telemetry to life by replaying races with accurate car positions, live timing gaps, and driver-specific data — all rendered on a dynamically generated track layout.

Inspired by Tom Shaw’s race replay project, this version is built fully from scratch, focusing on performance, precision, and an immersive visualization experience.

🚀 Key Features
🟦 Real-Time Race Replay

Cars move according to live telemetry (X/Y coordinates).

Smooth interpolation for frame-by-frame motion.

🟦 Live Leaderboard

Displays real-time positions and sub-second time gaps.

Updates automatically as the race progresses.

🟦 Driver Telemetry Panel

Speed

Gear

DRS Status

Tyre Compound

Car Color / Driver Initials

🟦 Dynamic Track Rendering

Circuit layout generated directly from coordinates.

Scaled & centered to fit display size.

Clean and accurate visual representation.

🟦 Race Selection Menu

Load any race from recent F1 seasons.

Automatically retrieves FastF1 cached or downloaded data.

🟦 Optimized Rendering Engine

Multi-threaded data loading.

Efficient update loops using Pygame.

Debug overlays for development.

📂 Project Structure
/F1-Race-Vision
│── main.py
│── replay.py
│── track_renderer.py
│── telemetry_loader.py
│── utils.py
│── assets/
│── README.md

🛠️ Tech Stack
Component	Technology
Language	Python
Visualization	Pygame
Telemetry Provider	FastF1
Tools	Pandas, Numpy, Threading
📦 Installation
1️⃣ Clone the repository
git clone https://github.com/yourusername/F1-Race-Vision.git
cd F1-Race-Vision

2️⃣ Create a virtual environment
python -m venv venv
source venv/bin/activate   # MacOS/Linux
venv\Scripts\activate      # Windows

3️⃣ Install dependencies
pip install -r requirements.txt

4️⃣ Run the program
python main.py

📥 FastF1 Cache Setup

FastF1 downloads heavy telemetry files the first time you load a session.
To speed up future loads, the data is cached automatically in:

/YourUser/AppData/Local/Temp/FastF1


You can delete old seasons or pre-download races if needed.

📸 Screenshots (Add your images here)

Replace these placeholder lines with real images.

Race replay view

Live leaderboard

Driver telemetry overlay

Track rendering

🧠 What I Learned

Telemetry parsing & data pipelines

Real-time rendering & interpolation

Performance optimization with threads

Scaling coordinate systems to screens

Building game-style simulation loops

🙌 Credits

A huge thanks to Tom Shaw, whose race replay project inspired this one.
