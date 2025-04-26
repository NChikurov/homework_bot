class HomeworkStatusException(Exception):
    """Базовое исключение для проекта."""
    pass


class EndpointUnavailableError(HomeworkStatusException):
    """Исключение при недоступности эндпоинта API."""
    pass


class APIResponseError(HomeworkStatusException):
    """Исключение при некорректном ответе API."""
    pass


class MissingAPIKeyError(HomeworkStatusException):
    """Исключение при отсутствии ключа в ответе API."""
    pass


class UnexpectedHomeworkStatusError(HomeworkStatusException):
    """Исключение при неожиданном статусе домашней работы."""
    pass


class TelegramError(HomeworkStatusException):
    """Исключение при ошибке в работе с Telegram API."""
    pass 