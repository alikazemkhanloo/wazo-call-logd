# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from functools import wraps
from contextlib import contextmanager
from hamcrest import assert_that
from hamcrest import contains_inanyorder
from hamcrest import empty
from hamcrest import has_entries
from hamcrest import has_key
from hamcrest import has_properties
from hamcrest import is_
from hamcrest import not_
from hamcrest import none
from xivo_test_helpers import until

from .helpers.base import IntegrationTest
from .helpers.confd import MockUser, MockLine


# this decorator takes the output of a psql and changes it into a list of dict
def raw_cels(cel_output):
    cels = []
    lines = cel_output.strip().split('\n')
    columns = [field.strip() for field in lines[0].split('|')]
    for line in lines[2:]:
        cel = [field.strip() for field in line.split('|')]
        cels.append(dict(zip(columns, cel)))

    def _decorate(func):
        @wraps(func)
        def wrapped_function(self, *args, **kwargs):
            with self.cels(cels):
                return func(self, *args, **kwargs)
        return wrapped_function
    return _decorate


class TestCallLogGeneration(IntegrationTest):

    asset = 'base'

    def setUp(self):
        self.bus = self.make_bus()
        self.confd = self.make_confd()
        self.confd.reset()
        until.true(self.bus.is_up, tries=10, interval=0.5)

    @raw_cels('''\
  eventtype   |         eventtime          |       channame        |   uniqueid    |   linkedid    | cid_name | cid_num
--------------+----------------------------+-----------------------+---------------+---------------+----------+---------
 CHAN_START   | 2017-11-10 10:07:08.620283 | SIP/dev_37_0-0000001a | 1510326428.26 | 1510326428.26 |          | 042302
 XIVO_INCALL  | 2017-11-10 10:07:08.877093 | SIP/dev_37_0-0000001a | 1510326428.26 | 1510326428.26 |          | 42302
 APP_START    | 2017-11-10 10:07:09.15148  | SIP/dev_37_0-0000001a | 1510326428.26 | 1510326428.26 |          | 42302
 CHAN_START   | 2017-11-10 10:07:09.156027 | SIP/9x1hhbkf-0000001b | 1510326429.27 | 1510326428.26 | Alicé    | 1645
 ANSWER       | 2017-11-10 10:07:11.986921 | SIP/9x1hhbkf-0000001b | 1510326429.27 | 1510326428.26 | Alicé    | 1645
 ANSWER       | 2017-11-10 10:07:11.993852 | SIP/dev_37_0-0000001a | 1510326428.26 | 1510326428.26 |          | 42302
 BRIDGE_ENTER | 2017-11-10 10:07:11.996672 | SIP/9x1hhbkf-0000001b | 1510326429.27 | 1510326428.26 | Alicé    | 1645
 BRIDGE_ENTER | 2017-11-10 10:07:12.007126 | SIP/dev_37_0-0000001a | 1510326428.26 | 1510326428.26 |          | 42302
 BRIDGE_EXIT  | 2017-11-10 10:07:13.69614  | SIP/9x1hhbkf-0000001b | 1510326429.27 | 1510326428.26 | Alicé    | 1645
 HANGUP       | 2017-11-10 10:07:13.756533 | SIP/9x1hhbkf-0000001b | 1510326429.27 | 1510326428.26 | Alicé    | 1645
 CHAN_END     | 2017-11-10 10:07:13.758228 | SIP/9x1hhbkf-0000001b | 1510326429.27 | 1510326428.26 | Alicé    | 1645
 BRIDGE_EXIT  | 2017-11-10 10:07:13.759858 | SIP/dev_37_0-0000001a | 1510326428.26 | 1510326428.26 |          | 42302
 HANGUP       | 2017-11-10 10:07:13.761307 | SIP/dev_37_0-0000001a | 1510326428.26 | 1510326428.26 |          | 42302
 CHAN_END     | 2017-11-10 10:07:13.762793 | SIP/dev_37_0-0000001a | 1510326428.26 | 1510326428.26 |          | 42302
 LINKEDID_END | 2017-11-10 10:07:13.764775 | SIP/dev_37_0-0000001a | 1510326428.26 | 1510326428.26 |          | 42302
''')
    def test_incoming_call_no_cid_name_rewritten_cid_num(self):
        linkedid = '1510326428.26'
        with self.no_call_logs():
            self.bus.send_linkedid_end(linkedid)

            def call_log_has_transformed_number():
                with self.database.queries() as queries:
                    call_log = queries.find_last_call_log()
                    assert_that(
                        call_log,
                        has_properties(
                            'source_name', '',
                            'source_exten', '42302'))

            until.assert_(call_log_has_transformed_number, tries=5)

    def test_given_cels_with_unknown_line_identities_when_generate_call_log_then_no_user_uuid(self):
        linkedid = '123456789.1011'
        cels = [
            {'eventtype': 'CHAN_START',
             'eventtime': '2015-06-18 14:08:56.910686',
             'channame': 'SIP/as2mkq-0000001f',
             'uniqueid': '1434650936.31',
             'linkedid': linkedid},
            {'eventtype': 'APP_START',
             'eventtime': '2015-06-18 14:08:57.014249',
             'channame': 'SIP/as2mkq-0000001f',
             'uniqueid': '1434650936.31',
             'linkedid': linkedid},
            {'eventtype': 'CHAN_START',
             'eventtime': '2015-06-18 14:08:57.019202',
             'channame': 'SIP/je5qtq-00000020',
             'uniqueid': '1434650937.32',
             'linkedid': linkedid},
            {'eventtype': 'ANSWER',
             'eventtime': '2015-06-18 14:08:59.864053',
             'channame': 'SIP/je5qtq-00000020',
             'uniqueid': '1434650937.32',
             'linkedid': linkedid},
            {'eventtype': 'ANSWER',
             'eventtime': '2015-06-18 14:08:59.877155',
             'channame': 'SIP/as2mkq-0000001f',
             'uniqueid': '1434650936.31',
             'linkedid': linkedid},
            {'eventtype': 'BRIDGE_ENTER',
             'eventtime': '2015-06-18 14:08:59.878',
             'channame': 'SIP/as2mkq-0000001f',
             'uniqueid': '1434650936.31',
             'linkedid': linkedid},
            {'eventtype': 'BRIDGE_ENTER',
             'eventtime': '2015-06-18 14:08:59.87976',
             'channame': 'SIP/je5qtq-00000020',
             'uniqueid': '1434650937.32',
             'linkedid': linkedid},
            {'eventtype': 'BRIDGE_EXIT',
             'eventtime': '2015-06-18 14:09:02.250446',
             'channame': 'SIP/je5qtq-00000020',
             'uniqueid': '1434650937.32',
             'linkedid': linkedid},
            {'eventtype': 'HANGUP',
             'eventtime': '2015-06-18 14:09:02.26592',
             'channame': 'SIP/je5qtq-00000020',
             'uniqueid': '1434650937.32',
             'linkedid': linkedid},
            {'eventtype': 'CHAN_END',
             'eventtime': '2015-06-18 14:09:02.267146',
             'channame': 'SIP/je5qtq-00000020',
             'uniqueid': '1434650937.32',
             'linkedid': linkedid},
            {'eventtype': 'BRIDGE_EXIT',
             'eventtime': '2015-06-18 14:09:02.268',
             'channame': 'SIP/as2mkq-0000001f',
             'uniqueid': '1434650936.31',
             'linkedid': linkedid},
            {'eventtype': 'HANGUP',
             'eventtime': '2015-06-18 14:09:02.269498',
             'channame': 'SIP/as2mkq-0000001f',
             'uniqueid': '1434650936.31',
             'linkedid': linkedid},
            {'eventtype': 'CHAN_END',
             'eventtime': '2015-06-18 14:09:02.271033',
             'channame': 'SIP/as2mkq-0000001f',
             'uniqueid': '1434650936.31',
             'linkedid': linkedid},
            {'eventtype': 'LINKEDID_END',
             'eventtime': '2015-06-18 14:09:02.272325',
             'channame': 'SIP/as2mkq-0000001f',
             'uniqueid': '1434650936.31',
             'linkedid': linkedid},
        ]
        msg_accumulator_1 = self.bus.accumulator('call_log.created')
        msg_accumulator_2 = self.bus.accumulator('call_log.user.*.created')
        with self.cels(cels), self.no_call_logs():
            self.bus.send_linkedid_end(linkedid)

            def call_log_has_no_user_uuid():
                with self.database.queries() as queries:
                    call_log = queries.find_last_call_log()
                    assert_that(call_log, is_(not_(none())))
                    user_uuids = queries.get_call_log_user_uuids(call_log.id)
                    assert_that(user_uuids, empty())

            def bus_event_call_log_created(accumulator):
                assert_that(accumulator.accumulate(), contains_inanyorder(has_entries(
                    name='call_log_created',
                    data=has_key('tags')
                )))

            def bus_event_call_log_user_created(accumulator):
                assert_that(accumulator.accumulate(), empty())

            until.assert_(call_log_has_no_user_uuid, tries=5)
            until.assert_(bus_event_call_log_created, msg_accumulator_1, tries=10, interval=0.25)
            until.assert_(bus_event_call_log_user_created, msg_accumulator_2, tries=10, interval=0.25)

    def test_given_cels_with_known_line_identities_when_generate_call_log_then_call_log_have_user_uuid(self):
        linkedid = '123456789.1011'
        cels = [
            {'eventtype': 'CHAN_START',
             'eventtime': '2015-06-18 14:08:56.910686',
             'channame': 'SIP/as2mkq-0000001f',
             'uniqueid': '1434650936.31',
             'linkedid': linkedid},
            {'eventtype': 'APP_START',
             'eventtime': '2015-06-18 14:08:57.014249',
             'channame': 'SIP/as2mkq-0000001f',
             'uniqueid': '1434650936.31',
             'linkedid': linkedid},
            {'eventtype': 'CHAN_START',
             'eventtime': '2015-06-18 14:08:57.019202',
             'channame': 'SIP/je5qtq-00000020',
             'uniqueid': '1434650937.32',
             'linkedid': linkedid},
            {'eventtype': 'ANSWER',
             'eventtime': '2015-06-18 14:08:59.864053',
             'channame': 'SIP/je5qtq-00000020',
             'uniqueid': '1434650937.32',
             'linkedid': linkedid},
            {'eventtype': 'ANSWER',
             'eventtime': '2015-06-18 14:08:59.877155',
             'channame': 'SIP/as2mkq-0000001f',
             'uniqueid': '1434650936.31',
             'linkedid': linkedid},
            {'eventtype': 'BRIDGE_ENTER',
             'eventtime': '2015-06-18 14:08:59.878',
             'channame': 'SIP/as2mkq-0000001f',
             'uniqueid': '1434650936.31',
             'linkedid': linkedid},
            {'eventtype': 'BRIDGE_ENTER',
             'eventtime': '2015-06-18 14:08:59.87976',
             'channame': 'SIP/je5qtq-00000020',
             'uniqueid': '1434650937.32',
             'linkedid': linkedid},
            {'eventtype': 'BRIDGE_EXIT',
             'eventtime': '2015-06-18 14:09:02.250446',
             'channame': 'SIP/je5qtq-00000020',
             'uniqueid': '1434650937.32',
             'linkedid': linkedid},
            {'eventtype': 'HANGUP',
             'eventtime': '2015-06-18 14:09:02.26592',
             'channame': 'SIP/je5qtq-00000020',
             'uniqueid': '1434650937.32',
             'linkedid': linkedid},
            {'eventtype': 'CHAN_END',
             'eventtime': '2015-06-18 14:09:02.267146',
             'channame': 'SIP/je5qtq-00000020',
             'uniqueid': '1434650937.32',
             'linkedid': linkedid},
            {'eventtype': 'BRIDGE_EXIT',
             'eventtime': '2015-06-18 14:09:02.268',
             'channame': 'SIP/as2mkq-0000001f',
             'uniqueid': '1434650936.31',
             'linkedid': linkedid},
            {'eventtype': 'HANGUP',
             'eventtime': '2015-06-18 14:09:02.269498',
             'channame': 'SIP/as2mkq-0000001f',
             'uniqueid': '1434650936.31',
             'linkedid': linkedid},
            {'eventtype': 'CHAN_END',
             'eventtime': '2015-06-18 14:09:02.271033',
             'channame': 'SIP/as2mkq-0000001f',
             'uniqueid': '1434650936.31',
             'linkedid': linkedid},
            {'eventtype': 'LINKEDID_END',
             'eventtime': '2015-06-18 14:09:02.272325',
             'channame': 'SIP/as2mkq-0000001f',
             'uniqueid': '1434650936.31',
             'linkedid': linkedid},
        ]
        self.confd.set_users(MockUser('user_1_uuid', line_ids=[1]), MockUser('user_2_uuid', line_ids=[2]))
        self.confd.set_lines(MockLine(id=1, name='as2mkq', users=[{'uuid': 'user_1_uuid'}]), MockLine(id=2, name='je5qtq', users=[{'uuid': 'user_2_uuid'}]))
        msg_accumulator_1 = self.bus.accumulator('call_log.created')
        msg_accumulator_2 = self.bus.accumulator('call_log.user.*.created')
        with self.cels(cels), self.no_call_logs():
            self.bus.send_linkedid_end(linkedid)

            def call_log_has_both_user_uuid():
                with self.database.queries() as queries:
                    call_log = queries.find_last_call_log()
                    assert_that(call_log, is_(not_(none())))
                    user_uuids = queries.get_call_log_user_uuids(call_log.id)
                    assert_that(user_uuids, contains_inanyorder('user_1_uuid', 'user_2_uuid'))

            def bus_event_call_log_created(accumulator):
                assert_that(accumulator.accumulate(), contains_inanyorder(has_entries(
                    name='call_log_created',
                    data=has_key('tags')
                )))

            def bus_event_call_log_user_created(accumulator):
                assert_that(accumulator.accumulate(), contains_inanyorder(
                    has_entries(
                        name='call_log_user_created',
                        required_acl='events.call_log.user.user_1_uuid.created',
                        data=not_(has_key('tags')),
                    ),
                    has_entries(
                        name='call_log_user_created',
                        required_acl='events.call_log.user.user_2_uuid.created',
                        data=not_(has_key('tags')),
                    )
                ))

            until.assert_(call_log_has_both_user_uuid, tries=5)
            until.assert_(bus_event_call_log_created, msg_accumulator_1, tries=10, interval=0.25)
            until.assert_(bus_event_call_log_user_created, msg_accumulator_2, tries=10, interval=0.25)

    @contextmanager
    def cels(self, cels):
        with self.database.queries() as queries:
            for cel in cels:
                cel['id'] = queries.insert_cel(**cel)

        yield

        with self.database.queries() as queries:
            for cel in cels:
                queries.delete_cel(cel['id'])

    @contextmanager
    def no_call_logs(self):
        with self.database.queries() as queries:
            queries.clear_call_logs()

        yield

        with self.database.queries() as queries:
            queries.clear_call_logs()
