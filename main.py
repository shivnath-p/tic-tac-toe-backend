from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict
import asyncio

app = FastAPI()

rooms: Dict[str, dict] = {}

@app.get("/")
def home():
    return {"status": "Tic Tac Toe WebSocket server is running"}

def check_winner(board, n):
    lines = []
    win_indices = []

    # Rows & columns
    for i in range(n):
        row = [i*n + j for j in range(n)]
        col = [j*n + i for j in range(n)]
        lines.append(row)
        lines.append(col)

    # Diagonals
    lines.append([i*n + i for i in range(n)])
    lines.append([(i+1)*n - (i+1) for i in range(n)])

    for line in lines:
        values = [board[i] for i in line]
        if values[0] and all(v == values[0] for v in values):
            return values[0], line

    if None not in board:
        return "Draw", []

    return None, []

@app.websocket("/ws/{room}")
async def ws_game(ws: WebSocket, room: str):
    await ws.accept()

    if room not in rooms:
        rooms[room] = {
            "players": [],
            "spectators": [],
            "board": [],
            "turn": 0,
            "names": [],
            "wins": [0, 0],
            "grid": 3,
            "timer": 15,
            "winner": None,
            "win_line": []
        }

    game = rooms[room]

    if len(game["players"]) < 2:
        player_id = len(game["players"])
        game["players"].append(ws)
    else:
        game["spectators"].append(ws)
        player_id = -1

    try:
        while True:
            data = await ws.receive_json()

            if data["type"] == "join":
                if player_id != -1:
                    game["names"].append(data["name"])
                game["grid"] = data["grid"]
                game["timer"] = data["timer"]
                game["board"] = [None] * (game["grid"] ** 2)
                game["turn"] = 0
                game["winner"] = None
                game["win_line"] = []

            if data["type"] == "move" and player_id == game["turn"]:
                idx = data["index"]
                if game["board"][idx] is None and not game["winner"]:
                    game["board"][idx] = player_id
                    winner, line = check_winner(game["board"], game["grid"])
                    if winner is not None:
                        game["winner"] = winner
                        game["win_line"] = line
                        if winner != "Draw":
                            game["wins"][winner] += 1
                    game["turn"] = 1 - game["turn"]

            if data["type"] == "reset":
                game["board"] = [None] * (game["grid"] ** 2)
                game["turn"] = 0
                game["winner"] = None
                game["win_line"] = []

            payload = {
                "board": game["board"],
                "turn": game["turn"],
                "names": game["names"],
                "wins": game["wins"],
                "winner": game["winner"],
                "win_line": game["win_line"],
                "grid": game["grid"]
            }

            for p in game["players"] + game["spectators"]:
                await p.send_json(payload)

    except WebSocketDisconnect:
        if player_id != -1:
            game["players"].remove(ws)
