from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, List, Optional
import asyncio
import random
import time

app = FastAPI()
@app.get("/")
def home():
    return {"status": "Tic Tac Toe WebSocket server is running"}


rooms: Dict[str, dict] = {}


def check_winner(board: List[Optional[int]], n: int):
    lines = []

    # rows & cols
    for i in range(n):
        lines.append([i * n + j for j in range(n)])
        lines.append([j * n + i for j in range(n)])

    # diagonals
    lines.append([i * n + i for i in range(n)])
    lines.append([(i + 1) * n - (i + 1) for i in range(n)])

    for line in lines:
        values = [board[i] for i in line]
        if values[0] is not None and all(v == values[0] for v in values):
            return values[0], line

    if None not in board:
        return "Draw", []

    return None, []


def ai_move(board):
    empty = [i for i, v in enumerate(board) if v is None]
    return random.choice(empty) if empty else None


@app.websocket("/ws/{room_id}")
async def ws_game(ws: WebSocket, room_id: str):
    await ws.accept()

    # Create room if not exists
    if room_id not in rooms:
        rooms[room_id] = {
            "players": [],
            "spectators": [],
            "names": [None, None],
            "board": [],
            "turn": 0,
            "wins": [0, 0],
            "grid": 3,
            "winner": None,
            "win_line": [],
            "timer": 15,
            "time_left": 15,
            "last_tick": time.time(),
            "ai_enabled": False
        }

    room = rooms[room_id]

    # Assign role
    if len(room["players"]) < 2:
        player_id = len(room["players"])
        room["players"].append(ws)
    else:
        room["spectators"].append(ws)
        player_id = -1

    try:
        while True:
            data = await ws.receive_json()

            if data["type"] == "join":
                if player_id != -1:
                    room["names"][player_id] = data["name"]

                if player_id == 0:
                    room["grid"] = data.get("grid", 3)
                    room["timer"] = data.get("timer", 15)
                    room["ai_enabled"] = data.get("ai", False)

                    room["board"] = [None] * (room["grid"] ** 2)
                    room["turn"] = 0
                    room["winner"] = None
                    room["win_line"] = []
                    room["time_left"] = room["timer"]
                    room["last_tick"] = time.time()

            if (
                data["type"] == "move"
                and player_id == room["turn"]
                and room["winner"] is None
            ):
                idx = data["index"]
                if 0 <= idx < len(room["board"]) and room["board"][idx] is None:
                    room["board"][idx] = player_id
                    winner, line = check_winner(room["board"], room["grid"])
                    if winner is not None:
                        room["winner"] = winner
                        room["win_line"] = line
                        if winner != "Draw":
                            room["wins"][winner] += 1
                    else:
                        room["turn"] = 1 - room["turn"]
                        room["time_left"] = room["timer"]
                        room["last_tick"] = time.time()

            if (
                room["ai_enabled"]
                and room["turn"] == 1
                and room["winner"] is None
                and len(room["players"]) == 1
            ):
                await asyncio.sleep(0.6)
                move = ai_move(room["board"])
                if move is not None:
                    room["board"][move] = 1
                    winner, line = check_winner(room["board"], room["grid"])
                    if winner is not None:
                        room["winner"] = winner
                        room["win_line"] = line
                        if winner != "Draw":
                            room["wins"][winner] += 1
                    else:
                        room["turn"] = 0
                        room["time_left"] = room["timer"]
                        room["last_tick"] = time.time()

            if room["winner"] is None:
                now = time.time()
                elapsed = int(now - room["last_tick"])
                if elapsed > 0:
                    room["time_left"] -= elapsed
                    room["last_tick"] = now

                    if room["time_left"] <= 0:
                        room["turn"] = 1 - room["turn"]
                        room["time_left"] = room["timer"]

            if data["type"] == "reset" and player_id == 0:
                room["board"] = [None] * (room["grid"] ** 2)
                room["turn"] = 0
                room["winner"] = None
                room["win_line"] = []
                room["time_left"] = room["timer"]
                room["last_tick"] = time.time()

            payload = {
                "board": room["board"],
                "turn": room["turn"],
                "names": room["names"],
                "wins": room["wins"],
                "winner": room["winner"],
                "win_line": room["win_line"],
                "grid": room["grid"],
                "time_left": room["time_left"],
                "ai": room["ai_enabled"]
            }

            for client in room["players"] + room["spectators"]:
                await client.send_json(payload)

    except WebSocketDisconnect:
        if player_id != -1:
            if ws in room["players"]:
                room["players"].remove(ws)
        else:
            if ws in room["spectators"]:
                room["spectators"].remove(ws)

        room["board"] = [None] * (room["grid"] ** 2)
        room["turn"] = 0
        room["winner"] = None
        room["win_line"] = []
        room["time_left"] = room["timer"]

