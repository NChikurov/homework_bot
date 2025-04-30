import json
import logging
import os
import sys
import time
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telebot import TeleBot
from telebot.apihelper import ApiException

from exceptions import (
    APIResponseError,
    EndpointUnavailableError,
    JSONDecodeError,
    MissingAPIKeyError,
    MissingTokensError,
    UnexpectedHomeworkStatusError
)


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных окружения, необходимые для работы."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    missing_tokens = []

    for token_name, token_value in tokens.items():
        if not token_value:
            missing_tokens.append(token_name)

    if missing_tokens:
        error_message = (
            'Отсутствуют обязательные переменные окружения: '
            f'{", ".join(missing_tokens)}'
        )
        logging.critical(error_message)
        raise MissingTokensError(error_message)


def send_message(bot, message):
    """Отправляет сообщение в Telegram, определяемый переменной окружения."""
    try:
        logging.debug(f'Начинаем отправку сообщения: {message}')
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Сообщение отправлено: {message}')
        return True
    except (ApiException, requests.exceptions.RequestException) as error:
        error_message = f'Ошибка при отправке сообщения: {error}'
        logging.error(error_message)
        return False


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    payload = {'from_date': timestamp}

    try:
        logging.debug(f'Начинаем запрос к API: {ENDPOINT}, {payload}')
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        logging.debug('Ответ API получен')
    except requests.exceptions.RequestException as error:
        raise EndpointUnavailableError(f'Ошибка при запросе к API: {error}')

    if response.status_code != HTTPStatus.OK:
        raise EndpointUnavailableError(
            f'Эндпоинт недоступен. Код ответа: {response.status_code}'
        )

    try:
        return response.json()
    except json.JSONDecodeError as error:
        raise JSONDecodeError(f'Ошибка при обработке ответа API: {error}')


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError(
            'Ответ API не соответствует ожидаемой структуре. '
            f'Получен тип: {type(response)}'
        )

    if 'homeworks' not in response:
        raise MissingAPIKeyError(
            'Отсутствует ключ "homeworks" в ответе API'
        )

    homeworks = response.get('homeworks')

    if not isinstance(homeworks, list):
        raise TypeError(
            f'homeworks не является списком. Получен тип: {type(homeworks)}'
        )

    return homeworks


def parse_status(homework):
    """Извлекает из информации о домашней работе статус этой работы."""
    if not isinstance(homework, dict):
        raise APIResponseError('Данные о домашней работе не являются словарем')

    if 'homework_name' not in homework:
        raise MissingAPIKeyError(
            'Отсутствует ключ "homework_name" в информации о домашней работе'
        )

    if 'status' not in homework:
        raise MissingAPIKeyError(
            'Отсутствует ключ "status" в информации о домашней работе'
        )

    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    if homework_status not in HOMEWORK_VERDICTS:
        raise UnexpectedHomeworkStatusError(
            f'Неизвестный статус работы: {homework_status}'
        )

    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    last_error_message = None

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                homework = homeworks[0]
                message = parse_status(homework)
                if send_message(bot, message):
                    current_timestamp = response.get(
                        'current_date',
                        current_timestamp
                    )
                    last_error_message = None
            else:
                logging.debug('Нет новых статусов')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message != last_error_message:
                send_message(bot, message)
                last_error_message = message
            logging.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('homework.log', encoding='UTF-8')
        ]
    )

    main()
