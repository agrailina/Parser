import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from collections import deque


def get_contact_info(start_url: str) -> dict:
    """
    Парсер сайта для извлечения email адресов и номеров телефонов.
    
    Args:
        start_url: абсолютный URL сайта для парсинга
        
    Returns:
        Словарь в формате {"url": str, "emails": list[str], "phones": list[str]}
    """
    # Проверяем входной URL
    if not start_url.startswith(('http://', 'https://')):
        return {"url": start_url, "emails": [], "phones": []}
    
    # Настройки для запросов
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    # Извлекаем базовый домен
    parsed_url = urlparse(start_url)
    base_domain = parsed_url.netloc
    
    # Инициализация
    emails = set()
    phones = set()
    visited = set()
    queue = deque([start_url])
    
    max_pages = 10
    pages_visited = 0
    
    while queue and pages_visited < max_pages:
        url = queue.popleft()
        
        if url in visited:
            continue
        
        try:
            # Получаем страницу
            response = requests.get(url, headers=headers, timeout=10)
            
            # Пропускаем если не HTML
            if response.status_code != 200:
                visited.add(url)
                continue
            
            content_type = response.headers.get('content-type', '')
            if 'text/html' not in content_type:
                visited.add(url)
                continue
            
            # Парсим HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ищем email в mailto ссылках
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.startswith('mailto:'):
                    email = href[7:].strip()
                    if '@' in email and '.' in email:
                        # Убираем параметры
                        email = email.split('?')[0].split(' ')[0]
                        if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
                            emails.add(email)
            
            # Ищем email в тексте
            text = soup.get_text()
            email_matches = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', text)
            for email in email_matches:
                if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
                    emails.add(email)
            
            # Ищем телефоны в tel ссылках
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.startswith('tel:'):
                    phone = href[4:].strip()
                    cleaned = re.sub(r'[^\d+]', '', phone)
                    if len(cleaned) >= 10:
                        # Форматируем российские номера
                        if cleaned.startswith('8') and len(cleaned) == 11:
                            cleaned = '+7' + cleaned[1:]
                        elif cleaned.startswith('7') and len(cleaned) == 11:
                            cleaned = '+' + cleaned
                        phones.add(cleaned)
            
            # Ищем телефоны в тексте
            phone_patterns = [
                r'\+7[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}',
                r'8[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}',
                r'\b\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b'
            ]
            
            for pattern in phone_patterns:
                found = re.findall(pattern, text)
                for phone in found:
                    cleaned = re.sub(r'[^\d+]', '', phone)
                    if len(cleaned) >= 10:
                        if cleaned.startswith('8') and len(cleaned) == 11:
                            cleaned = '+7' + cleaned[1:]
                        elif cleaned.startswith('7') and len(cleaned) == 11:
                            cleaned = '+' + cleaned
                        phones.add(cleaned)
            
            visited.add(url)
            pages_visited += 1
            
            # Собираем ссылки для обхода
            for link in soup.find_all('a', href=True):
                href = link['href'].strip()
                
                # Пропускаем якоря и спец. ссылки
                if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                    continue
                
                # Преобразуем в абсолютный URL
                absolute_url = urljoin(url, href)
                parsed = urlparse(absolute_url)
                
                # Проверяем, что ссылка на тот же домен
                if parsed.netloc == base_domain or not parsed.netloc:
                    # Пропускаем файлы
                    path_lower = parsed.path.lower()
                    if any(path_lower.endswith(ext) for ext in [
                        '.jpg', '.jpeg', '.png', '.gif', '.pdf', '.zip', 
                        '.rar', '.doc', '.docx', '.xls', '.xlsx', '.mp3', 
                        '.mp4', '.avi', '.exe'
                    ]):
                        continue
                    
                    # Убираем параметры запроса для нормализации
                    normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                    if normalized.endswith('/'):
                        normalized = normalized[:-1]
                    
                    if normalized not in visited and normalized not in queue:
                        queue.append(normalized)
                        
        except Exception:
            visited.add(url)
            continue
    
    return {
        "url": start_url, 
        "emails": list(emails),
        "phones": list(phones)
    }


if __name__ == "__main__":
    # Пример использования
    test_url = input("Введите URL сайта: ").strip()
    
    if not test_url:
        test_url = "https://example.com"
    
    if not test_url.startswith(('http://', 'https://')):
        test_url = "http://" + test_url
    
    print(f"Парсинг сайта: {test_url}")
    result = get_contact_info(test_url)
    print(result)
