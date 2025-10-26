#!/usr/bin/env python3
"""
Скрипт для упрощения markdown документов под editor.js

Основные преобразования:
- Приведение всех заголовков к уровню 3 (###)
- Удаление чек-листов (преобразование в обычные списки)
- Раскрытие выпадающих блоков <details>/<summary>
- Упрощение смешанного форматирования (** и * в одной строке)
- Удаление HTML-тегов
"""

import re
import os
import configparser
from pathlib import Path
from typing import List


class ConfigManager:
    """
    Менеджер конфигурации для чтения настроек из ss.ini файла.
    
    Обеспечивает централизованное управление путями к директориям
    и другими параметрами скрипта упрощения Markdown файлов.
    """
    
    def __init__(self, config_file: str = 'ss.ini'):
        """
        Инициализация менеджера конфигурации.
        
        Args:
            config_file: Путь к файлу конфигурации
        """
        self.config_file = Path(config_file)
        self.config = configparser.ConfigParser()
        
    def load_config(self) -> bool:
        """
        Загружает конфигурацию из файла.
        
        Returns:
            bool: True если конфигурация загружена успешно, False иначе
        """
        if not self.config_file.exists():
            print(f"❌ Файл конфигурации {self.config_file} не найден!")
            print("   Создайте файл ss.ini с настройками директорий")
            return False
            
        try:
            self.config.read(self.config_file, encoding='utf-8')
            return True
        except Exception as e:
            print(f"❌ Ошибка чтения конфигурации: {e}")
            return False
    
    def get_simplify_directories(self) -> List[tuple]:
        """
        Получает список пар (исходная_директория, целевая_директория) для упрощения.
        
        Ищет пары с суффиксом '_simplify_source' и '_simplify_target'.
        
        Returns:
            List[tuple]: Список кортежей (source, target)
        """
        if not self.config.has_section('directories'):
            print("❌ Секция [directories] не найдена в конфигурации!")
            return []
        
        directories = []
        
        # Получаем все пары simplify_source-simplify_target из конфигурации
        for key, value in self.config['directories'].items():
            if key.endswith('_simplify_source'):
                # Ищем соответствующую simplify_target директорию
                target_key = key.replace('_simplify_source', '_simplify_target')
                if target_key in self.config['directories']:
                    source_path = Path(value)
                    target_path = Path(self.config['directories'][target_key])
                    directories.append((source_path, target_path))
        
        return directories
    
    def get_encoding(self) -> str:
        """
        Получает кодировку из конфигурации.
        
        Returns:
            str: Кодировка файлов (по умолчанию 'utf-8')
        """
        if self.config.has_section('settings') and 'encoding' in self.config['settings']:
            return self.config['settings']['encoding']
        return 'utf-8'


def normalize_headers(line: str) -> str:
    """
    Приводит все заголовки к уровню 3 (###)
    
    Параметры:
        line: Строка markdown
        
    Возвращает:
        Преобразованную строку с заголовком уровня 3
    """
    # Проверяем, является ли строка заголовком
    header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
    if header_match:
        # Всегда делаем заголовок 3 уровня
        return f"### {header_match.group(2)}"
    return line


def remove_checklists(line: str) -> str:
    """
    Убирает чек-листы, превращая их в обычные списки
    
    Параметры:
        line: Строка markdown
        
    Возвращает:
        Строку с обычным списком вместо чек-листа
    """
    # Убираем чекбоксы из списков
    # - [ ] текст -> - текст
    # - [x] текст -> - текст
    line = re.sub(r'^(\s*-)\s*\[([ xX])\]\s*', r'\1 ', line)
    return line


def simplify_mixed_formatting(line: str) -> str:
    """
    Упрощает смешанное форматирование (жирный + курсив в одной строке)
    
    Если в строке есть и ** и *, превращает всё форматирование в обычный текст.
    При этом сохраняет одинарное форматирование (только ** или только *)
    
    Параметры:
        line: Строка markdown
        
    Возвращает:
        Упрощенную строку
    """
    # Проверяем наличие смешанного форматирования в одной строке
    # Если есть и жирный (**) и курсив (*), удаляем всё форматирование
    has_bold = bool(re.search(r'\*\*[^*]+\*\*', line))
    has_italic = bool(re.search(r'(?<!\*)\*(?!\*)([^*]+)\*(?!\*)', line))
    
    if has_bold and has_italic:
        # Убираем всё форматирование
        # Сначала жирный текст
        line = re.sub(r'\*\*([^*]+)\*\*', r'\1', line)
        # Потом курсив
        line = re.sub(r'(?<!\*)\*(?!\*)([^*]+)\*(?!\*)', r'\1', line)
    
    return line


