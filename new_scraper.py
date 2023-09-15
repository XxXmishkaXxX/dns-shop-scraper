import asyncio
from datetime import datetime
import multiprocessing
import os
import queue
import threading
import time
import json
import pandas as pd
import aiohttp
from bs4 import BeautifulSoup as bs
from prettytable import PrettyTable
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium_stealth import stealth


def driver_setup():
    ''' Настройка драйвера для доступа к сайту DNS '''
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--window-size=200x100")
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)
    main_driver = webdriver.Chrome(options=options)

    stealth(driver=main_driver,
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/  537.36 (KHTML, like Gecko)'
                       'Chrome/83.0.4103.53 Safari/537.36',
            languages=["ru-RU", "ru"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
            run_on_insecure_origins=True,
            )

    main_driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        'source': '''
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
      '''
    })
    return main_driver


def parse_page(driver_chrome, url_for_page):
    ''' Парсинг страницы или json '''
    driver_chrome.get(url_for_page)
    driver_chrome.implicitly_wait(5)
    time.sleep(1)
    return_soup = bs(driver_chrome.page_source, 'lxml')

    return return_soup


def get_number_last_page(soup_for_parse):
    '''Получаем номер последней страницы '''
    last_page_div = soup_for_parse.find('div', class_='pagination-widget')

    last_page_li = last_page_div.find_all('li', class_='pagination-widget__page')
    last_page_li_last = last_page_li[-1]
    last_page = last_page_li_last['data-page-number']
    return last_page


def get_catalog(soup_for_parse):
    '''Список карточек продуктов на странице'''
    catalogs = soup_for_parse.find_all("div", class_="catalog-product ui-button-widget")
    return catalogs


def get_title(product_card):
    try:
        model = product_card.find("a", class_="catalog-product__name ui-link ui-link_black").span.text
        return model
    except Exception as ex:
        print(ex)
        return None


def get_price(product_card):
    try:
        price_element = product_card.find("div", class_="product-buy__price")
        if price_element is not None:
            price = price_element.text
            return price
    except Exception as e:
        print(f"Ошибка при получении цены: {e}")
    return None


def get_product_id(product_card):
    try:
        return product_card['data-product']
    except Exception as ex:
        print(ex)
        return None


def parse_detaile_product(driver, product_id):
    ''' Забираем характеристики товара'''

    url_json_detail = f'https://www.dns-shop.ru/catalog/product/get-product-characteristics-actual/?id={product_id}'

    driver.get(url_json_detail)
    driver.implicitly_wait(3)

    detail_soup = bs(driver.page_source, 'lxml').text
    detail_json = json.loads(detail_soup)
    detail_html = bs(detail_json['html'], 'lxml')
    detail_spec = detail_html.find_all('div',
                                       class_='product-characteristics__spec-title')
    detail_spec_value = detail_html.find_all('div',
                                             class_='product-characteristics__spec-value')

    returned_detail = {}

    for spec, spec_value in zip(detail_spec, detail_spec_value):
        returned_detail[spec.text.replace('\t', '').strip()] = spec_value.text.replace('\t', '').strip()

    return returned_detail


def parse_description_product(driver_for_parse, product_id_for_parse):
    ''' Забираем описание товара'''

    url_json_description = f'https://www.dns-shop.ru/product/microdata/{product_id_for_parse}'

    driver_for_parse.get(url_json_description)
    driver_for_parse.implicitly_wait(3)

    description_soup = bs(driver_for_parse.page_source, 'lxml').text
    description_json = json.loads(description_soup)

    return description_json['data']['description']


async def get_binary_data_image(link):
    '''Заходим по ссылке и получаем бинарные данные'''
    async with aiohttp.ClientSession() as session:
        async with session.get(link) as response:
            if response.status == 200:
                binary_data = await response.read()
                return binary_data
            else:
                print(f"Ошибка при обращении к {link}. Статус код: {response.status}")


async def do_tasks(links):
    '''Асинхронная функция для обработки списка ссылок и получения бинарных данных изображений.'''
    tasks = [get_binary_data_image(link) for link in links]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    image_binaries = [result for result in results if result is not None]
    return image_binaries


def parse_images(driver, product_id):
    '''Получаем ссылки на все изображения товара'''

    url_image = f'https://www.dns-shop.ru/catalog/product/get-media-content/?id={product_id}'
    driver.get(url_image)
    driver.implicitly_wait(3)
    image_soup = bs(driver.page_source, 'lxml')
    image_soup_json = image_soup.text.replace("</pre></body></html>", "").replace('''<html><head><meta content="light dark" name="color-scheme"/></head><body><pre
        style="word-wrap: break-word; white-space: pre-wrap;">''', "")
    image_json = json.loads(image_soup_json)
    image_json_get_list_object = image_json['data']['tabs'][0]['objects']
    links_images = []
    # Добавляем ссылки в список
    for obj in image_json_get_list_object:
        links_images.append((obj['origSrc']['orig']))
    # асинхронно получаем бинарные данные изображений
    binary_data_images = asyncio.run(do_tasks(
        links_images[:11]))  # тут можно выбрать сколько скачать изображений, но на первом месте название модели товара
    return binary_data_images


