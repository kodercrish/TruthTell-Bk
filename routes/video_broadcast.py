from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict
from collections import defaultdict

router = APIRouter(
    prefix="/video",
    tags=["video broadcast"],
    responses={404: {"description": "Not found"}},
)

# Maps to store socket connections
room_to_sockets_map: Dict[str, List[WebSocket]] = defaultdict(list)

@router.get("/")
async def video_broadcast_info():
    """
    Get information about the video broadcasting service
    """
    return {
        "service": "TruthTell Video Broadcasting",
        "status": "online",
        "endpoints": {
            "websocket": "/video/ws/{room}"
        }
    }

@router.get("/rooms")
async def get_active_rooms():
    """
    Get a list of all active rooms and their connection counts
    """
    active_rooms = list(room_to_sockets_map.keys())
    room_stats = {room: len(connections) for room, connections in room_to_sockets_map.items()}
    return {
        "active_rooms": active_rooms,
        "room_stats": room_stats
    }

@router.websocket("/ws/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str):
    """
    WebSocket endpoint for video broadcasting in rooms
    """
    await websocket.accept()
    print(f"WebSocket Connected: {websocket.client}")

    room_to_sockets_map[room].append(websocket)

    try:
        while True:
            data = await websocket.receive_json()
            event = data.get("event")

            if event == "room:join":
                await websocket.send_json({"event": "room:join", "data": data})
                await broadcast_to_room(room, {"event": "user:joined", "data": {"id": id(websocket)}})

            elif event == "message:broadcast":
                message = data.get("message")
                await broadcast_to_room(room, {"event": "message:broadcast", "data": {"from": id(websocket), "message": message}})

    except WebSocketDisconnect:
        print("WebSocket Disconnected")
        if websocket in room_to_sockets_map[room]:
            room_to_sockets_map[room].remove(websocket)
        # Clean up empty rooms
        if len(room_to_sockets_map[room]) == 0:
            del room_to_sockets_map[room]

async def broadcast_to_room(room: str, message: dict):
    """
    Broadcast a message to all clients in a specific room
    """
    for websocket in room_to_sockets_map[room]:
        await websocket.send_json(message)
