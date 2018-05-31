import sys, unittest, code
from flask import Flask


class FlaskTestCase(unittest.TestCase):
    app = None
    db = None
    TEST_DATABASE_URI = 'sqlite://'

    def __call__(self, result=None):
        """
        Wrapper around default __call__ method to perform common Flask test
        set up. This means that user-defined Test Cases aren't required to
        include a call to super().setUp().
        """
        testMethod = getattr(self, self._testMethodName)
        skipped = (
            getattr(self.__class__, "__unittest_skip__", False) or
            getattr(testMethod, "__unittest_skip__", False)
        )

        if not skipped:
            try:
                self._pre_setup()
            except Exception:
                result.addError(self, sys.exc_info())
                return
        super().__call__(result)
        if not skipped:
            try:
                self._post_teardown()
            except Exception:
                result.addError(self, sys.exc_info())
                return

    def _pre_setup(self):
        """
        Perform pre-test setup:
        * Create a test client.
        * Push app context.
        """
        if isinstance(self.app, Flask):
            self.app.config['SQLALCHEMY_DATABASE_URI'] = self.TEST_DATABASE_URI
            self.app.testing = True
            self.client = self.app.test_client()
            self.app_context = self.app.app_context()
            self.app_context.push()

            if self.db:
                self.db.create_all()

    def _post_teardown(self):
        """
        Perform post-test things.
        * Pop app context.
        """
        if hasattr(self, 'app_context'):
            if self.db: self.db.drop_all()
            self.app_context.pop()

