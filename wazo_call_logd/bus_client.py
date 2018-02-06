# Copyright 2015-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging

from kombu import Exchange, Connection, Queue
from kombu.mixins import ConsumerMixin

logger = logging.getLogger(__name__)


class _CELConsumer(ConsumerMixin):

    def __init__(self, queue):
        self._queue = queue

    def get_consumers(self, Consumer, channel):
        return [
            Consumer(self._queue, callbacks=[self.on_message]),
        ]

    def on_message(self, body, message):
        if body['data']['EventName'] == 'LINKEDID_END':
            linked_id = body['data']['LinkedID']
            logger.debug('Received LINKEDID_END: %s', linked_id)
            self._call_logs_manager.generate_from_linked_id(linked_id)

        message.ack()

    def run(self, connection, call_logs_manager):
        self.connection = connection
        self._call_logs_manager = call_logs_manager

        try:
            super(_CELConsumer, self).run()
        except Exception:
            logger.exception('An error occured while processing bus events')


class BusClient(object):

    _KEY = 'ami.CEL'

    def __init__(self, config):
        self.bus_url = 'amqp://{username}:{password}@{host}:{port}//'.format(**config['bus'])
        exchange = Exchange(config['bus']['exchange_name'],
                            type=config['bus']['exchange_type'])
        self.queue = Queue(exchange=exchange, routing_key=self._KEY, exclusive=True)
        self._consumer = _CELConsumer(self.queue)

    def run(self, call_logs_manager):
        with Connection(self.bus_url) as conn:
            self._consumer.run(conn, call_logs_manager)

    def stop(self):
        self._consumer.should_stop = True
