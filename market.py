import datetime
import logging.config
from environs import Env
from seller import download_stock

import requests

from seller import divide, price_conversion

logger = logging.getLogger(__file__)


def get_product_list(page, campaign_id, access_token):
    """Получает страницу списка товаров продавца из Яндекс Маркета.

    Args:
        page (str): Токен страницы для постраничной загрузки товаров.
        campaign_id (str): Идентификатор магазина на Яндекс Маркете.
        access_token (str): Токен авторизации для доступа к API.

    Returns:
        dict: Данные о товарах и информация о следующей странице.

    Examples:
        Корректный вызов с действующими учётными данными:
        >>> products = get_product_list("", "12345", "valid_token")

        Некорректный вызов без обязательных аргументов:
        >>> get_product_list()
        Traceback (most recent call last):
            ...
        TypeError: get_product_list() missing 3 required positional arguments: 'page', 'campaign_id', and 'access_token'
    """

    endpoint_url = "https://api.partner.market.yandex.ru/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Host": "api.partner.market.yandex.ru",
    }
    payload = {
        "page_token": page,
        "limit": 200,
    }
    url = endpoint_url + f"campaigns/{campaign_id}/offer-mapping-entries"
    response = requests.get(url, headers=headers, params=payload)
    response.raise_for_status()
    response_object = response.json()
    return response_object.get("result")


def update_stocks(stocks, campaign_id, access_token):
    """Обновляет остатки товаров на складе Яндекс Маркета.

    Args:
        stocks (list[dict]): Список товаров с артикулами,
            идентификаторами складов и количеством.
        campaign_id (str): Идентификатор магазина на Яндекс Маркете.
        access_token (str): Токен авторизации для доступа к API.

    Returns:
        dict: Ответ сервера с результатом обработки запроса.

    Examples:
        Корректный вызов с действующими учётными данными:
        >>> stocks = [{
        ...     "sku": "12345",
        ...     "warehouseId": 100,
        ...     "items": [{"count": 10, "type": "FIT"}]
        ... }]
        >>> result = update_stocks(stocks, "12345", "valid_token")

        Некорректный вызов без обязательных аргументов:
        >>> update_stocks()
        Traceback (most recent call last):
            ...
        TypeError: update_stocks() missing 3 required positional arguments: 'stocks', 'campaign_id', and 'access_token'
    """

    endpoint_url = "https://api.partner.market.yandex.ru/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Host": "api.partner.market.yandex.ru",
    }
    payload = {"skus": stocks}
    url = endpoint_url + f"campaigns/{campaign_id}/offers/stocks"
    response = requests.put(url, headers=headers, json=payload)
    response.raise_for_status()
    response_object = response.json()
    return response_object


def update_price(prices, campaign_id, access_token):
    """Отправляет обновлённые цены товаров в Яндекс Маркет.

    Args:
        prices (list[dict]): Список товаров с артикулами,
            ценами и валютой.
        campaign_id (str): Идентификатор магазина на Яндекс Маркете.
        access_token (str): Токен авторизации для доступа к API.

    Returns:
        dict: Ответ сервера с результатом обработки запроса.

    Examples:
        Корректный вызов с действующими учётными данными:
        >>> prices = [{
        ...     "id": "12345",
        ...     "price": {
        ...         "value": 5990,
        ...         "currencyId": "RUR"
        ...     }
        ... }]
        >>> result = update_price(prices, "12345", "valid_token")

        Некорректный вызов без обязательных аргументов:
        >>> update_price()
        Traceback (most recent call last):
            ...
        TypeError: update_price() missing 3 required positional arguments: 'prices', 'campaign_id', and 'access_token'
    """
    endpoint_url = "https://api.partner.market.yandex.ru/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Host": "api.partner.market.yandex.ru",
    }
    payload = {"offers": prices}
    url = endpoint_url + f"campaigns/{campaign_id}/offer-prices/updates"
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    response_object = response.json()
    return response_object


