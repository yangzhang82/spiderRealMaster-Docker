import requests
import json
import time
import csv
from bs4 import BeautifulSoup
import os
import re
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging
from selenium.common.exceptions import TimeoutException
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)

# Path to your Microsoft Edge WebDriver
edgedriver_path = 'msedgedriver.exe'

# Load cookies from file
def load_cookies():
    """从文件加载cookies"""
    print("尝试从browser_cookies.json加载cookies...")
    try:
        with open('browser_cookies.json', 'r') as f:
            cookies = json.load(f)
        print(f"成功加载 {len(cookies)} 个cookies")
        return cookies
    except FileNotFoundError:
        print("错误: browser_cookies.json文件未找到。请确保该文件存在。")
        return []
    except json.JSONDecodeError:
        print("错误: browser_cookies.json文件格式不正确。")
        return []

# Headers to mimic browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

def get_page(url, driver):
    """使用Selenium获取页面内容"""
    print(f"正在获取页面: {url}")
    try:
        driver.get(url)
        print("等待页面加载...")
        time.sleep(3) # Give time for dynamic content to load
        print("页面加载成功")
        return driver.page_source
    except TimeoutException:
        print(f"错误: 页面加载超时: {url}")
        return None
    except Exception as e:
        print(f"错误: 获取页面时发生未知错误 {url}: {e}")
        return None

