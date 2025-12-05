# F1 Race Vision

F1 Race Vision is a Python-based desktop application that provides a sophisticated 2D replay visualization of Formula 1 races. Using the `fastf1` library to fetch official telemetry data and `pygame` for the graphical interface, it allows users to re-watch races with detailed insights into driver performance, track positions, and timing information.

!F1 Race Vision Screenshot *(Screenshot placeholder)*

---

## Features

-   **Interactive Race Menu**: A sleek, F1-themed UI to select a race from any available year.
-   **2D Track Visualization**: Displays the circuit layout with all cars represented as colored dots moving in real-time.
-   **Live Leaderboard**: A continuously updated ranking of drivers, showing position, name, and current tyre compound.
-   **Detailed Telemetry Panel**: Select any driver to view their real-time speed, gear, and DRS status.
-   **Timing Information**: Displays the current lap number, total laps, and sector times for the selected driver.
-   **Playback Controls**:
    -   Play, pause, and adjust playback speed.
    -   Seek forward or backward in the race timeline.
    -   Easily switch between drivers to follow the action.
-   **Data Caching**: Utilizes `fastf1`'s caching mechanism to store telemetry data locally, ensuring fast loading times for subsequent viewings.

---

## Requirements

-   Python 3.8+
-   `pygame`
-   `fastf1`

---

## Installation & Usage

1.  **Clone the repository:**
    
    ```bash
    git clone <your-repository-url>cd F1RaceVision
    ```
    
2.  **Install the required Python libraries:**
    
    ```bash
    pip install pygame fastf1
    ```
    
3.  **Run the application:**
    
    ```bash
    python main.py
    ```
    
4.  **Select a Race**: Use the on-screen menu to choose a year and a Grand Prix. The application will then download and cache the necessary data (this may take a moment on the first run for a specific race).
    
5.  **Enjoy the replay!**
    

---

## Replay Controls

Key

Action

`Spacebar`

Play / Pause the replay

`Up Arrow`

Increase playback speed (up to 8x)

`Down Arrow`

Decrease playback speed (down to 0.25x)

`Right Arrow`

Seek forward 5 seconds

`Left Arrow`

Seek backward 5 seconds

`]` (Right Bracket)

Select the next driver in the ranking

`[` (Left Bracket)

Select the previous driver in the ranking

---

## Project Structure

```
F1RaceVision/├── .fastf1-cache/      # Stores cached FastF1 telemetry data├── core/│   └── telemetry_loader.py # Handles fetching and parsing race data├── ui/│   ├── menu.py         # Implements the race selection menu│   └── replay.py       # Implements the main replay visualization screen└── main.py             # Main application entry point
```