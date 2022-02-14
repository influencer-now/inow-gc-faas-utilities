from functools import wraps
from typing import Any, Callable

from ..misc.exception import CallbackRunError
from ..misc.singleton import Singleton


class BaseCallback(metaclass=Singleton):
    def add_callback(self, function: Callable):
        """Decorate function to add a callback at the end of its execution

        Args:
            function (Callable): decorated function

        Raises:
            CallbackRunError: throws error if callback is not run

        Returns:
            Any: function result
        """

        @wraps(function)
        def wrapper(*args, **kwargs):
            result = function(*args, **kwargs)
            if self.callback_function(result):
                return result
            else:
                raise CallbackRunError()

        return wrapper

    def callback_function(self, data: Any) -> bool:
        """run callback logic given an input data

        Args:
            data (Any): input for callback

        Raises:
            NotImplementedError: if it is not implemented

        Returns:
            bool: True if success
        """
        raise NotImplementedError("not implemented")
