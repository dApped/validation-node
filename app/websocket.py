import asyncio
import json
import logging
import os
import threading

import janus
import websockets

from database import database

LOOP = asyncio.get_event_loop()
QUEUE = janus.Queue(loop=LOOP)

logger = logging.getLogger('flask.app')


class Common:
    WEBSOCKETS = dict()  # key: ip:port, value: websocket connections

    @staticmethod
    def key(host, port):
        return '%s:%s' % (host, port)

    @classmethod
    def register(cls, websocket):
        cls.WEBSOCKETS[cls.key(websocket.host, websocket.port)] = websocket

    @classmethod
    def unregister(cls, websocket):
        cls.WEBSOCKETS.pop(cls.key(websocket.host, websocket.port), None)

    @classmethod
    async def connect_to_websocket(cls, address):
        websocket = await websockets.connect('ws://' + address)
        cls.register(websocket)

    @classmethod
    async def get_or_create_websocket_connection(cls, websocket_address):
        if websocket_address not in cls.WEBSOCKETS:
            await cls.connect_to_websocket(websocket_address)
        return cls.WEBSOCKETS[websocket_address]

    @classmethod
    async def get_or_create_websocket_connections(cls, node_ips):
        websockets_nodes = []
        for node_ip in node_ips:
            if os.getenv('NODE_PORT') in node_ip:  # TODO improve this in production
                continue
            websocket_address = node_ip + '86'  # TODO remove this in production
            websocket = await cls.get_or_create_websocket_connection(websocket_address)
            websockets_nodes.append(websocket)
        return websockets_nodes


class Producer(Common):
    ''' Propagate votes to other nodes'''

    @staticmethod
    def create_message(vote):
        message_send = {}
        message_send['vote'] = vote.to_json()
        return json.dumps(message_send)

    @classmethod
    async def producer(cls, message):
        node_ips = message['node_ips']
        websockets_nodes = await cls.get_or_create_websocket_connections(node_ips)
        if websockets_nodes:
            message_json = cls.create_message(message['vote'])
            await asyncio.wait([websocket.send(message_json) for websocket in websockets_nodes])

    @classmethod
    async def producer_handler(cls, async_q):
        while True:
            message = await async_q.get()
            if 'node_ips' not in message or 'vote' not in message:
                logger.error('Message does not have required properties: %s', message)
                continue
            await cls.producer(message)
            # async_q.task_done() TODO if we need to block we also need to confirm the task


class Consumer(Common):
    ''' Consume votes from other nodes'''

    @staticmethod
    def is_message_valid(message):
        if 'vote' in message:
            return True
        return False

    @staticmethod
    def json_to_vote(vote_json):
        try:
            vote = database.Vote.from_json(vote_json)
        except Exception as e:
            logger.exception(e)
            return None
        return vote

    @staticmethod
    async def event_exists(event_id):
        event = database.VerityEvent.get(event_id)
        return event is not None

    @staticmethod
    async def create_vote(vote):
        vote.create()
        logger.info('Created vote from %s user for %s event from %s node', vote.user_id,
                    vote.event_id, vote.node_id)

    @classmethod
    async def consumer_handler(cls, websocket, _):
        cls.register(websocket)
        try:
            # asynchronous iteration
            async for message_json in websocket:
                message = json.loads(message_json)
                if not cls.is_message_valid(message):
                    logger.error("Message is not valid: %s", message)
                    continue
                vote = cls.json_to_vote(message['vote'])
                if vote is None:
                    logger.error("Vote %s is not valid", vote)
                    continue
                if not await cls.event_exists(vote.event_id):
                    logger.error("Event %s does not exist", vote.event_id)
                    continue
                await cls.create_vote(vote)
                # TODO check consensus
        finally:
            cls.unregister(websocket)


def loop_in_thread(event_loop):
    asyncio.set_event_loop(event_loop)
    event_loop.run_until_complete(websockets.serve(Consumer.consumer_handler, '0.0.0.0', 8765))
    event_loop.run_until_complete(Producer.producer_handler(QUEUE.async_q))
    event_loop.run_forever()


def init():
    logger.info('werzeug %s', os.environ.get("WERKZEUG_RUN_MAIN"))
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        # prevent flask running the the code twice
        return
    logger.info('Websocket Init started')
    t = threading.Thread(target=loop_in_thread, args=(LOOP, ))
    t.start()
    logger.info('Websocket Init done')
