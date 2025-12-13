from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict
import time

app = FastAPI()
rooms: Dict[str, dict] = {}

@app.get("/")
def home():
    return {"status": "Tic Tac Toe WebSocket server is running"}

def check_winner(board, n):
    lines = []

    for i in range(n):
        lines.append(board[i*n:(i+1)*n])
        lines.append([board[j*n+i] for j in range(n)])

    lines.append([board[i*n+i] for i in range(n)])
    lines.append([board[(i+1)*n-(i+1)] for i in range(n)])

    for idx, line in enumerate(lines):
        if line[0] and all(cell == line[0] for cell in line):
            return line[0], idx

    if None not in board:
        return "Draw", None

    return None, None


@app.websocket("/ws/{room_id}")
async def websocket_endpoint(ws: WebSocket, room_id: str):
    await ws.accept()

    if room_id not in rooms:
        rooms[room_id] = {
            "players": [],
            "spectators": [],
            "board": [None]*9,
            "turn": 0,
            "names": {},
            "wins": {"p1": 0, "p2": 0},
            "timer": 15,
            "last_move": time.time()
        }

    room = rooms[room_id]

    role = "spectator"
    if len(room["players"]) < 2:
        role = "player"
        room["players"].append(ws)
    else:
        room["spectators"].append(ws)

    try:
        while True:
            data = await ws.receive_json()

            if data["type"] == "join":
                room["names"][ws] = data["name"]

            if data["type"] == "move" and role == "player":
                idx = data["index"]
                if room["board"][idx] is None:
                    symbol = "X" if room["turn"] == 0 else "O"
                    room["board"][idx] = symbol
                    room["turn"] = 1 - room["turn"]
                    room["last_move"] = time.time()

                    winner, line = check_winner(room["board"], 3)
                    if winner == "X":
                        room["wins"]["p1"] += 1
                    elif winner == "O":
                        room["wins"]["p2"] += 1

                    payload = {
                        "board": room["board"],
                        "turn": room["turn"],
                        "winner": winner,
                        "line": line,
                        "wins": room["wins"],
                        "names": list(room["names"].values())
                    }

                    for client in room["players"] + room["spectators"]:
                        await client.send_json(payload)

            if data["type"] == "reset":
                room["board"] = [None]*9
                room["turn"] = 0
                for client in room["players"] + room["spectators"]:
                    await client.send_json({
                        "board": room["board"],
                        "turn": room["turn"],
                        "winner": None,
                        "line": None,
                        "wins": room["wins"],
                        "names": list(room["names"].values())
                    })

    except WebSocketDisconnect:
        if ws in room["players"]:
            room["players"].remove(ws)
        if ws in room["spectators"]:
            room["spectators"].remove(ws)