def fix_bold_colon_in_lists(line: str) -> str:
    """
    Исправляет проблему с editor.js: конструкция "- **Текст:** продолжение"
    
    Editor.js теряет текст после двоеточия в списках с жирным текстом.
    Преобразуем "- **Текст:** продолжение" в "- Текст: продолжение"
    
    ВАЖНО: Двоеточие может быть ВНУТРИ или СНАРУЖИ жирного текста:
    - "- **FUNCTION:** текст" → двоеточие внутри **
    - "- **FUNCTION**: текст" → двоеточие снаружи **
    
    Параметры:
        line: Строка markdown
        
    Возвращает:
        Исправленную строку
    """
    # Паттерн 1: двоеточие ВНУТРИ ** (самый частый случай)
    # Пример: "- **FUNCTION:** Вычисления..." или "1. **FUNCTION:** Вычисления..."
    pattern1 = r'^(\s*(?:-|\d+\.)\s+)\*\*([^*]+):\*\*\s*(.+)$'
    
    # Паттерн 2: двоеточие СНАРУЖИ **
    # Пример: "- **FUNCTION**: Вычисления..." или "1. **FUNCTION**: Вычисления..."
    pattern2 = r'^(\s*(?:-|\d+\.)\s+)\*\*([^*]+)\*\*:\s*(.+)$'
    
    if re.match(pattern1, line):
        # Убираем ** и оставляем двоеточие
        line = re.sub(pattern1, r'\1\2: \3', line)
    elif re.match(pattern2, line):
        # Убираем ** и сохраняем двоеточие
        line = re.sub(pattern2, r'\1\2: \3', line)
    
    return line


def fix_code_with_dash_in_lists(line: str) -> str:
    """
    Исправляет проблему с editor.js: конструкция "- `код` — пояснение"
    
    Editor.js теряет текст после backticks (обратных кавычек) с тире.
    Преобразуем "- `RAISE NOTICE` — информация" в "- RAISE NOTICE — информация"
    
    Также обрабатывает варианты с двоеточием:
    - "- `код` — пояснение"
    - "- `код` : пояснение"
    
    Параметры:
        line: Строка markdown
        
    Возвращает:
        Исправленную строку
    """
    # Паттерн 1: с длинным тире (—)
    # Пример: "- `RAISE NOTICE` — информация" или "1. `RAISE NOTICE` — информация"
    pattern_dash = r'^(\s*(?:-|\d+\.)\s+)`([^`]+)`\s*—\s*(.+)$'
    
    # Паттерн 2: с двоеточием
    # Пример: "- `PRIMARY KEY` : уникальность" или "1. `PRIMARY KEY` : уникальность"
    pattern_colon = r'^(\s*(?:-|\d+\.)\s+)`([^`]+)`\s*:\s*(.+)$'
    
    # Паттерн 3: с обычным дефисом + пробел (может быть спутан с тире)
    # Пример: "- `код` - пояснение" или "1. `код` - пояснение"
    pattern_hyphen = r'^(\s*(?:-|\d+\.)\s+)`([^`]+)`\s*-\s*(.+)$'
    
    if re.match(pattern_dash, line):
        # Убираем backticks, сохраняем длинное тире
        line = re.sub(pattern_dash, r'\1\2 — \3', line)
    elif re.match(pattern_colon, line):
        # Убираем backticks, сохраняем двоеточие
        line = re.sub(pattern_colon, r'\1\2: \3', line)
    elif re.match(pattern_hyphen, line):
        # Убираем backticks, сохраняем дефис
        line = re.sub(pattern_hyphen, r'\1\2 - \3', line)
    
    return line


def remove_bold_in_lists(line: str) -> str:
    """
    Убирает ВСЁ жирное форматирование (**текст**) в списках
    
    Editor.js полностью теряет содержимое жирного текста в списках.
    Примеры проблем:
    - "- Когда система **оптимальна**" → редактор видит только "Когда система"
    - "- 🔥 **70% проектов**" → редактор видит только "🔥"
    - "1. **Текст** в списке" → редактор видит только пустоту
    
    Решение: убираем ** полностью в списках (маркированных И нумерованных).
    
    Параметры:
        line: Строка markdown
        
    Возвращает:
        Строку без жирного форматирования в списках
    """
    # Проверяем, является ли строка элементом списка (маркированный или нумерованный)
    # Маркированный: - текст
    # Нумерованный: 1. текст, 2. текст и т.д.
    if re.match(r'^\s*(-|\d+\.)\s+', line):
        # Убираем ВСЁ жирное форматирование (**текст**)
        line = re.sub(r'\*\*([^*]+)\*\*', r'\1', line)
    
    return line


def remove_code_in_lists(line: str) -> str:
    """
    Убирает ВСЁ форматирование кода (`текст`) в списках
    
    Editor.js теряет содержимое внутри backticks в списках.
    Примеры проблем:
    - "- Убить запрос: `SELECT pg_terminate_backend(pid);`" → editor.js видит только "Убить запрос:"
    - "- Используйте `DROP TABLE` осторожно" → editor.js видит только "Используйте осторожно"
    - "1. `incident_id → analyst_id` (пояснение)" → editor.js теряет всё
    
    Решение: убираем ` полностью в списках, оставляя содержимое.
    
    Параметры:
        line: Строка markdown
        
    Возвращает:
        Строку без backticks в списках
    """
    # Проверяем, является ли строка элементом списка (маркированный или нумерованный)
    if re.match(r'^\s*(-|\d+\.)\s+', line):
        # Убираем ВСЁ форматирование кода (`текст`)
        line = re.sub(r'`([^`]+)`', r'\1', line)
    
    return line