def get_info_from_parse_components(url, all_products_list, all_images_list):
    driver = driver_setup()

    soup = parse_page(driver, url)

    # Список с карточками товаров
    list_cards = get_catalog(soup)

    for card in list_cards:

        # получаем заголовок, цену, id товара
        title, price, id_card = get_title(card), get_price(card), get_product_id(card)
        model = title.split(' [')[0]

        time.sleep(1)
        try:

            details = parse_detaile_product(driver, id_card)
        except Exception as ex:
            print("Ошибка в получении характеристик", ex)
            details = None
        try:
            description = parse_description_product(driver, id_card)
        except Exception as ex:
            print("Ошибка в получении описания", ex)
            description = None
        try:
            images = parse_images(driver, id_card)
        except Exception as ex:
            print("Ошибка в получении изображений", ex)
            images = None

        info_component = {}
        images_component = {}

        info_component["Модель"] = model
        info_component["Заголовок"] = title
        info_component["Цена"] = price
        info_component["Описание"] = description
        info_component |= details

        images_component["Модель"] = model
        for index, img in enumerate(images):
            images_component[f"Изображение {index}"] = img

        all_images_list.put(images_component)
        all_products_list.put(info_component)

        time.sleep(1)

    driver.quit()


def save_data_to_excel(data, images, file_path_products, file_path_img_components):
    '''функция для сохранения информации в .xlsx формате'''
    df = pd.DataFrame(data)
    df.to_excel(file_path_products, index=False)

    df_2 = pd.DataFrame(images)
    df_2.to_excel(file_path_img_components, index=False)


def main(full_url):
    '''Основной цикл парсинга'''
    print(f"{full_url} scraping")

    # Списки где хранится вся информация о товарах категории
    all_products_list = queue.Queue()
    all_images_list = queue.Queue()

    driver = driver_setup()

    soup_main_info = parse_page(driver, f"{full_url}1")
    # Забираем количество страниц категории
    count_pages = int(get_number_last_page(soup_main_info))
    driver.quit()

    urls = [f"{full_url}{page}" for page in range(1, count_pages + 1)]

    threads = []

    # Создание потоков для каждой страницы категории
    for url in urls:
        thread = threading.Thread(target=get_info_from_parse_components, args=(url, all_products_list, all_images_list))
        threads.append(thread)
        thread.start()

    # Дожидаемся завершения всех потоков
    for thread in threads:
        thread.join()

    results_products = []
    results_images = []

    while not all_products_list.empty():
        result_prod = all_products_list.get()
        results_products.append(result_prod)

    while not all_images_list.empty():
        result_img = all_images_list.get()
        results_images.append(result_img)

    print(f"{full_url} scraping is done")

    category_name = f"{full_url.split('/')[-2]}"

    try:
        file_path_components = f"C:/Users/Михаил/Desktop/projects/dns-shop-parse/{category_name}/{category_name}.xlsx"
        file_path_images = f"C:/Users/Михаил/Desktop/projects/dns-shop-parse/{category_name}/images_{category_name}.xlsx"
        os.makedirs(os.path.dirname(file_path_components), exist_ok=True)

        print(f"save data: {file_path_components}")
        print(f"save data: {file_path_images}")

        save_data_to_excel(list(results_products), list(results_images), file_path_components, file_path_images)
        print(f"{category_name} data has saved")

    except Exception as ex:
        print(f"Произошла ошибка с категорией {full_url}", ex)


if __name__ == '__main__':
    '''Приветственное окно, где выбирают категории для парсинга'''
    table = PrettyTable()

    table.field_names = ['№', 'Категория', 'Ссылка']

    scheme = [[1, "Процессоры", "https://www.dns-shop.ru/catalog/17a899cd16404e77/processory/?p="],
              [2, "Видеокарты", "https://www.dns-shop.ru/catalog/17a89aab16404e77/videokarty/?p="],
              [3, "Материнские платы", "https://www.dns-shop.ru/catalog/17a89a0416404e77/materinskie-platy/?p="],
              [4, "Оперативная плата", "https://www.dns-shop.ru/catalog/17a89a3916404e77/operativnaya-pamyat-dimm/?p="],
              [5, "Жесткий Диск 3.5", "https://www.dns-shop.ru/catalog/17a8914916404e77/zhestkie-diski-35/?p="],
              [6, "Блоки питания", "https://www.dns-shop.ru/catalog/17a89c2216404e77/bloki-pitaniya/?p="],
              [7, "SSD накопители", "https://www.dns-shop.ru/catalog/8a9ddfba20724e77/ssd-nakopiteli/?p="],
              [8, "SSD M2 накопители", "https://www.dns-shop.ru/catalog/dd58148920724e77/ssd-m2-nakopiteli/?p="],
              [9, "Кулера для цп", "https://www.dns-shop.ru/catalog/17a9cc2d16404e77/kulery-dlya-processorov/?p="],
              [10, "Системы жид. охлождения",
               "https://www.dns-shop.ru/catalog/17a9cc9816404e77/sistemy-zhidkostnogo-oxlazhdeniya/?p="],
              [11, "Корпуса", "https://www.dns-shop.ru/catalog/17a89c5616404e77/korpusa/?p="]]

    table.add_rows(scheme)
    print(table)
    print("Выберите категорию(ии) для парсинга\n"
          "Например:\n"
          "'1' - выбрать одну категорию\n"
          "'1,2,3' - выбрать несколько категорий'\n")
    ans = input("Ввод: ")
    start = datetime.now()
    list_cat = list(map(int, ans.split(',')))

    urls = []
    # Добавляем ссылки категорий в список
    for num in list_cat:
        urls.append(scheme[num - 1][-1])

    processes = []

    # Создаем процессы под категории
    for url in urls:
        p = multiprocessing.Process(target=main, args=[url])
        processes.append(p)
        p.start()
    # Дожидаеся завершения процессов
    for p in processes:
        p.join()

    end = datetime.now() - start

    print(end)
