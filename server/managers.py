import json
import uuid
from typing import Dict, List

import aiofiles
from fastapi import WebSocket


class ConnectionManager:
    """Class which manages the users connections to the server"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        """Connects to the incoming client's connection request"""
        await websocket.accept()
        self.active_connections[user_id] = websocket

    async def disconnect(self, websocket: WebSocket) -> None:
        """Disconnects to the exisiting client's connection"""
        for user_id in self.active_connections:
            if self.active_connections[user_id] == websocket:
                del self.active_connections[user_id]


class MessageManager:
    """Class which manages sending message to the correct user"""

    def __init__(self):
        self.message: Dict

    async def recieve_message(self, msg: json) -> None:
        """Processes the recieved message, sends to user if online, else stores in the db"""
        self.message = json.load(msg)

    async def send_message(self, websocket: WebSocket) -> None:
        """Sends messge to the requested user"""
        await websocket.send_json(json.dumps(self.message))


class DbManager:
    """Manages the Database operations"""

    def __init__(self, user_db_file: str, messages_db_file: str):
        self.user_db_file = user_db_file
        self.rooms_db_file = messages_db_file
        print("entering")

    async def get_user(self, user_id: str) -> Dict:
        """Fetches the user data from Database"""
        async with aiofiles.open(self.user_db_file, mode="r") as f:
            data = await f.read()
        users = json.loads(data)
        return users.get(user_id, {"error": "user not found"})

    async def get_room(self, room_id: str) -> Dict:
        """Fetches the room data from Database"""
        async with aiofiles.open(self.rooms_db_file, mode="r") as f:
            data = await f.read()
        rooms = json.loads(data)
        return rooms.get(room_id, {"error": "user not found"})

    async def create_room(self, sender_id: str, reciever_id: str) -> None:
        """Creates a new room(only if the persons don't already have one)"""
        async with aiofiles.open(self.rooms_db_file, mode="r") as f:
            data = await f.read()
        rooms = json.loads(data)
        room_id = sender_id + reciever_id
        if ((sender_id + reciever_id) in rooms) or ((reciever_id + sender_id) in rooms):
            return {"error": "room already exists"}
        rooms[room_id] = {
            "room_id": room_id,
            "users": [sender_id, reciever_id],
            "messages": [],
        }
        async with aiofiles.open(self.rooms_db_file, mode="w") as f:
            await f.write(json.dumps(rooms))
        return {"success": {"room_id": room_id}}

    async def create_user(self, username: str, password: str) -> Dict:
        """Creates a new user"""
        async with aiofiles.open(self.user_db_file, mode="r") as f:
            data = await f.read()
        users = json.loads(data)
        for i in users:
            if username in users[i]["username"]:
                return {"error": "This username already exists"}
        user_id = str(uuid.uuid4())
        users[user_id] = {
            "user_id": user_id,
            "username": username,
            "password": password,
        }
        async with aiofiles.open(self.user_db_file, mode="w") as f:
            await f.write(json.dumps(users))
        return {"success": {"user_id": user_id}}

    async def get_latest_messages(self, room_id: str, n: int = 20) -> List:
        """Get latest "n" no of messages"""
        async with aiofiles.open(self.rooms_db_file, mode="r") as f:
            data = await f.read()
        rooms = json.loads(data)
        req_room = rooms[room_id]
        messages = req_room["messages"]
        return messages[-n:]

    async def create_message(
        self, sender_id: str, message: str, timestamp: int, room_id: str
    ) -> Dict:
        """Adds a message created by the user to Database"""
        async with aiofiles.open(self.rooms_db_file, mode="r") as f:
            data = await f.read()
        rooms = json.loads(data)
        req_room = rooms[room_id]
        message_id = str(uuid.uuid4())
        req_room["messages"].append(
            {
                "message_id": message_id,
                "sender": sender_id,
                "message": message,
                "timestamp": timestamp,
            }
        )
        async with aiofiles.open(self.rooms_db_file, mode="w") as f:
            await f.write(json.dumps(rooms))
        return {"success": {"message_id": message_id}}