def parse_listing_detail(html, url):
    print("开始解析房源详情")
    soup = BeautifulSoup(html, 'html.parser')
    
    # 保存调试HTML文件
    try:
        # 从URL中提取一个安全的ID作为文件名的一部分
        listing_id_for_debug = url.split('/')[-1].split('?')[0] # 提取最后一个路径部分，并移除查询参数
        if not listing_id_for_debug: # 如果URL末尾没有有效部分，尝试从URL中获取一个唯一的名称
            listing_id_for_debug = hashlib.md5(url.encode()).hexdigest()[:8] # 使用MD5哈希的简化版
        debug_filename = f"debug_listing_detail_{listing_id_for_debug}.html"
        with open(debug_filename, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"房源详情HTML已保存到调试文件: {debug_filename}")
    except Exception as e:
        print(f"保存调试HTML文件时出错: {e}")

    # 提取房源ID
    listing_id = None
    price = None
    address = None
    bedrooms = None
    bathrooms = None
    garage = None
    
    # 优先从结构化数据 (LD+JSON) 中提取信息
    try:
        script_tag = soup.find('script', type='application/ld+json')
        if script_tag:
            json_data = json.loads(script_tag.string)
            # 由于JSON中可能有多个Product或Residence对象，我们需要遍历找到包含所需信息的对象
            for item in json_data:
                if item.get('@type') == 'Product' or item.get('@type') == 'Residence':
                    # 提取ID
                    if 'sku' in item:
                        listing_id = item['sku']
                    elif 'mpn' in item:
                        listing_id = item['mpn']
                    print(f"从JSON中找到房源ID: {listing_id}")

                    # 提取价格
                    if 'offers' in item and 'price' in item['offers']:
                        price = item['offers']['price']
                    print(f"从JSON中找到价格: {price}")

                    # 提取地址
                    if 'address' in item and item['address'].get('@type') == 'PostalAddress':
                        street = item['address'].get('streetAddress', '')
                        locality = item['address'].get('addressLocality', '')
                        region = item['address'].get('addressRegion', '')
                        address = f"{street}, {locality}, {region}".strip(', ')
                    print(f"从JSON中找到地址: {address}")

                    # 从description中提取卧室和浴室（如果需要）
                    description = item.get('description', '')
                    bed_match = re.search(r'(\d+)[Bb]d', description)
                    if bed_match:
                        bedrooms = bed_match.group(1)
                    bath_match = re.search(r'(\d+)[Bb]a', description)
                    if bath_match:
                        bathrooms = bath_match.group(1)
                    print(f"从JSON description中找到卧室: {bedrooms}, 浴室: {bathrooms}")
                    
                    # 提取车库信息
                    if 'GarageYN' in item and item['GarageYN'] == True:
                        garage = "Yes"
                    elif 'garage' in item and item['garage'] == True:
                        garage = "Yes"
                    print(f"从JSON中找到车库: {garage}")
                    
                    # 如果已经找到所有关键信息，则跳出循环
                    if listing_id and price and address and bedrooms and bathrooms and garage:
                        break
    except Exception as e:
        print(f"从LD+JSON提取数据时出错: {e}")
        # traceback.print_exc() # 调试时可以取消注释

    # 如果部分信息未从JSON中提取到，则尝试从HTML中提取作为备用
    if not listing_id:
        id_element = soup.find('div', class_='listing-id')
        if id_element:
            id_text = id_element.text.strip()
            id_match = re.search(r'MLS® #: (\d+)', id_text)
            if id_match:
                listing_id = id_match.group(1)
                print(f"从HTML中找到房源ID (备用): {listing_id}")

    if not price:
        price_element = soup.find('div', class_='listing-price')
        if price_element:
            price_text = price_element.text.strip()
            price_match = re.search(r'\$([\d,]+)', price_text)
            if price_match:
                price = price_match.group(1).replace(',', '')
                print(f"从HTML中找到价格 (备用): {price}")

    if not address:
        address_element = soup.find('div', class_='listing-address')
        if address_element:
            address = address_element.text.strip()
            print(f"从HTML中找到地址 (备用): {address}")
    
    # 卧室、浴室、车库的备用提取（使用新的class选择器）
    # 注意：这些字段可能以不同格式出现在HTML中，这里根据之前的grep结果进行调整
    if not bedrooms or not bathrooms or not garage:
        listing_prop_rooms = soup.find_all('span', class_='listing-prop-room')
        for prop_room in listing_prop_rooms:
            text = prop_room.find('span', recursive=False).text.strip() # 获取直接子span的文本
            if 'Bed' in prop_room.text:
                bedrooms = text
                print(f"从HTML中找到卧室数量 (备用): {bedrooms}")
            elif 'Bath' in prop_room.text:
                bathrooms = text
                print(f"从HTML中找到浴室数量 (备用): {bathrooms}")
            elif 'car' in prop_room.text: # Assuming 'fa fa-rmcar' icon indicates garage
                garage = text
                print(f"从HTML中找到车库数量 (备用): {garage}")

    square_footage = None
    lot_size = None
    land_size = None
    land_size_acres = None
    
    # 查找所有详细信息标签
    # 修改选择器以匹配新的HTML结构
    summary_rows = soup.find_all('div', class_='prop-summary-row')
    for row in summary_rows:
        label = row.find('span', class_='summary-label')
        value = row.find('span', class_='summary-value')
        
        if not label or not value:
            continue
            
        label_text = label.text.strip()
        value_text = value.text.strip()
        print(f"找到详细信息: {label_text} = {value_text}")
        
        if "Square Footage" in label_text:
            square_footage = value_text
            print(f"找到房屋面积: {square_footage}")
        elif "Lot Size" in label_text:
            lot_size = value_text
            print(f"找到地块大小: {lot_size}")
        elif "Land Size" in label_text:
            land_size_raw = value_text
            print(f"找到原始土地面积: {land_size_raw}")
            
            # 提取数值部分
            try:
                # 使用更灵活的正则表达式来匹配数字
                land_size_match = re.search(r'([\d,]+\.?\d*)', land_size_raw)
                if land_size_match:
                    land_size_numerical_str = land_size_match.group(1).replace(',', '')
                    land_size = float(land_size_numerical_str)
                    print(f"提取到土地面积数值: {land_size}")
                    
                    # 转换为英亩
                    land_size_acres = round(land_size / 43560, 2)
                    print(f"转换为英亩: {land_size_acres}")
                    
                    if land_size_acres < 1:
                        land_size_acres = 'N/A'
                        print("土地面积小于1英亩，设置为N/A")
                else:
                    print(f"无法从 '{land_size_raw}' 提取数值")
                    land_size = 'N/A'
                    land_size_acres = 'N/A'
            except Exception as e:
                print(f"处理土地面积时出错: {e}")
                land_size = 'N/A'
                land_size_acres = 'N/A'
    
    # 构建返回数据
    listing_data = {
        'url': url,
        'id': listing_id or 'N/A',
        'price': price or 'N/A',
        'address': address or 'N/A',
        'bedrooms': bedrooms or 'N/A',
        'bathrooms': bathrooms or 'N/A',
        'garage': garage or 'N/A',
        'Square Footage': square_footage or 'N/A',
        'Lot Size': lot_size or 'N/A',
        'Land Size': land_size or 'N/A',
        'Land Size (acres)': land_size_acres or 'N/A'
    }
    
    print("房源数据解析完成:")
    for key, value in listing_data.items():
        print(f"{key}: {value}")
    
    return listing_data

def format_city_name(city_name):
    """格式化城市名称，确保首字母和连字符后的字母大写"""
    # 分割城市名称（处理可能包含多个连字符的情况）
    parts = city_name.split('-')
    # 对每个部分进行首字母大写处理
    formatted_parts = [part.strip().capitalize() for part in parts]
    # 重新用连字符连接
    return '-'.join(formatted_parts)

