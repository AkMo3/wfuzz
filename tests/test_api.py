import unittest
import sys
from io import BytesIO
import gzip
import pickle as pickle

import wfuzz
from wfuzz.facade import Facade
from wfuzz.fuzzobjects import FuzzResult
from wfuzz.fuzzrequest import FuzzRequest

try:
    # Python >= 3.3
    from unittest import mock
except ImportError:
    # Python < 3.3
    import mock

LOCAL_DOMAIN = "http://localhost"
URL_LOCAL = "%s:8000/dir" % (LOCAL_DOMAIN)
HTTPD_PORT = 8000

ECHO_URL = "%s:8000/echo" % (LOCAL_DOMAIN)


class APITests(unittest.TestCase):
    def test_get_payload(self):
        payload_list = wfuzz.get_payload(list(range(4))).data.get('dictio')[0]
        self.assertEqual(sorted(payload_list), sorted([0, 1, 2, 3]))

    def test_get_payloads(self):
        payload_list = wfuzz.get_payload([list(range(2)), list(range(2))]).data.get('dictio')[0]
        self.assertEqual(sorted(payload_list), sorted([[0, 1], [0, 1]]))

    def test_decode(self):
        payload_list = wfuzz.get_payload([list(range(2)), list(range(2))]).data.get('dictio')[0]
        self.assertEqual(sorted(payload_list), sorted([[0, 1], [0, 1]]))

    def test_get_session(self):
        data = wfuzz.get_session('-z range,0-4 http://127.0.0.1/FUZZ').data

        self.assertEqual(data.get('url'), 'http://127.0.0.1/FUZZ')
        self.assertEqual(data.get('payloads'), [('range', {'default': '0-4', 'encoder': None}, None)])

    def test_payload_description(self):
        class mock_saved_session(object):
            def __init__(self, fields, show_field):
                fr = FuzzRequest()
                fr.url = "http://www.wfuzz.org/path?param=1&param2=2"
                fuzz_res = FuzzResult(history=fr)
                fuzz_res._fields = fields
                fuzz_res._show_field = show_field

                self.outfile = BytesIO()

                with gzip.GzipFile(fileobj=self.outfile, mode="wb") as f:
                    pickle.dump(fuzz_res, f)

                self.outfile.seek(0)
                self.outfile.name = "mockfile"

            def close(self):
                pass

            def read(self, *args, **kwargs):
                return self.outfile.read(*args, **kwargs)

            def seek(self, *args, **kwargs):
                return self.outfile.seek(*args, **kwargs)

            def tell(self):
                return self.outfile.tell()

        # load plugins before mocking file object
        Facade().payloads

        m = mock.MagicMock(name='open', spec=open)
        m.return_value = mock_saved_session(["r.params.all"], True)

        mocked_fun = "builtins.open" if sys.version_info >= (3, 0) else "__builtin__.open"
        with mock.patch(mocked_fun, m):
            payload_list = list(wfuzz.payload(**{'show_field': True, 'fields': ['r'], 'payloads': [('wfuzzp', {'default': 'mockedfile', 'encoder': None}, None)]}))
            self.assertEqual([res[0].description for res in payload_list], ['param=1\nparam2=2'])

        m = mock.MagicMock(name='open', spec=open)
        m.return_value = mock_saved_session(["url"], None)

        mocked_fun = "builtins.open" if sys.version_info >= (3, 0) else "__builtin__.open"
        with mock.patch(mocked_fun, m):
            payload_list = list(wfuzz.payload(**{'show_field': True, 'fields': ['r'], 'payloads': [('wfuzzp', {'default': 'mockedfile', 'encoder': None}, None)]}))
            self.assertEqual([res[0].description for res in payload_list], ['http://www.wfuzz.org/path?param=1&param2=2'])

        m = mock.MagicMock(name='open', spec=open)
        m.return_value = mock_saved_session(["r.scheme"], False)

        mocked_fun = "builtins.open" if sys.version_info >= (3, 0) else "__builtin__.open"
        with mock.patch(mocked_fun, m):
            payload_list = list(wfuzz.payload(**{'show_field': True, 'fields': ['r'], 'payloads': [('wfuzzp', {'default': 'mockedfile', 'encoder': None}, None)]}))
            self.assertEqual([res[0].description for res in payload_list], ['http://www.wfuzz.org/path?param=1&param2=2 | http'])

    def test_payload(self):
        payload_list = list(wfuzz.payload(**{'payloads': [('range', {'default': '0-4', 'encoder': None}, None)]}))
        self.assertEqual(payload_list, [('0',), ('1',), ('2',), ('3',), ('4',)])

        payload_list = list(wfuzz.payload(**{'payloads': [('buffer_overflow', {'default': '10', 'encoder': None}, None)]}))
        self.assertEqual(payload_list, [('AAAAAAAAAA',)])

        with mock.patch('os.walk') as mocked_oswalk:
            mocked_oswalk.return_value = [
                ('foo', ('bar',), ('baz',)),
                ('foo/bar', (), ('spam', 'eggs')),
            ]
            payload_list = list(wfuzz.payload(**{'payloads': [('dirwalk', {'default': 'foo', 'encoder': None}, None)]}))
            self.assertEqual(payload_list, [('baz',), ('bar/spam',), ('bar/eggs',)])

        class mock_file(object):
            def __init__(self):
                self.my_iter = iter([b"one", b"two"])

            def __iter__(self):
                return self

            def __next__(self):
                return next(self.my_iter)

            def seek(self, pos):
                self.my_iter = iter([b"one", b"two"])

            next = __next__  # for Python 2

        m = mock.MagicMock(name='open', spec=open)
        m.return_value = mock_file()

        mocked_fun = "builtins.open" if sys.version_info >= (3, 0) else "__builtin__.open"
        with mock.patch(mocked_fun, m):
            payload_list = list(wfuzz.payload(**{'payloads': [('file', {'default': 'mockedfile', 'encoder': None}, None)]}))
            self.assertEqual(sorted(payload_list), sorted([('one',), ('two',)]))

        payload_list = list(wfuzz.payload(**{'payloads': [('hexrange', {'default': '09-10', 'encoder': None}, None)]}))
        self.assertEqual(payload_list, [('09',), ('0a',), ('0b',), ('0c',), ('0d',), ('0e',), ('0f',), ('10',)])

        payload_list = list(wfuzz.payload(**{'payloads': [('hexrange', {'default': '009-00B', 'encoder': None}, None)]}))
        self.assertEqual(payload_list, [('009',), ('00a',), ('00b',)])

        payload_list = list(wfuzz.payload(**{'payloads': [('ipnet', {'default': '192.168.0.1/30', 'encoder': None}, None)]}))
        self.assertEqual(payload_list, [('192.168.0.1',), ('192.168.0.2',)])

        payload_list = list(wfuzz.payload(**{'payloads': [('iprange', {'default': '192.168.0.1-192.168.0.2', 'encoder': None}, None)]}))
        self.assertEqual(payload_list, [('192.168.0.1',), ('192.168.0.2',)])

        payload_list = list(wfuzz.payload(**{'payloads': [('list', {'default': 'a-b', 'encoder': None}, None)]}))
        self.assertEqual(payload_list, [('a',), ('b',)])

        payload_list = list(wfuzz.payload(**{'payloads': [('list', {'default': 'a\\-b-b', 'encoder': None}, None)]}))
        self.assertEqual(payload_list, [('a-b',), ('b',)])

        payload_list = list(wfuzz.payload(**{'payloads': [('range', {'default': '1-2', 'encoder': None}, None)]}))
        self.assertEqual(payload_list, [('1',), ('2',)])
