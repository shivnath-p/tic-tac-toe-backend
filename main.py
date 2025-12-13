from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()
rooms = {}

@app.get("/")
def home():
    return {"status": "Server running"}

def check_winner(board, n):
    lines = []

    for i in range(n):
        lines.append([(i*n+j) for j in range(n)])
        lines.append([(j*n+i) for j in range(n)])

    lines.append([i*n+i for i in range(n)])
    lines.append([(i+1)*n-(i+1) for i in range(n)])

    for line in lines:
        values = [board[i] for i in line]
        if values[0] and all(v == values[0] for v in values):
            return values[0], line

    if None not in board:
        return "Draw", []

    return None, []

@app.websocket("/ws/{room}/{size}")
async def ws(ws: WebSocket, room: str, size: int):
    await ws.accept()

    if room not in rooms:
        rooms[room] = {
            "board": [None]*(size*size),
            "turn": "P1",
            "players": [],
            "spectators": [],
            "wins": {"P1": 0, "P2": 0},
            "size": size
        }

    data = rooms[room]

    role = "spectator"
    if len(data["players"]) < 2:
        role = f"P{len(data['players'])+1}"
        data["players"].append(ws)
    else:
        data["spectators"].append(ws)

    try:
        while True:
            msg = await ws.receive_json()

            if msg["type"] == "move" and role == data["turn"]:
                idx = msg["index"]
                if data["board"][idx] is None:
                    data["board"][idx] = role
                    winner, line = check_winner(data["board"], size)
                    if winner in ["P1", "P2"]:
                        data["wins"][winner] += 1
                    data["turn"] = "P2" if data["turn"] == "P1" else "P1"

            if msg["type"] == "reset":
                data["board"] = [None]*(size*size)
                data["turn"] = "P1"

            payload = {
                "board": data["board"],
                "turn": data["turn"],
                "wins": data["wins"],
                "role": role,
                "winner": check_winner(data["board"], size)[0],
                "line": check_winner(data["board"], size)[1]
            }

            for c in data["players"] + data["spectators"]:
                await c.send_json(payload)

    except WebSocketDisconnect:
        pass