def unify_nested_list_types(lines: List[str]) -> List[str]:
    """
    Унифицирует типы вложенных списков для совместимости с editor.js
    
    Editor.js не поддерживает смешанные списки (нумерованный + маркированный).
    Преобразование:
    - Если родитель нумерованный (1.) → вложенные тоже нумерованные
    - Если родитель маркированный (-) → вложенные тоже маркированные
    
    Пример:
    Было:
        1. Первый пункт
           - Подпункт A     ← маркированный внутри нумерованного
           - Подпункт B
    
    Станет:
        1. Первый пункт
           1. Подпункт A    ← нумерованный (как родитель)
           2. Подпункт B
    
    Параметры:
        lines: Список строк документа
        
    Возвращает:
        Обработанный список строк
    """
    result = []
    parent_type = None  # 'numbered' или 'bullet'
    parent_indent = 0   # Уровень отступа родителя
    nested_counter = 1  # Счётчик для вложенных нумерованных списков
    
    for i, line in enumerate(lines):
        # Определяем тип и отступ текущей строки
        stripped = line.lstrip()
        current_indent = len(line) - len(stripped)
        
        # Проверяем, является ли строка элементом списка
        is_numbered = re.match(r'^\d+\.\s+', stripped)
        is_bullet = re.match(r'^-\s+', stripped)
        
        if not is_numbered and not is_bullet:
            # Обычная строка (не список)
            result.append(line)
            # Если отступ меньше родительского - сбрасываем контекст
            if current_indent <= parent_indent:
                parent_type = None
                parent_indent = 0
                nested_counter = 1
            continue
        
        # Это элемент списка
        if current_indent == 0 or current_indent <= parent_indent:
            # Это родительский элемент (нет отступа или новый уровень)
            result.append(line)
            parent_indent = current_indent
            nested_counter = 1  # Сбрасываем счётчик для нового родителя
            
            if is_numbered:
                parent_type = 'numbered'
            elif is_bullet:
                parent_type = 'bullet'
        else:
            # Это вложенный элемент (есть отступ)
            if parent_type is None:
                # Нет родителя - оставляем как есть
                result.append(line)
                continue
            
            # Извлекаем текст после маркера списка
            if is_numbered:
                text = re.sub(r'^\d+\.\s+', '', stripped)
            elif is_bullet:
                text = re.sub(r'^-\s+', '', stripped)
            else:
                text = stripped
            
            # Преобразуем в тип родителя
            indent_spaces = ' ' * current_indent
            
            if parent_type == 'numbered':
                # Родитель нумерованный → вложенный тоже нумерованный
                result.append(f"{indent_spaces}{nested_counter}. {text}")
                nested_counter += 1
            else:
                # Родитель маркированный → вложенный тоже маркированный
                result.append(f"{indent_spaces}- {text}")
    
    return result


def remove_italic_in_lists(line: str) -> str:
    """
    Убирает ВСЁ форматирование курсивом (*текст*) в нумерованных списках
    
    Editor.js теряет содержимое внутри курсива в нумерованных списках:
    - "1. *incident_id → analyst_id* (пояснение)" → editor.js видит только "incident_id → analyst_id"
    
    Решение: убираем * в нумерованных списках, оставляя содержимое.
    
    Параметры:
        line: Строка markdown
        
    Возвращает:
        Строку без курсива в нумерованных списках
    """
    # Проверяем, является ли строка нумерованным списком
    if re.match(r'^\s*\d+\.\s+', line):
        # Убираем ВСЁ форматирование курсивом (*текст*)
        # Но НЕ трогаем markdown разделители типа * * *
        line = re.sub(r'(?<!\*)\*(?!\*)([^*]+)\*(?!\*)', r'\1', line)
    
    return line


def remove_inline_code_everywhere(line: str) -> str:
    """
    Убирает ВСЕ inline backticks (`текст`) из обычного текста
    
    Editor.js неправильно интерпретирует inline код в обычном тексте:
    - "таблицу `users` (avatar)" → создаёт блок кода "users1javascript"
    
    Решение: убираем все inline backticks, заменяя на курсив для технических терминов.
    НЕ трогаем блоки кода (строки, начинающиеся с ```)
    
    Параметры:
        line: Строка markdown
        
    Возвращает:
        Строку без inline backticks (backticks заменены на курсив)
    """
    # Пропускаем блоки кода (начинаются с ```)
    if line.strip().startswith('```'):
        return line
    
    # Пропускаем строки в таблицах (содержат | как разделители)
    if '|' in line and not line.strip().startswith('|'):
        # Это может быть строка таблицы, но не начало (начало обычно |---|---|)
        # Всё равно обрабатываем, но аккуратно
        pass
    
    # Убираем inline backticks, заменяя на курсив для технических терминов
    # `текст` → *текст* (курсив вместо кода)
    line = re.sub(r'`([^`]+)`', r'*\1*', line)
    
    return line


