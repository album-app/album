import traceback
import threading
import os


class GlobalExceptionWatcher(object):
    def _store_excepthook(self, args):
        """
        Uses as an exception handlers which stores any uncaught exceptions.
        """
        self.__org_hook(args)
        formated_exc = traceback.format_exception(
            args.exc_type, args.exc_value, args.exc_traceback
        )
        self._exceptions.append("\n".join(formated_exc))
        return formated_exc

    def __enter__(self):
        """
        Register us to the hook.
        """
        self._exceptions = []
        self.__org_hook = threading.excepthook
        threading.excepthook = self._store_excepthook

    def __exit__(self, type, value, traceback):
        """
        Remove us from the hook, assure no exception were thrown.
        """
        threading.excepthook = self.__org_hook
        if len(self._exceptions) != 0:
            tracebacks = os.linesep.join(self._exceptions)
            raise Exception(f"Exceptions in other threads: {tracebacks}")
