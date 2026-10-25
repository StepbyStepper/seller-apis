import io
import logging.config
import os
import re
import zipfile
from environs import Env

import pandas as pd
import requests

logger = logging.getLogger(__file__)


def get_product_list(last_id, client_id, seller_token):
    """Получает страницу списка товаров магазина Ozon.

    Args:
        last_id (str): Идентификатор для получения следующей страницы товаров.
        client_id (str): Идентификатор продавца в Ozon.
        seller_token (str): API-ключ продавца.

    Returns:
        dict: Данные страницы товаров, полученные от Ozon.

    Examples:
        Корректный вызов:
        >>> products = get_product_list("", "12345", "valid_api_key")

        Некорректный вызов:
        >>> get_product_list("", "12345", "invalid_api_key")
        # Ozon отклонит запрос с недействительным API-ключом.
    """
    url = "https://api-seller.ozon.ru/v2/product/list"
    headers = {
        "Client-Id": client_id,
        "Api-Key": seller_token,
    }
    payload = {
        "filter": {
            "visibility": "ALL",
        },
        "last_id": last_id,
        "limit": 1000,
    }
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    response_object = response.json()
    return response_object.get("result")


def get_offer_ids(client_id, seller_token):
    """Получает список артикулов всех товаров продавца на Ozon.

    Args:
        client_id (str): Идентификатор продавца в Ozon.
        seller_token (str): API-ключ продавца.

    Returns:
        list[str]: Список артикулов товаров.

    Examples:
        Корректный результат вызова с действующими данными:
        >>> get_offer_ids("12345", "valid_api_key")
        ['10001', '10002', '10003']

        Некорректный вызов:
        >>> get_offer_ids()
        Traceback (most recent call last):
            ...
        TypeError: get_offer_ids() missing 2 required positional arguments: 'client_id' and 'seller_token'
    """
    last_id = ""
    product_list = []
    while True:
        some_prod = get_product_list(last_id, client_id, seller_token)
        product_list.extend(some_prod.get("items"))
        total = some_prod.get("total")
        last_id = some_prod.get("last_id")
        if total == len(product_list):
            break
    offer_ids = []
    for product in product_list:
        offer_ids.append(product.get("offer_id"))
    return offer_ids


def update_price(prices: list, client_id, seller_token):
    """Отправляет обновлённые цены товаров в Ozon.

    Args:
        prices (list): Список товаров с новыми ценами.
        client_id (str): Идентификатор продавца в Ozon.
        seller_token (str): API-ключ продавца.

    Returns:
        dict: Ответ Ozon с результатами обработки запроса.

    Examples:
        Корректный вызов с действующими учётными данными:
        >>> prices = [{
        ...     "offer_id": "12345",
        ...     "price": "5990",
        ...     "old_price": "0",
        ...     "currency_code": "RUB",
        ...     "auto_action_enabled": "UNKNOWN"
        ... }]
        >>> result = update_price(prices, "12345", "valid_api_key")

        Некорректный вызов:
        >>> update_price()
        Traceback (most recent call last):
            ...
        TypeError: update_price() missing 3 required positional arguments: 'prices', 'client_id', and 'seller_token'
    """
    url = "https://api-seller.ozon.ru/v1/product/import/prices"
    headers = {
        "Client-Id": client_id,
        "Api-Key": seller_token,
    }
    payload = {"prices": prices}
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()


def update_stocks(stocks: list, client_id, seller_token):
    """Обновляет остатки товаров на складе Ozon.

    Args:
        stocks (list[dict]): Список товаров с артикулами и остатками.
        client_id (str): Идентификатор продавца в Ozon.
        seller_token (str): API-ключ продавца.

    Returns:
        dict: Ответ Ozon с результатом обработки обновления остатков.

    Examples:
        Корректный вызов с действующими учётными данными:
        >>> stocks = [{"offer_id": "12345", "stock": 10}]
        >>> result = update_stocks(stocks, "12345", "valid_api_key")

        Некорректный вызов:
        >>> update_stocks()
        Traceback (most recent call last):
            ...
        TypeError: update_stocks() missing 3 required positional arguments: 'stocks', 'client_id', and 'seller_token'
    """
    url = "https://api-seller.ozon.ru/v1/product/import/stocks"
    headers = {
        "Client-Id": client_id,
        "Api-Key": seller_token,
    }
    payload = {"stocks": stocks}
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()


