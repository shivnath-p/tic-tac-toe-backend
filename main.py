from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()

rooms = {}


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

    for line in lines:
        if line[0] and all(cell == line[0] for cell in line):
            return line, line[0]

    if None not in board:
        return [], "Draw"

    return [], None


@app.websocket("/ws/{room_id}/{size}")
async def websocket_endpoint(ws: WebSocket, room_id: str, size: int):
    await ws.accept()

    if room_id not in rooms:
        rooms[room_id] = {
            "board": [None] * (size * size),
            "turn": "X",
            "players": [],
            "size": size
        }

    room = rooms[room_id]

    # ❌ STEP 4: BLOCK 3rd PLAYER
    if len(room["players"]) >= 2:
        await ws.send_json({"error": "Room is full"})
        await ws.close()
        return

    symbol = "X" if len(room["players"]) == 0 else "O"
    room["players"].append({"ws": ws, "symbol": symbol})

    await ws.send_json({
        "symbol": symbol,
        "board": room["board"],
        "turn": room["turn"],
        "winner": None,
        "winLine": []
    })

    try:
        while True:
            data = await ws.receive_json()
            idx = data.get("index")

            if room["turn"] != symbol:
                continue

            if room["board"][idx] is None:
                room["board"][idx] = symbol
                room["turn"] = "O" if symbol == "X" else "X"

            winLine, winner = check_winner(room["board"], room["size"])

            for p in room["players"]:
                await p["ws"].send_json({
                    "board": room["board"],
                    "turn": room["turn"],
                    "winner": winner,
                    "winLine": winLine
                })

    except WebSocketDisconnect:
        room["players"] = [p for p in room["players"] if p["ws"] != ws]
