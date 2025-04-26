import json
import logging
import os
import sys
import time

import requests
from dotenv import load_dotenv
from telebot import TeleBot

from exceptions import (
    APIResponseError,
    EndpointUnavailableError,
    MissingAPIKeyError,
    TelegramError,
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
    missing_tokens = []
    
    if not PRACTICUM_TOKEN:
        missing_tokens.append('PRACTICUM_TOKEN')
    if not TELEGRAM_TOKEN:
        missing_tokens.append('TELEGRAM_TOKEN')
    if not TELEGRAM_CHAT_ID:
        missing_tokens.append('TELEGRAM_CHAT_ID')
        
    if missing_tokens:
        logging.critical(
            'Отсутствуют обязательные переменные окружения: '
            f'{", ".join(missing_tokens)}'
        )
        return False
        
    return True


def send_message(bot, message):
    """Отправляет сообщение в Telegram-чат, определяемый переменной окружения."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Сообщение отправлено: {message}')
    except Exception as error:
        error_message = f'Ошибка при отправке сообщения: {error}'
        logging.error(error_message)
        raise TelegramError(error_message)


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса.
    В качестве параметра в функцию передаётся временная метка.
    В случае успешного запроса должна вернуть ответ API."""
    
    payload = {'from_date': timestamp}
    
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        
        if response.status_code != 200:
            raise EndpointUnavailableError(
                f'Эндпоинт недоступен. Код ответа: {response.status_code}'
            )
            
        return response.json()
        
    except requests.exceptions.RequestException as error:
        raise EndpointUnavailableError(f'Ошибка при запросе к API: {error}')
    except json.JSONDecodeError as error:
        raise Exception(f'Ошибка при обработке ответа API: {error}')


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError('Ответ API не соответствует ожидаемой структуре')
        
    if 'homeworks' not in response:
        raise MissingAPIKeyError(
            'Отсутствует ключ "homeworks" в ответе API'
        )
        
    homeworks = response.get('homeworks')
    
    if not isinstance(homeworks, list):
        raise TypeError('homeworks не является списком')
        
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

    if not check_tokens():
        logging.critical('Отсутствуют обязательные переменные окружения')
        sys.exit('Отсутствуют обязательные переменные окружения')

    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                homework = homeworks[0]
                message = parse_status(homework)
                send_message(bot, message)
            else:
                logging.debug('Отсутствие в ответе новых статусов')
                
            timestamp = response.get('current_date', timestamp)
                
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            try:
                send_message(bot, message)
            except Exception as send_error:
                logging.error(
                    f'Не удалось отправить сообщение об ошибке: {send_error}'
                )
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
    )

    main()