def wrap_technical_terms_in_italic_except_images(line: str) -> str:
    """
    Оборачивает технические термины в курсив, НО пропускает пути к изображениям
    
    Аналогично wrap_technical_terms_in_italic, но исключает обработку
    путей внутри ![alt](path) для сохранения корректности ссылок на изображения.
    """
    # Проверяем, есть ли в строке изображение ![alt](path)
    # Если есть, обрабатываем строку по частям, исключая путь к изображению
    pattern = r'(!\[[^\]]+\]\()([^\)]+)(\))'
    
    # Проверяем, содержит ли строка изображение
    if re.search(pattern, line):
        # Разбиваем строку на части: до изображения, путь, после изображения
        def process_without_image_path(match):
            before_path = match.group(1)  # ![alt](
            path = match.group(2)  # путь
            after_path = match.group(3)  # )
            # Обрабатываем части ДО и ПОСЛЕ пути отдельно
            before_processed = wrap_technical_terms_in_italic(before_path)
            after_processed = wrap_technical_terms_in_italic(after_path)
            # Собираем вместе, не трогая путь
            return before_processed + path + after_processed
        
        # Обрабатываем строку, защищая путь к изображению
        line = re.sub(pattern, process_without_image_path, line)
        return line
    
    # Если нет изображений, обрабатываем как обычно
    return wrap_technical_terms_in_italic(line)


def wrap_technical_terms_in_italic(line: str) -> str:
    """
    Оборачивает технические термины (идентификаторы БД) в курсив
    
    Editor.js автоматически превращает технические термины в JavaScript блоки:
    - "course_title и instructor" → "course_title1javascript и instructor1javascript"
    
    Решение: оборачиваем все технические термины в курсив заранее.
    
    Технические термины:
    - snake_case: слова с подчёркиванием (student_id, course_title)
    - Односложные латинские слова рядом с русским текстом (users, profiles)
    
    НЕ трогаем:
    - Блоки кода (```)
    - Строки таблиц (начинаются с |)
    - Списки (маркированные и нумерованные) — там всё форматирование убирается
    - Уже оформленный текст (внутри * или **)
    
    Параметры:
        line: Строка markdown
        
    Возвращает:
        Строку с техническими терминами в курсиве
    """
    # Пропускаем блоки кода
    if line.strip().startswith('```'):
        return line
    
    # Пропускаем строки таблиц (начинаются с | или содержат много |)
    if line.strip().startswith('|') or line.count('|') > 2:
        return line
    
    # Пропускаем уже обработанные строки (заголовки, горизонтальные линии)
    if line.strip().startswith('#') or line.strip() == '---':
        return line
    
    # ВАЖНО: Пропускаем списки (маркированные и нумерованные)
    # В списках editor.js теряет форматирование, поэтому там все термины - просто текст
    if re.match(r'^\s*(-|\d+\.)\s+', line):
        return line
    
    # Паттерн 1: snake_case термины (хотя бы один underscore)
    # Примеры: student_id, course_title, user_id
    # НЕ оборачиваем, если уже внутри * или **
    
    def wrap_snake_case(match):
        word = match.group(1)
        # Проверяем контекст - не находится ли уже внутри форматирования
        # Это приближённая проверка, не идеальная
        return f"*{word}*"
    
    # Ищем слова формата word_word (snake_case)
    # Но НЕ трогаем, если перед словом * или **
    line = re.sub(r'(?<![*])\b([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\b(?![*])', wrap_snake_case, line)
    
    # Паттерн 2: технические односложные термины (users, profiles, incidents и т.д.)
    # Только маленькие буквы, длина 4+ символов
    # НЕ трогаем: распространённые английские слова
    # НЕ трогаем: слова внутри составных слов (NULL-able)
    
    # Список исключений (обычные английские слова, которые НЕ нужно оборачивать)
    common_words = {
        'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'and', 'or', 'not', 'but', 'if', 'the', 'a', 'an',
        'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
        'as', 'it', 'this', 'that', 'from', 'all', 'can',
        'will', 'would', 'should', 'could', 'may', 'might',
        'do', 'does', 'did', 'have', 'has', 'had',
        'get', 'set', 'use', 'make', 'take', 'go', 'see',
        'new', 'old', 'first', 'last', 'next', 'one', 'two',
        'when', 'where', 'why', 'how', 'what', 'which',
        'some', 'any', 'many', 'much', 'few', 'more', 'most',
        'only', 'just', 'also', 'even', 'well', 'way', 'back',
        'time', 'year', 'work', 'part', 'case', 'over', 'than',
        'able', 'data', 'into', 'then', 'them', 'each', 'such'
    }
    
    # Находим латинские слова длиной 4+ символов
    # Оборачиваем в курсив, если НЕ в списке исключений
    # И НЕ внутри составного слова (после дефиса)
    def replace_tech_term(match):
        word = match.group(1)
        if word.lower() in common_words:
            return word  # Не трогаем распространённые слова
        return f"*{word}*"
    
    # Паттерн: латинское слово (4+ буквы, только маленькие)
    # НЕ после дефиса (чтобы не трогать NULL-able)
    # НЕ внутри * или **
    line = re.sub(r'(?<![-*])\b([a-z]{4,})\b(?![*])', replace_tech_term, line)
    
    return line


