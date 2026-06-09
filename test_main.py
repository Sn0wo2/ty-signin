import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from telethon.errors import RPCError, SessionPasswordNeededError
import main

class TestMain(unittest.IsolatedAsyncioTestCase):

    def test_name_username(self):
        entity = MagicMock()
        entity.username = "testuser"
        self.assertEqual(main._name(entity), "@testuser")

    def test_name_title(self):
        entity = MagicMock()
        del entity.username
        entity.title = "Test Title"
        self.assertEqual(main._name(entity), "Test Title")

    def test_name_first_name(self):
        entity = MagicMock()
        del entity.username
        del entity.title
        entity.first_name = "First"
        self.assertEqual(main._name(entity), "First")

    def test_name_id(self):
        entity = MagicMock()
        del entity.username
        del entity.title
        del entity.first_name
        entity.id = 12345
        self.assertEqual(main._name(entity), "12345")

    def test_name_fallback(self):
        self.assertEqual(main._name("fallback_str"), "fallback_str")
        entity = MagicMock(spec=[])
        self.assertEqual(main._name(entity), str(entity))

    async def test_signin_success_with_reply(self):
        client = AsyncMock()
        client.add_event_handler = MagicMock()
        client.remove_event_handler = MagicMock()

        entity = MagicMock()
        entity.username = "testuser"
        message = "hello"

        sent_msg = MagicMock()
        sent_msg.id = 999
        client.send_message = AsyncMock(return_value=sent_msg)

        handler = None
        def add_handler(h, event_filter):
            nonlocal handler
            handler = h

        client.add_event_handler.side_effect = add_handler

        async def run_signin():
            await main._signin(client, entity, message)

        task = asyncio.create_task(run_signin())
        await asyncio.sleep(0.05)

        if handler:
            event = MagicMock()
            event.message.text = "reply text"
            await handler(event)

        await task
        client.send_message.assert_called_once_with(entity, message)
        client.remove_event_handler.assert_called_once()

    async def test_signin_timeout(self):
        client = AsyncMock()
        client.add_event_handler = MagicMock()
        client.remove_event_handler = MagicMock()

        entity = MagicMock()
        entity.username = "testuser"
        message = "hello"

        sent_msg = MagicMock()
        sent_msg.id = 999
        client.send_message = AsyncMock(return_value=sent_msg)

        with patch("main.REPLY_TIMEOUT", 0.01):
            await main._signin(client, entity, message)

        client.send_message.assert_called_once_with(entity, message)
        client.remove_event_handler.assert_called_once()

    async def test_signin_retry_success(self):
        client = AsyncMock()
        client.add_event_handler = MagicMock()
        client.remove_event_handler = MagicMock()

        entity = MagicMock()
        entity.username = "testuser"
        message = "hello"

        sent_msg = MagicMock()
        sent_msg.id = 999
        client.send_message = AsyncMock(side_effect=[RPCError(None, "error"), sent_msg])

        with patch("main.REPLY_TIMEOUT", 0.01), patch("asyncio.sleep", AsyncMock()) as mock_sleep:
            await main._signin(client, entity, message)

        self.assertEqual(client.send_message.call_count, 2)
        mock_sleep.assert_called_once_with(1)

    async def test_login_authorized(self):
        client = AsyncMock()
        client.is_user_authorized = AsyncMock(return_value=True)

        await main._login(client)
        client.is_user_authorized.assert_called_once()
        client.qr_login.assert_not_called()

    async def test_login_qr_success(self):
        client = AsyncMock()
        client.is_user_authorized = AsyncMock(return_value=False)
        qr = AsyncMock()
        qr.url = "http://qr"
        qr.expires = MagicMock()
        client.qr_login = AsyncMock(return_value=qr)

        await main._login(client)
        client.is_user_authorized.assert_called_once()
        client.qr_login.assert_called_once()
        qr.wait.assert_called_once()

    async def test_login_qr_2fa(self):
        client = AsyncMock()
        client.is_user_authorized = AsyncMock(return_value=False)
        qr = AsyncMock()
        qr.url = "http://qr"
        qr.expires = MagicMock()
        qr.wait = AsyncMock(side_effect=SessionPasswordNeededError(None))
        client.qr_login = AsyncMock(return_value=qr)
        client.sign_in = AsyncMock()

        with patch("builtins.input", return_value="mypassword"):
            await main._login(client)

        client.is_user_authorized.assert_called_once()
        client.qr_login.assert_called_once()
        qr.wait.assert_called_once()
        client.sign_in.assert_called_once_with(password="mypassword")

    @patch("main.API_ID", 12345)
    @patch("main.API_HASH", "hash")
    @patch("main.TelegramClient")
    @patch("main._login", AsyncMock())
    @patch("main._signin", AsyncMock())
    async def test_main_login_only(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client

        args = MagicMock()
        args.login_only = True
        args.session_path = None
        args.target = None
        args.message = None

        tasks = [
            {"session": "sess1", "session_path": "path1"},
            {"session": "sess1", "session_path": "path1"}, # duplicate session
            {"session": "sess2", "session_path": "path2"},
        ]

        with patch("main.parse_args", return_value=args), patch("main.TASKS", tasks):
            await main.main()

        self.assertEqual(mock_client_cls.call_count, 2)
        mock_client_cls.assert_any_call("path1", 12345, "hash")
        mock_client_cls.assert_any_call("path2", 12345, "hash")

    @patch("main.API_ID", 12345)
    @patch("main.API_HASH", "hash")
    @patch("main.TelegramClient")
    @patch("main._login", AsyncMock())
    @patch("main._signin", AsyncMock())
    async def test_main_single_task(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client
        mock_client.get_entity = AsyncMock(return_value="resolved_entity")

        args = MagicMock()
        args.login_only = False
        args.session_path = "path1"
        args.target = "target1"
        args.message = "msg1"

        with patch("main.parse_args", return_value=args):
            await main.main()

        mock_client_cls.assert_called_once_with("path1", 12345, "hash")
        mock_client.connect.assert_called_once()
        mock_client.get_entity.assert_called_once_with("target1")
        main._signin.assert_called_once_with(mock_client, "resolved_entity", "msg1")
        mock_client.disconnect.assert_called_once()

    @patch("main.API_ID", 12345)
    @patch("main.API_HASH", "hash")
    @patch("main.TelegramClient")
    @patch("main._login", AsyncMock())
    @patch("main._signin", AsyncMock())
    async def test_main_batch_mode(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client
        mock_client.get_entity = AsyncMock(return_value="resolved_entity")

        args = MagicMock()
        args.login_only = False
        args.session_path = None
        args.target = None
        args.message = None

        tasks = [
            {"session": "sess1", "session_path": "path1", "parsed_target": "t1", "message": "m1"},
            {"session": "sess1", "session_path": "path1", "parsed_target": "t2", "message": "m2"},
        ]

        with patch("main.parse_args", return_value=args), patch("main.TASKS", tasks):
            await main.main()

        mock_client_cls.assert_called_once_with("path1", 12345, "hash")
        mock_client.connect.assert_called_once()
        self.assertEqual(mock_client.get_entity.call_count, 2)
        self.assertEqual(main._signin.call_count, 2)
        mock_client.disconnect.assert_called_once()

if __name__ == "__main__":
    unittest.main()