def format_city_for_url(city_name):
    """格式化城市名称用于URL，保持空格并确保正确的大小写"""
    # 首先进行基本的大小写格式化
    formatted_city = format_city_name(city_name)
    # 保持空格，不替换为连字符
    return formatted_city

def main():
    print("\n=== 开始运行房源数据抓取程序 ===")
    
    # 获取用户输入
    province_input = input("请输入省份 (例如: Ontario): ").strip()
    city_input = input("请输入城市 (例如: Toronto): ").strip()

    # 格式化城市名称
    formatted_city = format_city_name(city_input)
    if formatted_city != city_input:
        print(f"注意: 城市名称已自动格式化为: {formatted_city}")
    city_input = formatted_city

    # 省份全名到代码的映射
    province_codes = {
        "Ontario": "ON",
        "British Columbia": "BC",
        "Alberta": "AB",
        "Quebec": "QC",
        "Manitoba": "MB",
        "Saskatchewan": "SK",
        "Nova Scotia": "NS",
        "New Brunswick": "NB",
        "Newfoundland and Labrador": "NL",
        "Prince Edward Island": "PE",
        "Yukon": "YT",
        "Northwest Territories": "NT",
        "Nunavut": "NU"
    }

    province_code = province_codes.get(province_input.title()) # 将输入转换为首字母大写进行查找
    if not province_code:
        print(f"错误: 无法识别省份 '{province_input}'。请检查输入是否正确。")
        return # 如果省份无效，退出程序

    # 格式化城市名称用于URL (保持空格，不替换为连字符)
    city_url_format = format_city_for_url(city_input)
    print(f"城市名称格式化后: {city_url_format}")

    # 构建指定城市和省份的基准URL
    base_url = f"https://www.realmaster.com/en/for-sale/{city_url_format}-{province_code}"
    print(f"构造的基准URL为: {base_url}")

    # 加载cookies
    cookies_list = load_cookies()
    if not cookies_list:
        print("错误: 未能加载cookies，请确保browser_cookies.json文件存在")
        return
    
    # 初始化Selenium WebDriver
    print("\n正在初始化Selenium WebDriver...")
    options = EdgeOptions()
    options.add_argument('--headless')  # 无头模式运行
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument(f'user-agent={HEADERS["User-Agent"]}')
    service = EdgeService(edgedriver_path)
    driver = webdriver.Edge(service=service, options=options)
    driver.set_page_load_timeout(30)
    print("Selenium WebDriver初始化完成")
    
    try:
        # 首先访问主页并设置cookies
        print("\n正在访问realmaster.com并设置cookies...")
        driver.get("https://www.realmaster.com")
        time.sleep(3)  # 等待页面加载
        
        # 设置cookies
        for cookie in cookies_list:
            try:
                selenium_cookie = {
                    'name': cookie['name'],
                    'value': cookie['value'],
                    'domain': cookie.get('domain', ''),
                    'path': cookie.get('path', '/'),
                    'secure': cookie.get('secure', False),
                    'httpOnly': cookie.get('httpOnly', False),
                    'sameSite': cookie.get('sameSite', 'Lax') if cookie.get('sameSite') and cookie.get('sameSite') != 'unspecified' else 'None'
                }
                if 'expirationDate' in cookie:
                    selenium_cookie['expiry'] = int(cookie['expirationDate'])
                driver.add_cookie(selenium_cookie)
            except Exception as e:
                print(f"设置cookie时出错: {e}")
                continue
        
        print("Cookies设置完成")
        
        # 验证登录状态
        print("\n正在验证登录状态...")
        driver.get("https://www.realmaster.com/en/account")
        time.sleep(5)
        
        if "Login" in driver.page_source:
            print("警告: 登录状态验证失败，请确保cookies有效")
            print("请重新登录网站并导出新的cookies")
            return
        
        print("登录状态验证成功")
        
        # --- 验证输入城市/省份的第一页是否有房源 --- #
        first_page_url = base_url
        print(f"\n正在验证城市和省份: {first_page_url}")
        print("正在加载页面...")
        driver.get(first_page_url)
        print("页面加载完成，等待页面渲染...")
        time.sleep(5)  # 给页面一些时间完全加载
        
        # 获取页面源码
        page_html = driver.page_source
        if not page_html:
            print(f"错误: 无法获取 {city_input}, {province_input} 的第一页数据，请检查输入或网络连接。")
            return
        
        # 检查是否需要登录
        if "Login To View More" in page_html:
            print("错误: 需要登录才能查看房源信息")
            print("请确保：")
            print("1. 已经登录 RealMaster 网站")
            print("2. cookies 文件是最新的")
            print("3. 重新导出 cookies 并更新 browser_cookies.json 文件")
            return
        
        soup_first_page = BeautifulSoup(page_html, 'html.parser')
        
        # 尝试提取总房源数量
        total_listings_on_site = "N/A"
        listings_found_element = soup_first_page.find(text=re.compile(r'\d+ Listings found'))
        if listings_found_element:
            total_listings_on_site = listings_found_element.strip()
            print(f"网站报告总房源数量: {total_listings_on_site}")
        else:
            print("未能找到网站报告的总房源数量信息。")

        listing_links_first_page = soup_first_page.find_all('a', class_='listing-prop')
        
        if not listing_links_first_page:
            print(f"错误: 未在 {city_input}, {province_input} 找到任何房源链接。")
            print("可能的原因：")
            print("1. 城市名称格式不正确")
            print("2. 该区域当前没有房源")
            print("3. 网站结构可能已更改")
            print("\n建议：")
            print("1. 请访问 RealMaster 网站，手动搜索该城市")
            print("2. 检查 URL 是否正确")
            print("3. 确保使用正确的城市名称格式")
            return
        print(f"在 {city_input}, {province_input} 的第一页找到 {len(listing_links_first_page)} 个房源。")
        # --- 验证结束 --- #

        # 创建CSV文件 - 移动到验证成功后
        csv_file = f'{city_input.lower().replace(" ", "_")}_{province_input.lower()}_listings.csv' # 动态文件名
        fieldnames = [
            'url', 'id', 'price', 'address', 'bedrooms', 'bathrooms', 'garage', 
            'Square Footage', 'Lot Size', 'Land Size', 'Land Size (acres)', 'city', 'province'
        ]
        
        print(f"\n正在创建CSV文件: {csv_file}")
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            print("CSV文件创建成功")
            
            # 开始抓取所有房源
            page_num = 0
            total_listings = 0
            
            while True:
                # 构建页面URL
                page_url = f"{base_url}?page={page_num}" if page_num > 0 else base_url
                print(f"\n正在获取第 {page_num + 1} 页: {page_url}")
                
                # 获取页面内容
                driver.get(page_url)
                time.sleep(5)  # 给页面一些时间完全加载
                page_html = driver.page_source
                
                if not page_html:
                    print(f"无法获取第 {page_num + 1} 页，停止抓取")
                    break
                
                # 检查是否需要登录
                if "Login To View More" in page_html:
                    print("错误: 登录状态已失效，请更新 cookies")
                    break
                
                # 解析页面获取房源链接
                soup = BeautifulSoup(page_html, 'html.parser')
                listing_links = soup.find_all('a', class_='listing-prop')
                
                if not listing_links:
                    print(f"第 {page_num + 1} 页没有找到房源链接，可能是最后一页")
                    break
                
                print(f"在第 {page_num + 1} 页找到 {len(listing_links)} 个房源")
                
                # 处理每个房源
                for link in listing_links:
                    listing_url = link['href']
                    print(f"\n正在处理房源: {listing_url}")
                    
                    # 获取房源详情
                    driver.get(listing_url)
                    time.sleep(5)  # 给页面一些时间完全加载
                    listing_html = driver.page_source
                    
                    if listing_html:
                        # 检查是否需要登录
                        if "Login To View More" in listing_html:
                            print("错误: 登录状态已失效，请更新 cookies")
                            break
                            
                        # 解析房源数据
                        listing_data = parse_listing_detail(listing_html, listing_url)
                        
                        # 添加城市和省份信息到字典
                        listing_data['city'] = city_input
                        listing_data['province'] = province_input

                        # 写入CSV
                        writer.writerow(listing_data)
                        total_listings += 1
                        print(f"成功保存房源数据，当前总计: {total_listings}")
                    else:
                        print(f"无法获取房源详情: {listing_url}")
                    
                    # 添加延时避免请求过快
                    time.sleep(5)
                
                # 检查是否有下一页
                next_button = soup.find('a', class_='listing-pagination-link')
                if not next_button:
                    print("没有找到下一页按钮，抓取完成")
                    break
                
                page_num += 1
                # 页面间添加延时
                time.sleep(10)
            
            print(f"\n抓取完成！共处理 {total_listings} 个房源")
    
    except Exception as e:
        print(f"\n程序运行出错: {e}")
        print("详细错误信息:")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n正在关闭WebDriver...")
        driver.quit()
        print("WebDriver已关闭")
        print("\n=== 程序运行结束 ===")

if __name__ == "__main__":
    main()