def fix_emoji_at_list_start(line: str) -> str:
    """
    Исправляет проблему с editor.js: эмодзи в начале списка
    
    Editor.js теряет весь текст после эмодзи в начале элемента списка.
    Примеры проблем:
    - "- 🔥 70% проектов" → editor.js видит только "🔥"
    - "- 📊 Типичный стек" → editor.js видит только "📊"
    
    Решение: добавляем двоеточие или тире после эмодзи как разделитель.
    
    Параметры:
        line: Строка markdown
        
    Возвращает:
        Строку с разделителем после эмодзи
    """
    # Проверяем, является ли строка элементом списка, начинающимся с эмодзи
    # Паттерн: начало строки, список (- или 1.), пробелы, эмодзи, опциональный variation selector, пробел, текст
    # Эмоджи определяем через диапазоны unicode + опциональный variation selector \uFE0F
    emoji_pattern = r'^(\s*(?:-|\d+\.)\s+)([\U0001F300-\U0001F9FF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\U00002600-\U000027BF\U0001F1E0-\U0001F1FF\U0001F900-\U0001F9FF\U0001FA70-\U0001FAFF][\uFE0F]?)\s+(.+)$'
    
    match = re.match(emoji_pattern, line)
    if match:
        # Добавляем двоеточие после эмодзи для разделения
        line = f"{match.group(1)}{match.group(2)}: {match.group(3)}"
    
    return line


def process_details_blocks(lines: List[str]) -> List[str]:
    """
    Раскрывает блоки <details>/<summary>, удаляя теги и оставляя содержимое
    
    ВАЖНО: Также удаляет строки-заголовки типа "👁️ Показать ответ",
    которые остались от summary и теперь бессмысленны (нет возможности скрыть).
    
    Параметры:
        lines: Список строк документа
        
    Возвращает:
        Обработанный список строк
    """
    result = []
    in_details = False
    in_summary = False
    summary_content = ""  # Сохраняем содержимое summary для проверки
    
    for line in lines:
        # Начало блока details
        if '<details>' in line.lower():
            in_details = True
            # Если на этой же строке есть текст, сохраняем его
            clean_line = re.sub(r'<details>', '', line, flags=re.IGNORECASE)
            if clean_line.strip():
                result.append(clean_line)
            continue
        
        # Тег summary - извлекаем содержимое, но НЕ добавляем в результат
        if '<summary>' in line.lower():
            in_summary = True
            # Извлекаем содержимое summary для анализа
            clean_line = re.sub(r'<summary>', '', line, flags=re.IGNORECASE)
            clean_line = re.sub(r'</summary>', '', clean_line, flags=re.IGNORECASE)
            summary_content = clean_line.strip()
            # НЕ добавляем в результат - эта строка будет удалена
            continue
        
        # Закрытие summary
        if '</summary>' in line.lower():
            in_summary = False
            summary_content = ""
            continue
        
        # Закрытие details
        if '</details>' in line.lower():
            in_details = False
            continue
        
        # Обычная строка - добавляем как есть
        result.append(line)
    
    return result


def remove_show_answer_headers(line: str) -> str:
    """
    Удаляет строки-заголовки типа "👁️ Показать ответ" или "Показать решение"
    
    Эти строки остались после раскрытия <details>/<summary> блоков.
    Теперь они бессмысленны (нет возможности скрыть контент).
    
    Паттерны для удаления:
    - "**👁️ Показать ответ**"
    - "**Показать решение**"
    - Любые варианты с "Показать"
    
    Параметры:
        line: Строка markdown
        
    Возвращает:
        None, если это заголовок "Показать..." (строка должна быть удалена)
        Исходную строку в остальных случаях (включая пустые строки!)
    """
    # Проверяем, является ли строка заголовком "Показать..."
    # Паттерны:
    # - **👁️ Показать ответ**
    # - **Показать решение**
    # - Показать ответ (без жирного)
    
    stripped = line.strip()
    
    # Пустые строки ВСЕГДА сохраняем (важно для разделения блоков!)
    if not stripped:
        return line
    
    # Убираем жирное форматирование для проверки
    clean = re.sub(r'\*\*([^*]+)\*\*', r'\1', stripped)
    
    # Проверяем паттерны "Показать ..."
    if re.match(r'^[👁️\s]*Показать\s+(ответ|решение|результат)', clean, re.IGNORECASE):
        return None  # Удаляем строку (возвращаем None, а не "")
    
    return line


