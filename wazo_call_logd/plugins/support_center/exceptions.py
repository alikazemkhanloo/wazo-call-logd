# Copyright 2020-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo.rest_api_helpers import APIException


class AgentNotFoundException(APIException):
    def __init__(self, details=None):
        super().__init__(
            status_code=404,
            message='No agent found matching this ID',
            error_id='agent-not-found-with-given-id',
            details=details,
        )


class QueueNotFoundException(APIException):
    def __init__(self, details=None):
        super().__init__(
            status_code=404,
            message='No queue found matching this ID',
            error_id='queue-not-found-with-given-id',
            details=details,
        )


class RangeTooLargeException(APIException):
    def __init__(self, details=None):
        super().__init__(
            status_code=400,
            message='Date range is too large for the given interval',
            error_id='date-range-too-large-for-interval',
            details=details,
        )
