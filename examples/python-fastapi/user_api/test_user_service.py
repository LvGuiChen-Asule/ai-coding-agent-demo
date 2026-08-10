"""业务层单元测试（标准库 unittest，离线可运行）。"""
import unittest

from .schemas import LoginRequest, RegisterRequest
from .user_service import login, register


class UserServiceTest(unittest.TestCase):
    def setUp(self):
        from . import models

        models.USERS.clear()

    def test_register_success(self):
        user = register(RegisterRequest("alice", "secret123", "alice@example.com"))
        self.assertEqual(user.username, "alice")
        self.assertNotEqual(user.password_hash, "secret123")

    def test_register_duplicate(self):
        register(RegisterRequest("bob", "secret123"))
        with self.assertRaises(ValueError):
            register(RegisterRequest("bob", "secret456"))

    def test_login_success(self):
        register(RegisterRequest("alice", "secret123"))
        resp = login(LoginRequest("alice", "secret123"))
        self.assertTrue(resp.token)

    def test_login_wrong_password(self):
        register(RegisterRequest("alice", "secret123"))
        with self.assertRaises(ValueError):
            login(LoginRequest("alice", "wrong-pass"))


if __name__ == "__main__":
    unittest.main()