def convert_markdown_links(line: str) -> str:
    """
    Преобразует markdown-ссылки в текст с URL в скобках для editor.js
    
    Editor.js не поддерживает markdown-ссылки [текст](url).
    Преобразуем так, чтобы сохранить и текст, и URL, но URL без протокола.
    
    ВАЖНО: Изображения (внутренние ссылки на файлы изображений) НЕ обрабатываются!
    - "![alt](./image.svg)" остается без изменений
    - "[текст](url)" преобразуется в "*текст (url)*"
    
    Преобразование:
    - "[PostgreSQL Docs](https://postgresql.org)" → "*PostgreSQL Docs (postgresql.org)*"
    - "[GitHub](https://github.com)" → "*GitHub (github.com)*"
    - "![INNER JOIN](./image.svg)" → "![INNER JOIN](./image.svg)" (БЕЗ ИЗМЕНЕНИЙ!)
    
    Параметры:
        line: Строка markdown
        
    Возвращает:
        Строку с преобразованными ссылками: *текст (url)*
    """
    # Список расширений изображений
    image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp']
    
    # Паттерн для markdown-ссылок: [текст](url) или ![alt](url)
    # НО пропускаем ссылки на изображения
    def replace_link(match):
        full_match = match.group(0)  # Вся ссылка [!text](url) или [text](url)
        optional_bang = match.group(1)  # Группа 1: `!` или пусто
        text = match.group(2)  # Группа 2: текст внутри []
        url = match.group(3)  # Группа 3: URL внутри ()
        
        # Проверяем, является ли это изображением (начинается с !)
        is_image = optional_bang == '!'
        
        # Проверяем, является ли URL путем к изображению
        is_image_path = any(url.lower().endswith(ext) for ext in image_extensions)
        
        # Если это изображение (начинается с ! или путь к изображению), НЕ ОБРАБАТЫВАЕМ
        if is_image or is_image_path:
            return full_match  # Возвращаем как есть
        
        # Для обычных ссылок - преобразуем
        # Убираем протокол из URL
        url_clean = re.sub(r'^https?://', '', url)
        return f'*{text} ({url_clean})*'
    
    # Паттерн: (!?) захватывает опциональный !, затем текст и URL
    line = re.sub(r'(!?)\[([^\]]+)\]\(([^)]+)\)', replace_link, line)
    
    return line


def remove_bare_urls(line: str) -> str:
    """
    Преобразует голые URL в текст с URL без протокола для editor.js
    
    Editor.js автоматически создаёт ссылки из URL типа https://example.com
    Чтобы предотвратить это, заменяем URL на текст с URL без протокола.
    
    Преобразование:
    - "https://www.postgresql.org/docs/" → "www.postgresql.org/docs/"
    - "http://example.com" → "example.com"
    - "www.example.com" → "www.example.com"
    
    Параметры:
        line: Строка markdown
        
    Возвращает:
        Строку с заменёнными URL без протокола
    """
    # Паттерны для различных типов URL
    # https:// или http:// URL - убираем протокол
    # Захватываем всё кроме пробелов и закрывающей скобки
    line = re.sub(r'https?://([^\s)]+)', r'\1', line)
    
    return line


def quote_operators_in_lists(line: str) -> str:
    """
    Оборачивает операторы в кавычки для предотвращения markdown-разметки
    
    Editor.js может неправильно интерпретировать операторы типа >= как цитаты.
    Оборачиваем их в кавычки, чтобы они отображались как обычный текст.
    
    Преобразование:
    - "-> — Возвращает JSON(B) объект" → "\"->\" — Возвращает JSON(B) объект"
    - ">= — Больше или равно" → "\">=\" — Больше или равно"
    - "!= — Не равно" → "\"!=\" — Не равно"
    
    НЕ трогает операторы в блоках кода (строки, начинающиеся с ```)
    НЕ трогает markdown-цитаты (строки, начинающиеся с "> ")
    
    Параметры:
        line: Строка markdown
        
    Возвращает:
        Строку с операторами в кавычках
    """
    # Проверяем, что это НЕ блок кода
    if line.strip().startswith('```'):
        return line
    
    # Проверяем, что это НЕ markdown-цитата (начинается с "> ")
    if re.match(r'^\s*>\s+', line):
        return line
    
    # Оборачиваем операторы в кавычки
    # Паттерны для различных операторов
    operators = [
        r'->',      # стрелка
        r'->>',     # двойная стрелка
        r'@>',      # оператор содержания
        r'\?',      # оператор существования
        r'<=',      # меньше или равно
        r'>=',      # больше или равно
        r'!=',      # не равно
    ]
    
    for op in operators:
        # Ищем оператор в строке (не только в списках)
        # Паттерн: начало строки или пробел, затем оператор, затем пробел или тире
        pattern = r'(\s|^)(' + op + r')(\s*—\s*|\s+)'
        replacement = r'\1"\2"\3'
        line = re.sub(pattern, replacement, line)
    
    return line


def remove_blockquotes(line: str) -> str:
    """
    Убирает markdown-цитаты (>) для совместимости с editor.js
    
    Editor.js не поддерживает блок-цитаты. Текст вставляется, но без визуального оформления.
    
    Преобразование:
    - "> Текст" → "Текст"
    - "> > Вложенная цитата" → "Вложенная цитата"
    - "> **Примечание:** текст" → "**Примечание:** текст"
    
    НЕ трогает операторы типа ->, ->>, @>, <=, >=, !=
    
    Параметры:
        line: Строка markdown
        
    Возвращает:
        Строку без символов цитирования (но с сохранением операторов)
    """
    # Убираем только markdown-цитаты: строки, начинающиеся с "> " (больше + пробел)
    # НЕ трогаем операторы типа ->, ->>, @>, <=, >=, !=
    line = re.sub(r'^(\s*>\s+)+', '', line)
    
    return line


