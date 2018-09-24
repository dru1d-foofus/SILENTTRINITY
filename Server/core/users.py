import asyncio
import json


class User:
    def __init__(self, username, websocket):
        self.username = username
        self.websocket = websocket

    async def send(self, message):
        await self.websocket.send(message)
    
    async def disconnect(self):
        await self.websocket.close()

    def __str__(self):
        return f"User(username='{self.username}' websocket='{self.websocket}')"


class Users:
    def __init__(self):
        self.users = set()

    async def broadcast_message(self, message: str, status='info'):
        message = json.dumps({'type': 'event', 'name': 'message', 'data': {'status': status, 'text': message}})
        await asyncio.wait([user.send(message) for user in self.users])
    
    async def broadcast_event(self, name, data):
        message = json.dumps({
            'type': 'event', 
            'name': name,
            'data': data
        })

        await asyncio.wait([user.send(message) for user in self.users])

    def unregister(self, username: str):
        users = set(self.users)
        for user in users:
            if user.username == username:
                self.users.remove(user)

    async def register(self, username: str, websocket):
        self.users.add(User(username, websocket))
        await self.broadcast_message(f"User {username} has joined!")
    
    def __len__(self):
        return len(self.users)