def download_stock():
    """Скачивает и обрабатывает файл с остатками часов с сайта Timeworld.

    Returns:
        list[dict]: Список товаров с артикулами, ценами и остатками.

    Examples:
        Корректный вызов при доступности файла:
        >>> stocks = download_stock()
        >>> isinstance(stocks, list)
        True

        Некорректное выполнение при недоступности сервера:
        >>> download_stock()
        Traceback (most recent call last):
            ...
        requests.exceptions.ConnectionError: ...
    """
    # Скачать остатки с сайта
    casio_url = "https://timeworld.ru/upload/files/ostatki.zip"
    session = requests.Session()
    response = session.get(casio_url)
    response.raise_for_status()
    with response, zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        archive.extractall(".")
    # Создаем список остатков часов:
    excel_file = "ostatki.xls"
    watch_remnants = pd.read_excel(
        io=excel_file,
        na_values=None,
        keep_default_na=False,
        header=17,
    ).to_dict(orient="records")
    os.remove("./ostatki.xls")  # Удалить файл
    return watch_remnants


def create_stocks(watch_remnants, offer_ids):
    """Формирует список остатков товаров для обновления на Ozon.

    Args:
        watch_remnants (list[dict]): Данные о часах из Excel-файла.
        offer_ids (list[str]): Список артикулов товаров на Ozon.

    Returns:
        list[dict]: Список артикулов и доступного количества товаров.

    Examples:
        Корректный вызов:
        >>> watches = [{"Код": "123", "Количество": 5}]
        >>> create_stocks(watches, ["123", "456"])
        [{'offer_id': '123', 'stock': 5},
         {'offer_id': '456', 'stock': 0}]

        Некорректный вызов:
        >>> create_stocks(None, ["123"])
        Traceback (most recent call last):
            ...
        TypeError: 'NoneType' object is not iterable
    """
    stocks = []
    for watch in watch_remnants:
        if str(watch.get("Код")) in offer_ids:
            count = str(watch.get("Количество"))
            if count == ">10":
                stock = 100
            elif count == "1":
                stock = 0
            else:
                stock = int(watch.get("Количество"))
            stocks.append({"offer_id": str(watch.get("Код")), "stock": stock})
            offer_ids.remove(str(watch.get("Код")))
    # Добавим недостающее из загруженного:
    for offer_id in offer_ids:
        stocks.append({"offer_id": offer_id, "stock": 0})
    return stocks


def create_prices(watch_remnants, offer_ids):
    """Формирует список цен товаров для обновления на Ozon.

    Args:
        watch_remnants (list[dict]): Данные о часах из Excel-файла.
        offer_ids (list[str]): Список артикулов товаров на Ozon.

    Returns:
        list[dict]: Список товаров с артикулами, ценами и валютой.

    Examples:
        Корректный вызов:
        >>> watches = [{"Код": "123", "Цена": "5'990.00 руб."}]
        >>> create_prices(watches, ["123"])
        [{'auto_action_enabled': 'UNKNOWN',
          'currency_code': 'RUB',
          'offer_id': '123',
          'old_price': '0',
          'price': '5990'}]

        Некорректный вызов:
        >>> create_prices(None, ["123"])
        Traceback (most recent call last):
            ...
        TypeError: 'NoneType' object is not iterable
    """
    prices = []
    for watch in watch_remnants:
        if str(watch.get("Код")) in offer_ids:
            price = {
                "auto_action_enabled": "UNKNOWN",
                "currency_code": "RUB",
                "offer_id": str(watch.get("Код")),
                "old_price": "0",
                "price": price_conversion(watch.get("Цена")),
            }
            prices.append(price)
    return prices


def price_conversion(price: str) -> str:
    """Преобразует цену товара в строку из цифр без дробной части.

    Args:
        price (str): Цена товара в строковом формате.

    Returns:
        str: Цена без дробной части и нечисловых символов.

    Examples:
        Корректный вызов:
        >>> price_conversion("5'990.00 руб.")
        '5990'

        Некорректный вызов:
        >>> price_conversion(5990)
        Traceback (most recent call last):
            ...
        AttributeError: 'int' object has no attribute 'split'
    """
    return re.sub("[^0-9]", "", price.split(".")[0])