def remove_html_tags(line: str) -> str:
    """
    Удаляет простые HTML теги, оставляя их содержимое
    
    Параметры:
        line: Строка markdown
        
    Возвращает:
        Строку без HTML тегов
    """
    # Удаляем теги <b>, <i>, <strong>, <em> и прочие простые теги
    line = re.sub(r'<b>([^<]+)</b>', r'**\1**', line, flags=re.IGNORECASE)
    line = re.sub(r'<i>([^<]+)</i>', r'*\1*', line, flags=re.IGNORECASE)
    line = re.sub(r'<strong>([^<]+)</strong>', r'**\1**', line, flags=re.IGNORECASE)
    line = re.sub(r'<em>([^<]+)</em>', r'*\1*', line, flags=re.IGNORECASE)
    
    # Удаляем прочие простые теги, оставляя содержимое
    line = re.sub(r'<([a-z]+)>([^<]+)</\1>', r'\2', line, flags=re.IGNORECASE)
    
    return line


def simplify_markdown_file(input_path: Path, output_path: Path, encoding: str = 'utf-8') -> None:
    """
    Обрабатывает один markdown файл, применяя все упрощения
    
    Параметры:
        input_path: Путь к исходному файлу
        output_path: Путь для сохранения результата
        encoding: Кодировка файлов (по умолчанию 'utf-8')
    """
    # Читаем исходный файл
    with open(input_path, 'r', encoding=encoding) as f:
        lines = f.readlines()
    
    # Убираем переносы строк для обработки
    lines = [line.rstrip('\n\r') for line in lines]
    
    # Раскрываем блоки details (обрабатываем весь документ сразу)
    lines = process_details_blocks(lines)
    
    # Унифицируем смешанные списки (обрабатываем весь документ сразу)
    lines = unify_nested_list_types(lines)
    
    # Построчная обработка
    processed_lines = []
    in_code_block = False  # Флаг: находимся ли внутри блока кода
    
    for line in lines:
        # Отслеживаем блоки кода (начало/конец ```)
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
            processed_lines.append(line)
            continue
        
        # Пропускаем обработку внутри блоков кода
        if in_code_block:
            processed_lines.append(line)
            continue
        
        # Удаляем бессмысленные заголовки "Показать ответ" (остались от <summary>)
        line = remove_show_answer_headers(line)
        if line is None:  # Если строка удалена (вернулся None), пропускаем
            continue
        
        # Нормализуем заголовки
        line = normalize_headers(line)
        
        # Убираем чек-листы
        line = remove_checklists(line)
        
        # ИСПРАВЛЕНИЕ: убираем жирное в списках с двоеточием (для editor.js)
        line = fix_bold_colon_in_lists(line)
        
        # ИСПРАВЛЕНИЕ: убираем backticks в списках с тире/двоеточием (для editor.js)
        line = fix_code_with_dash_in_lists(line)
        
        # ИСПРАВЛЕНИЕ: убираем ВСЁ жирное форматирование в списках (editor.js теряет текст)
        line = remove_bold_in_lists(line)
        
        # ИСПРАВЛЕНИЕ: убираем ВСЁ форматирование кода (`текст`) в списках (editor.js теряет текст)
        line = remove_code_in_lists(line)
        
        # ИСПРАВЛЕНИЕ: добавляем разделитель после эмодзи в начале списка (editor.js теряет текст)
        line = fix_emoji_at_list_start(line)
        
        # ОТКЛЮЧЕНО: Упрощаем смешанное форматирование
        # (теперь специально используем курсив для технических терминов)
        # line = simplify_mixed_formatting(line)
        
        # Удаляем HTML теги
        line = remove_html_tags(line)
        
        # ИСПРАВЛЕНИЕ: убираем блок-цитаты (>) - editor.js не поддерживает
        line = remove_blockquotes(line)
        
        # ИСПРАВЛЕНИЕ: убираем протоколы из URL ПЕРЕД преобразованием ссылок
        line = remove_bare_urls(line)
        
        # ИСПРАВЛЕНИЕ: преобразуем markdown-ссылки [текст](url) → *текст (url)*
        # ВАЖНО: ДО обёртки технических терминов, чтобы пути не оборачивались в курсив
        line = convert_markdown_links(line)
        
        # ИСПРАВЛЕНИЕ: оборачиваем операторы в кавычки в списках (предотвращает markdown-разметку)
        line = quote_operators_in_lists(line)
        
        # ИСПРАВЛЕНИЕ: убираем ВСЕ inline backticks везде (editor.js создаёт блоки кода)
        line = remove_inline_code_everywhere(line)
        
        # ИСПРАВЛЕНИЕ: оборачиваем технические термины в курсив (editor.js превращает их в код)
        # НО только если это НЕ путь к изображению
        line = wrap_technical_terms_in_italic_except_images(line)
        
        # ИСПРАВЛЕНИЕ: убираем курсив в нумерованных списках ПОСЛЕ обёртки терминов (editor.js теряет текст)
        line = remove_italic_in_lists(line)
        
        processed_lines.append(line)
    
    # Создаем директорию для вывода, если не существует
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Записываем результат
    with open(output_path, 'w', encoding=encoding) as f:
        f.write('\n'.join(processed_lines))
    
    print(f"✓ {input_path.name} → {output_path.name}")