def get_offer_ids(campaign_id, market_token):
    """Получает артикулы всех товаров продавца на Яндекс Маркете.

    Args:
        campaign_id (str): Идентификатор магазина на Яндекс Маркете.
        market_token (str): Токен авторизации для доступа к API.

    Returns:
        list[str]: Список артикулов товаров продавца.

    Examples:
        Корректный вызов с действующими учётными данными:
        >>> offer_ids = get_offer_ids("12345", "valid_token")
        >>> isinstance(offer_ids, list)
        True

        Некорректный вызов без обязательных аргументов:
        >>> get_offer_ids()
        Traceback (most recent call last):
            ...
        TypeError: get_offer_ids() missing 2 required positional arguments: 'campaign_id' and 'market_token'
    """
    page = ""
    product_list = []
    while True:
        some_prod = get_product_list(page, campaign_id, market_token)
        product_list.extend(some_prod.get("offerMappingEntries"))
        page = some_prod.get("paging").get("nextPageToken")
        if not page:
            break
    offer_ids = []
    for product in product_list:
        offer_ids.append(product.get("offer").get("shopSku"))
    return offer_ids


def create_stocks(watch_remnants, offer_ids, warehouse_id):
    """Формирует список остатков товаров для Яндекс Маркета.

    Args:
        watch_remnants (list[dict]): Данные о часах из Excel-файла.
        offer_ids (list[str]): Список артикулов товаров магазина.
        warehouse_id (str): Идентификатор склада на Яндекс Маркете.

    Returns:
        list[dict]: Список товаров с артикулами, идентификаторами
            складов, количеством и временем обновления остатков.

    Examples:
        Корректный вызов:
        >>> watches = [{"Код": "123", "Количество": 5}]
        >>> stocks = create_stocks(watches, ["123"], "100")
        >>> stocks[0]["items"][0]["count"]
        5

        Некорректный вызов:
        >>> create_stocks(None, ["123"], "100")
        Traceback (most recent call last):
            ...
        TypeError: 'NoneType' object is not iterable
    """
    # Уберем то, что не загружено в market
    stocks = list()
    date = str(datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z")
    for watch in watch_remnants:
        if str(watch.get("Код")) in offer_ids:
            count = str(watch.get("Количество"))
            if count == ">10":
                stock = 100
            elif count == "1":
                stock = 0
            else:
                stock = int(watch.get("Количество"))
            stocks.append(
                {
                    "sku": str(watch.get("Код")),
                    "warehouseId": warehouse_id,
                    "items": [
                        {
                            "count": stock,
                            "type": "FIT",
                            "updatedAt": date,
                        }
                    ],
                }
            )
            offer_ids.remove(str(watch.get("Код")))
    # Добавим недостающее из загруженного:
    for offer_id in offer_ids:
        stocks.append(
            {
                "sku": offer_id,
                "warehouseId": warehouse_id,
                "items": [
                    {
                        "count": 0,
                        "type": "FIT",
                        "updatedAt": date,
                    }
                ],
            }
        )
    return stocks


def create_prices(watch_remnants, offer_ids):
    """Формирует список цен товаров для Яндекс Маркета.

    Args:
        watch_remnants (list[dict]): Данные о часах из Excel-файла.
        offer_ids (list[str]): Список артикулов товаров магазина.

    Returns:
        list[dict]: Список товаров с артикулами, ценами и валютой.

    Examples:
        Корректный вызов:
        >>> watches = [{"Код": "123", "Цена": "5'990.00 руб."}]
        >>> create_prices(watches, ["123"])
        [{'id': '123', 'price': {'value': 5990, 'currencyId': 'RUR'}}]

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
                "id": str(watch.get("Код")),
                # "feed": {"id": 0},
                "price": {
                    "value": int(price_conversion(watch.get("Цена"))),
                    # "discountBase": 0,
                    "currencyId": "RUR",
                    # "vat": 0,
                },
                # "marketSku": 0,
                # "shopSku": "string",
            }
            prices.append(price)
    return prices


async def upload_prices(watch_remnants, campaign_id, market_token):
    """Подготавливает и отправляет обновлённые цены в Яндекс Маркет.

    Args:
        watch_remnants (list[dict]): Данные о часах из Excel-файла.
        campaign_id (str): Идентификатор магазина на Яндекс Маркете.
        market_token (str): Токен авторизации для доступа к API.

    Returns:
        list[dict]: Список товаров с подготовленными ценами.

    Examples:
        Корректный вызов с действующими учётными данными:
        >>> import asyncio
        >>> watches = [{"Код": "123", "Цена": "5'990.00 руб."}]
        >>> prices = asyncio.run(
        ...     upload_prices(watches, "12345", "valid_token")
        ... )

        Некорректный вызов без обязательных аргументов:
        >>> asyncio.run(upload_prices())
        Traceback (most recent call last):
            ...
        TypeError: upload_prices() missing 3 required positional arguments: 'watch_remnants', 'campaign_id', and 'market_token'
    """
    offer_ids = get_offer_ids(campaign_id, market_token)
    prices = create_prices(watch_remnants, offer_ids)
    for some_prices in list(divide(prices, 500)):
        update_price(some_prices, campaign_id, market_token)
    return prices


async def upload_stocks(watch_remnants, campaign_id, market_token, warehouse_id):
    """Подготавливает и отправляет актуальные остатки в Яндекс Маркет.

    Args:
        watch_remnants (list[dict]): Данные о часах из Excel-файла.
        campaign_id (str): Идентификатор магазина на Яндекс Маркете.
        market_token (str): Токен авторизации для доступа к API.
        warehouse_id (str): Идентификатор склада на Яндекс Маркете.

    Returns:
        tuple[list[dict], list[dict]]: Два списка остатков.
            Первый содержит товары с ненулевыми остатками.
            Второй содержит все товары, включая отсутствующие.

    Examples:
        Корректный вызов с действующими учётными данными:
        >>> import asyncio
        >>> watches = [{"Код": "123", "Количество": 5}]
        >>> result = asyncio.run(
        ...     upload_stocks(watches, "12345", "valid_token", "100")
        ... )

        Некорректный вызов без обязательных аргументов:
        >>> asyncio.run(upload_stocks())
        Traceback (most recent call last):
            ...
        TypeError: upload_stocks() missing 4 required positional arguments: 'watch_remnants', 'campaign_id', 'market_token', and 'warehouse_id'
    """
    offer_ids = get_offer_ids(campaign_id, market_token)
    stocks = create_stocks(watch_remnants, offer_ids, warehouse_id)
    for some_stock in list(divide(stocks, 2000)):
        update_stocks(some_stock, campaign_id, market_token)
    not_empty = list(
        filter(lambda stock: (stock.get("items")[0].get("count") != 0), stocks)
    )
    return not_empty, stocks


def main():
    """Обновляет цены и остатки часов на Яндекс Маркете для FBS и DBS.

    Загружает данные поставщика, обновляет остатки и цены
    товаров для обеих схем работы и обрабатывает ошибки соединения.

    Returns:
        None: Функция ничего не возвращает.

    Examples:
        Корректный вызов при наличии настроек и доступа к API:
        >>> main()

        Некорректный вызов при отсутствии переменных окружения:
        >>> main()
        Traceback (most recent call last):
            ...
        environs.EnvError: ...
    """
    env = Env()
    market_token = env.str("MARKET_TOKEN")
    campaign_fbs_id = env.str("FBS_ID")
    campaign_dbs_id = env.str("DBS_ID")
    warehouse_fbs_id = env.str("WAREHOUSE_FBS_ID")
    warehouse_dbs_id = env.str("WAREHOUSE_DBS_ID")

    watch_remnants = download_stock()
    try:
        # FBS
        offer_ids = get_offer_ids(campaign_fbs_id, market_token)
        # Обновить остатки FBS
        stocks = create_stocks(watch_remnants, offer_ids, warehouse_fbs_id)
        for some_stock in list(divide(stocks, 2000)):
            update_stocks(some_stock, campaign_fbs_id, market_token)
        # Поменять цены FBS
        upload_prices(watch_remnants, campaign_fbs_id, market_token)

        # DBS
        offer_ids = get_offer_ids(campaign_dbs_id, market_token)
        # Обновить остатки DBS
        stocks = create_stocks(watch_remnants, offer_ids, warehouse_dbs_id)
        for some_stock in list(divide(stocks, 2000)):
            update_stocks(some_stock, campaign_dbs_id, market_token)
        # Поменять цены DBS
        upload_prices(watch_remnants, campaign_dbs_id, market_token)
    except requests.exceptions.ReadTimeout:
        print("Превышено время ожидания...")
    except requests.exceptions.ConnectionError as error:
        print(error, "Ошибка соединения")
    except Exception as error:
        print(error, "ERROR_2")


if __name__ == "__main__":
    main()
