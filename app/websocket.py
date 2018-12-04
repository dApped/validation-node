import asyncio
import json
import logging
import threading

import janus
import websockets

import common
import scheduler
from database import database
from events import consensus

LOOP = asyncio.get_event_loop()
QUEUE = janus.Queue(loop=LOOP)

logger = logging.getLogger()


class Common:
    WEBSOCKETS = dict()  # key: ip:port, value: websocket connection

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
        try:
            websocket = await websockets.connect(address, timeout=2)
        except Exception as e:
            logger.error('Cannot connect to websocket: %s', address)
            logger.error(e)
            return
        cls.register(websocket)

    @classmethod
    async def get_or_create_websocket_connection(cls, websocket_address):
        if websocket_address not in cls.WEBSOCKETS:
            await cls.connect_to_websocket(websocket_address)
        return cls.WEBSOCKETS.get(websocket_address)

    @classmethod
    async def get_or_create_websocket_connections(cls, node_websocket_ips_ports):
        my_websocket_ip_port = common.node_websocket_ip_port()
        websockets_nodes = []
        for websocket_ip_port in node_websocket_ips_ports:
            if my_websocket_ip_port == websocket_ip_port:
                continue
            websocket = await cls.get_or_create_websocket_connection(websocket_ip_port)
            if not websocket:
                continue
            websockets_nodes.append(websocket)
        return websockets_nodes

    @staticmethod
    def is_message_valid(message_json):
        if message_json is None:
            return False
        for field in ['event_id', 'current_timestamp', 'json_data', 'node_id']:
            if field not in message_json or message_json[field] is None:
                return False
        return True

    @staticmethod
    def parse_fields_from_message(message_json):
        return (message_json['event_id'], message_json['node_id'],
                message_json['current_timestamp'], message_json['json_data'])


class Producer(Common):
    ''' Propagate votes to other nodes'''

    @classmethod
    async def producer(cls, message):
        event_id, _, _, _ = cls.parse_fields_from_message(message)
        # event exists because vote was accepted with vote API
        event_metadata = database.VerityEvent.get(event_id).metadata()
        node_websocket_ips = event_metadata.node_websocket_ips
        if not node_websocket_ips:
            logger.warning('Node Websocket IPs are not set')
            return
        websockets_nodes = await cls.get_or_create_websocket_connections(node_websocket_ips)
        if not websockets_nodes:
            logger.warning('Websockets are not connected')
            return
        message_json = json.dumps(message)
        await asyncio.wait([websocket.send(message_json) for websocket in websockets_nodes])

    @classmethod
    async def producer_handler(cls, async_q):
        while True:
            message_json = await async_q.get()
            if not cls.is_message_valid(message_json):
                logger.info('Invalid message_json: %s', message_json)
                continue
            await cls.producer(message_json)


class Consumer(Common):
    ''' Consume votes from other nodes'''

    @classmethod
    async def consumer(cls, message_json):
        _, node_id, current_timestamp, json_data = cls.parse_fields_from_message(message_json)

        if not common.is_vote_payload_valid(json_data):
            logger.info('Invalid vote payload: %s', json_data)
            return

        event_id, user_id, data, signature = common.parse_fields_from_json_data(json_data)
        event = database.VerityEvent.get(event_id)
        if not event:
            logger.info('[%s] Event not found', event_id)
            return

        event_metadata = event.metadata()
        # Do not check if consensus was already reached because nodes needs to have a common state

        is_vote_valid, message = common.is_vote_valid(current_timestamp, user_id, event)
        if not is_vote_valid:
            logger.info(message)
            return

        if not common.is_vote_signed(json_data):
            logger.info('[%s] Vote not signed correctly: %s', event_id, json_data)
            return

        vote = database.Vote(user_id, event_id, node_id, current_timestamp, data['answers'],
                             signature)
        vote.create()
        logger.info('[%s] Accepted vote from %s user from %s node: %s', vote.event_id, vote.user_id,
                    vote.node_id, vote.answers)
        if consensus.should_calculate_consensus(event):
            scheduler.scheduler.add_job(consensus.check_consensus, args=[event, event_metadata])

    @classmethod
    async def consumer_handler(cls, websocket, _):
        logger.info('Websocket opened %s:%s', websocket.host, websocket.port)
        while True:
            try:
                message_json = await asyncio.wait_for(websocket.recv(), timeout=20)
                message_json = json.loads(message_json)
                if not cls.is_message_valid(message_json):
                    logger.info('Invalid message_json: %s', message_json)
                    continue
                await cls.consumer(message_json)
            except websockets.exceptions.ConnectionClosed:
                logger.error('Websocket connection closed %s:%s', websocket.host, websocket.port)
                return
            except asyncio.TimeoutError:
                # No data in 20 seconds
                try:
                    pong_waiter = await websocket.ping()
                    await asyncio.wait_for(pong_waiter, timeout=10)
                except asyncio.TimeoutError:
                    logger.error(
                        'No response to ping in 10 seconds. Websocket connection closed %s:%s',
                        websocket.host, websocket.port)
                    return
            except Exception as e:
                logger.error(e)


def loop_in_thread(event_loop):
    node_websocket_port = common.node_websocket_port()
    asyncio.set_event_loop(event_loop)
    event_loop.run_until_complete(
        websockets.serve(Consumer.consumer_handler, '0.0.0.0', node_websocket_port))
    event_loop.run_until_complete(Producer.producer_handler(QUEUE.async_q))
    event_loop.run_forever()


def init():
    logger.info('Websocket Init started')
    t = threading.Thread(target=loop_in_thread, args=(LOOP, ))
    t.start()
    logger.info('Websocket Init done')