def process_directory(source_dir: str, target_dir: str, encoding: str = 'utf-8') -> int:
    """
    Обрабатывает все markdown файлы в директории
    
    Параметры:
        source_dir: Исходная директория с файлами для упрощения (detailed)
        target_dir: Целевая директория для упрощенных файлов (simpled)
        encoding: Кодировка файлов (по умолчанию 'utf-8')
        
    Возвращает:
        Количество обработанных файлов
    """
    source_path = Path(source_dir)
    target_path = Path(target_dir)
    
    if not source_path.exists():
        print(f"⚠ Директория не найдена: {source_dir}")
        return 0
    
    # Находим все .md файлы
    md_files = list(source_path.glob('*.md'))
    
    if not md_files:
        print(f"⚠ Нет .md файлов в: {source_dir}")
        return 0
    
    count = 0
    for md_file in md_files:
        output_file = target_path / md_file.name
        simplify_markdown_file(md_file, output_file, encoding)
        count += 1
    
    return count


def main():
    """
    Главная функция скрипта упрощения Markdown файлов.
    
    Читает конфигурацию из ss.ini и обрабатывает директории
    согласно настройкам в конфигурационном файле.
    """
    print("🔧 Split and Simple - Упрощение Markdown документов для editor.js")
    print("=" * 70)
    
    # Инициализируем менеджер конфигурации
    config_manager = ConfigManager('ss.ini')
    
    # Загружаем конфигурацию
    if not config_manager.load_config():
        print("\n💡 Создайте файл ss.ini с настройками директорий:")
        print("""
[directories]
# Пример конфигурации для упрощения файлов
course_simplify_source = Course/Sections
course_simplify_target = Course/Simplified

[settings]
encoding = utf-8
""")
        return
    
    # Получаем список директорий для упрощения
    directories = config_manager.get_simplify_directories()
    
    if not directories:
        print("❌ Не найдено директорий для упрощения в конфигурации!")
        print("   Добавьте пары *_simplify_source и *_simplify_target в секцию [directories]")
        return
    
    # Получаем кодировку
    encoding = config_manager.get_encoding()
    
    print(f"📁 Найдено {len(directories)} пар директорий для упрощения")
    print(f"🔤 Кодировка файлов: {encoding}")
    print()
    
    total_processed = 0
    total_files = 0
    
    # Обрабатываем каждую пару директорий
    for source_dir, target_dir in directories:
        print(f"📂 Упрощение: {source_dir} -> {target_dir}")
        
        if not source_dir.exists():
            print(f"  ⚠️  Исходная директория {source_dir} не найдена")
            continue
        
        # Обрабатываем директорию
        try:
            files_count = process_directory(source_dir, target_dir, encoding)
            total_files += files_count
            total_processed += 1
            
            print(f"  ✅ Обработано файлов: {files_count}")
                
        except Exception as e:
            print(f"  ❌ Ошибка при обработке {source_dir}: {e}")
    
    print("\n" + "=" * 70)
    print(f"✓ Готово!")
    print(f"   Обработано директорий: {total_processed}")
    print(f"   Всего упрощено файлов: {total_files}")
    print("=" * 70)
    
    # Дополнительная информация о применённых преобразованиях
    print()
    print("Применённые преобразования:")
    print("  • Все заголовки приведены к уровню 3 (###)")
    print("  • Чек-листы превращены в обычные списки")
    print("  • Раскрыты выпадающие блоки <details>/<summary>")
    print("  • Унифицированы смешанные списки (вложенные списки того же типа, что родитель)")
    print("  • Удалены заголовки 'Показать ответ' (остались от <summary>)")
    print("  • Убраны блок-цитаты (> текст → текст) - editor.js не поддерживает")
    print("  • Преобразованы markdown-ссылки ([текст](url) → *текст (url)*)")
    print("  • Убраны протоколы из голых URL (https://... → ...)")
    print("  • Операторы обёрнуты в кавычки (->, ->>, @>, <=, >=, !=)")
    print("  • Исправлены списки с жирным текстом и двоеточием (- **Текст:** ...)")
    print("  • Исправлены списки с backticks и тире (- `код` — пояснение)")
    print("  • Убрано ВСЁ жирное форматирование в списках (маркированных + нумерованных)")
    print("  • Убраны ВСЕ backticks в списках (маркированных + нумерованных)")
    print("  • Убран курсив в нумерованных списках (1. *текст* → 1. текст)")
    print("  • Убраны ВСЕ inline backticks везде (`users` → *users*)")
    print("  • Технические термины обёрнуты в курсив вне списков (users, instructor)")
    print("  • Добавлено двоеточие после эмодзи в начале списка (- 🔥 текст → - 🔥: текст)")
    print("  • Удалены простые HTML теги")
    print()
    print("Результаты сохранены в:")
    print("  • " + str(source_dir))
    print("  • " + str(target_dir))


if __name__ == '__main__':
    main()

