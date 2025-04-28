class HomeworkStatusException(Exception):
    """Базовое исключение для проекта."""


class EndpointUnavailableError(HomeworkStatusException):
    """Исключение при недоступности эндпоинта API."""


class APIResponseError(HomeworkStatusException):
    """Исключение при некорректном ответе API."""


class MissingAPIKeyError(HomeworkStatusException):
    """Исключение при отсутствии ключа в ответе API."""


class UnexpectedHomeworkStatusError(HomeworkStatusException):
    """Исключение при неожиданном статусе домашней работы."""


class JSONDecodeError(HomeworkStatusException):
    """Исключение при ошибке декодирования JSON."""


class MissingTokensError(HomeworkStatusException):
    """Исключение при отсутствии обязательных переменных окружения."""