def divide(lst: list, n: int):
    """Разбивает список на части заданного размера.

    Args:
        lst (list): Исходный список элементов.
        n (int): Максимальное количество элементов в одной части.

    Yields:
        list: Очередная часть исходного списка.

    Examples:
        Корректный вызов:
        >>> list(divide([1, 2, 3, 4, 5], 2))
        [[1, 2], [3, 4], [5]]

        Некорректный вызов:
        >>> list(divide([1, 2, 3], 0))
        Traceback (most recent call last):
            ...
        ValueError: range() arg 3 must not be zero
    """
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


async def upload_prices(watch_remnants, client_id, seller_token):
    """Подготавливает и отправляет обновлённые цены товаров в Ozon.

    Args:
        watch_remnants (list[dict]): Данные о часах из Excel-файла.
        client_id (str): Идентификатор продавца в Ozon.
        seller_token (str): API-ключ продавца.

    Returns:
        list[dict]: Список товаров с подготовленными ценами.

    Examples:
        Корректный вызов с действующими учётными данными:
        >>> import asyncio
        >>> watches = [{"Код": "123", "Цена": "5'990.00 руб."}]
        >>> prices = asyncio.run(
        ...     upload_prices(watches, "12345", "valid_api_key")
        ... )

        Некорректный вызов:
        >>> import asyncio
        >>> asyncio.run(upload_prices())
        Traceback (most recent call last):
            ...
        TypeError: upload_prices() missing 3 required positional arguments: 'watch_remnants', 'client_id', and 'seller_token'
    """
    offer_ids = get_offer_ids(client_id, seller_token)
    prices = create_prices(watch_remnants, offer_ids)
    for some_price in list(divide(prices, 1000)):
        update_price(some_price, client_id, seller_token)
    return prices


async def upload_stocks(watch_remnants, client_id, seller_token):
    """Подготавливает и отправляет актуальные остатки товаров в Ozon.

    Args:
        watch_remnants (list[dict]): Данные о часах из Excel-файла.
        client_id (str): Идентификатор продавца в Ozon.
        seller_token (str): API-ключ продавца.

    Returns:
        tuple[list[dict], list[dict]]: Два списка остатков.
            Первый содержит только товары с ненулевыми остатками.
            Второй содержит все товары, включая отсутствующие.

    Examples:
        Корректный вызов с действующими учётными данными:
        >>> import asyncio
        >>> watches = [{"Код": "123", "Количество": 5}]
        >>> result = asyncio.run(
        ...     upload_stocks(watches, "12345", "valid_api_key")
        ... )

        Некорректный вызов:
        >>> asyncio.run(upload_stocks())
        Traceback (most recent call last):
            ...
        TypeError: upload_stocks() missing 3 required positional arguments: 'watch_remnants', 'client_id', and 'seller_token'
    """
    offer_ids = get_offer_ids(client_id, seller_token)
    stocks = create_stocks(watch_remnants, offer_ids)
    for some_stock in list(divide(stocks, 100)):
        update_stocks(some_stock, client_id, seller_token)
    not_empty = list(filter(lambda stock: (stock.get("stock") != 0), stocks))
    return not_empty, stocks


def main():
    """Запускает обновление цен и остатков товаров на Ozon.

    Загружает актуальные данные о часах и передаёт их
    на маркетплейс. Обрабатывает ошибки соединения.

    Returns:
        None: Функция ничего не возвращает.

    Examples:
        Корректный вызов при наличии настроек и доступа к Ozon:
        >>> main()

        Некорректный вызов при отсутствии переменных окружения:
        >>> main()
        Traceback (most recent call last):
            ...
        environs.EnvError: ...
    """
    env = Env()
    seller_token = env.str("SELLER_TOKEN")
    client_id = env.str("CLIENT_ID")
    try:
        offer_ids = get_offer_ids(client_id, seller_token)
        watch_remnants = download_stock()
        # Обновить остатки
        stocks = create_stocks(watch_remnants, offer_ids)
        for some_stock in list(divide(stocks, 100)):
            update_stocks(some_stock, client_id, seller_token)
        # Поменять цены
        prices = create_prices(watch_remnants, offer_ids)
        for some_price in list(divide(prices, 900)):
            update_price(some_price, client_id, seller_token)
    except requests.exceptions.ReadTimeout:
        print("Превышено время ожидания...")
    except requests.exceptions.ConnectionError as error:
        print(error, "Ошибка соединения")
    except Exception as error:
        print(error, "ERROR_2")


if __name__ == "__main__":
    main()
