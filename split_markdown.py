#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для разбивки больших Markdown файлов на отдельные файлы 
по заголовкам второго уровня (##).

Стратегия: Простая разбивка по ## без сохранения контекста.
Именование: {префикс_исходного_файла}_{номер_секции:02d}.md

Алгоритмическая сложность: O(n), где n - количество строк во всех файлах.
Пространственная сложность: O(m), где m - размер самого большого раздела.
"""

import os
import re
import configparser
from pathlib import Path
from typing import List, Dict, Tuple
from urllib.parse import unquote


class ConfigManager:
    """
    Менеджер конфигурации для чтения настроек из ss.ini файла.
    
    Обеспечивает централизованное управление путями к директориям
    и другими параметрами скрипта.
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
    
    def get_directories(self) -> List[Tuple[Path, Path]]:
        """
        Получает список пар (исходная_директория, целевая_директория) для разбивки.
        
        Обрабатывает только пары *_source и *_target, исключая пары для упрощения.
        
        Returns:
            List[Tuple[Path, Path]]: Список кортежей (source, target)
        """
        if not self.config.has_section('directories'):
            print("❌ Секция [directories] не найдена в конфигурации!")
            return []
        
        directories = []
        
        # Получаем только пары source-target для разбивки (исключаем simplify)
        for key, value in self.config['directories'].items():
            if key.endswith('_source') and not key.endswith('_simplify_source'):
                # Ищем соответствующую target директорию
                target_key = key.replace('_source', '_target')
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


class MarkdownSplitter:
    """
    Класс для разбивки Markdown файлов по заголовкам второго уровня.
    
    Использует конечный автомат для парсинга с учетом code blocks.
    """
    
    def __init__(self, source_dir: str, target_dir: str, encoding: str = 'utf-8'):
        """
        Инициализация сплиттера.
        
        Args:
            source_dir: Директория с исходными .md файлами
            target_dir: Директория для сохранения разбитых файлов
            encoding: Кодировка файлов (по умолчанию 'utf-8')
        """
        self.source_dir = Path(source_dir)
        self.target_dir = Path(target_dir)
        self.encoding = encoding
        
    def parse_markdown_file(self, file_path: Path) -> List[List[str]]:
        """
        Парсит Markdown файл и разбивает его на секции по ## заголовкам.
        
        Алгоритм:
        1. Читаем файл построчно (O(n))
        2. Отслеживаем состояние: внутри/снаружи code block
        3. При обнаружении ## (вне code block) создаем новую секцию
        4. НЕ сохраняем заголовок первого уровня - чистая разбивка
        
        Args:
            file_path: Путь к исходному файлу
            
        Returns:
            List[List[str]]: Список секций (каждая секция - список строк)
        """
        with open(file_path, 'r', encoding=self.encoding) as f:
            lines = f.readlines()
        
        sections = []
        current_section = []
        in_code_block = False
        
        for line in lines:
            # Отслеживаем code blocks (``` или ~~~)
            if line.strip().startswith('```') or line.strip().startswith('~~~'):
                in_code_block = not in_code_block
                current_section.append(line)
                continue
            
            # Если внутри code block, просто добавляем строку
            if in_code_block:
                current_section.append(line)
                continue
            
            # Проверяем на заголовок второго уровня (но не третьего и выше)
            if line.strip().startswith('## ') and not line.strip().startswith('### '):
                # Сохраняем предыдущую секцию (если есть и не пустая)
                if current_section and any(l.strip() for l in current_section):
                    sections.append(current_section)
                
                # Начинаем новую секцию с заголовка ##
                current_section = [line]
            else:
                current_section.append(line)
        
        # Сохраняем последнюю секцию (если не пустая)
        if current_section and any(l.strip() for l in current_section):
            sections.append(current_section)
        
        return sections
    
    def save_sections(self, sections: List[List[str]], file_prefix: str, source_filename: str) -> List[str]:
        """
        Сохраняет секции в отдельные файлы.
        
        Стратегия именования:
        {file_prefix}_{index:02d}.md
        
        Примеры:
        - 01_course_structure.md -> 01_01.md, 01_02.md, 01_03.md
        - 04_sql_basics.md -> 04_01.md, 04_02.md, ...
        
        Также обновляет относительные пути к изображениям для корректной работы
        в новой директории (например, ./image.svg → ../image.svg).
        
        Args:
            sections: Список секций (каждая - список строк)
            file_prefix: Префикс исходного файла (например, "01", "04")
            source_filename: Имя исходного файла для лога
            
        Returns:
            List[str]: Список путей созданных файлов
        """
        # Создаем целевую директорию, если не существует
        self.target_dir.mkdir(parents=True, exist_ok=True)
        
        # Вычисляем количество уровней вложенности для корректировки путей
        levels_up = self.calculate_path_adjustment()
        
        created_files = []
        
        # Подсчитываем общее количество исправленных путей
        total_paths_fixed = 0
        
        for idx, section in enumerate(sections, start=1):
            # Формируем имя файла: {префикс}_{номер}.md
            filename = f"{file_prefix}_{idx:02d}.md"
            file_path = self.target_dir / filename
            
            # Обрабатываем секцию: корректируем пути к изображениям
            adjusted_section = []
            paths_fixed_in_section = 0
            for line in section:
                adjusted_line = self.adjust_relative_path(line, levels_up)
                if adjusted_line != line:
                    paths_fixed_in_section += 1
                adjusted_section.append(adjusted_line)
            
            if paths_fixed_in_section > 0:
                total_paths_fixed += paths_fixed_in_section
            
            # Сохраняем содержимое
            content = ''.join(adjusted_section)
            with open(file_path, 'w', encoding=self.encoding) as f:
                f.write(content)
            
            created_files.append(str(file_path))
            print(f"✓ {source_filename} → {file_prefix}_{idx:02d}.md" + 
                  (f" ({paths_fixed_in_section} путей исправлено)" if paths_fixed_in_section > 0 else ""))
        
        return created_files
    
    def extract_file_prefix(self, filename: str) -> str:
        """
        Извлекает префикс из имени файла.
        
        Примеры:
        - "01_course_structure.md" -> "01"
        - "04_sql_basics.md" -> "04"
        - "14_final_defense.md" -> "14"
        
        Args:
            filename: Имя файла с расширением
            
        Returns:
            str: Префикс файла
        """
        # Убираем расширение
        name_without_ext = Path(filename).stem
        
        # Ищем паттерн: цифры в начале строки
        match = re.match(r'^(\d+)', name_without_ext)
        
        if match:
            return match.group(1)
        else:
            # Если нет числового префикса, используем первые 2 символа
            return name_without_ext[:2]
    
    def calculate_path_adjustment(self) -> int:
        """
        Вычисляет количество уровней вложенности для корректировки путей.
        
        Примеры:
        - source: Src/Base, target: Src/Base/detailed → возвращает 1
        - source: Src/Base, target: Src/Base/detailed/subdir → возвращает 2
        
        Returns:
            int: Количество уровней, на которые target глубже source (0 если на том же уровне)
        """
        # Приводим пути к абсолютным для корректного сравнения
        source_absolute = self.source_dir.resolve()
        target_absolute = self.target_dir.resolve()
        
        # Получаем части пути как список
        source_parts = source_absolute.parts
        target_parts = target_absolute.parts
        
        # Считаем общее количество частей пути, которые не совпадают
        # Если target вложен в source, то target имеет больше частей
        if len(target_parts) > len(source_parts):
            # Проверяем, является ли source родителем target
            if target_parts[:len(source_parts)] == source_parts:
                # Возвращаем разницу в уровнях
                return len(target_parts) - len(source_parts)
        
        return 0
    
    def is_image_path(self, path: str) -> bool:
        """
        Проверяет, является ли путь путем к изображению.
        
        Args:
            path: Путь к файлу
            
        Returns:
            bool: True если путь ведет к изображению
        """
        image_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp')
        path_lower = path.lower()
        return any(path_lower.endswith(ext) for ext in image_extensions)
    
    def adjust_relative_path(self, line: str, levels_up: int) -> str:
        """
        Корректирует относительные пути НЕ для изображений.
        
        Важно: Пути к изображениям (png, jpeg, svg, etc.) НЕ изменяются,
        так как Editor.js требует относительные пути вида ./image.svg.
        
        Обрабатывает только "голые" относительные ссылки БЕЗ префикса:
        - `[text](file.md)` → `[text](../file.md)` (если нужно подняться на 1 уровень)
        
        НЕ обрабатывает (оставляет без изменений):
        - Пути к изображениям (png, jpg, jpeg, svg, gif, webp, bmp)
        - Абсолютные пути (`/path/to/file`)
        - HTTP/HTTPS URLs
        - Пути, уже начинающиеся с `./` или `../`
        
        Args:
            line: Строка markdown для обработки
            levels_up: Количество уровней, на которые нужно подняться (например, 1 для ../)
            
        Returns:
            str: Строка с обновленными путями
        """
        if levels_up == 0:
            return line
        
        result = line
        
        # Паттерн для всех markdown ссылок: ![alt](path) или [text](path)
        markdown_link_pattern = re.compile(r'(!?)\[([^\]]*)\]\(([^\)]+)\)', re.IGNORECASE)
        
        def replace_link(match):
            is_image = match.group(1) == '!'  # Начинается с ! значит это изображение
            alt_or_text = match.group(2)
            old_path = match.group(3).strip()
            
            # Проверяем, не является ли путь абсолютным или URL (для всех)
            if old_path.startswith('http://') or old_path.startswith('https://'):
                return match.group(0)
            if old_path.startswith('/'):
                return match.group(0)
            
            # Проверяем, является ли путь путем к изображению
            if is_image or self.is_image_path(old_path):
                # Для изображений нужно исправить путь ./ на ../ при разбивке
                if old_path.startswith('./'):
                    # Убираем ./ и добавляем ../
                    file_path = old_path[2:]  # убираем ./
                    new_path = '../' * levels_up + file_path
                    return f'{match.group(1)}[{alt_or_text}]({new_path})'
                # Если уже начинается с ../, не трогаем
                if old_path.startswith('../'):
                    return match.group(0)
                # Если просто имя файла без префикса, добавляем ../
                new_path = '../' * levels_up + old_path
                return f'{match.group(1)}[{alt_or_text}]({new_path})'
            
            # Для НЕ-изображений: не трогаем, если уже есть ./ или ../
            if old_path.startswith('../'):
                return match.group(0)
            if old_path.startswith('./'):
                return match.group(0)
            
            # Это относительный путь к НЕ-изображению БЕЗ ./ или ../ в начале
            # Для НЕ-изображений не корректируем пути
            return match.group(0)
        
        result = markdown_link_pattern.sub(replace_link, result)
        
        return result
    
    def process_directory(self) -> None:
        """
        Обрабатывает все .md файлы в исходной директории.
        """
        print(f"\n{'='*60}")
        print(f"Обработка директории: {self.source_dir}")
        print(f"Целевая директория: {self.target_dir}")
        print(f"{'='*60}\n")
        
        # Находим все .md файлы только в корне директории (не во вложенных)
        md_files = [f for f in self.source_dir.iterdir() 
                   if f.is_file() and f.suffix == '.md']
        
        if not md_files:
            print(f"⚠️  В {self.source_dir} не найдено .md файлов")
            return
        
        total_sections = 0
        
        for md_file in sorted(md_files):
            # Парсим файл
            sections = self.parse_markdown_file(md_file)
            
            if not sections:
                print(f"⚠️  {md_file.name} - нет секций уровня ##")
                continue
            
            # Извлекаем префикс файла
            file_prefix = self.extract_file_prefix(md_file.name)
            
            # Сохраняем секции (вывод происходит внутри save_sections)
            created_files = self.save_sections(sections, file_prefix, md_file.name)
            
            total_sections += len(sections)
            
            # print(f"✓ {md_file.name} → {len(sections)} файлов ({file_prefix}_01.md - {file_prefix}_{len(sections):02d}.md)")
        
        print(f"\n{'='*60}")
        print(f"✅ ЗАВЕРШЕНО")
        print(f"   Обработано файлов: {len(md_files)}")
        print(f"   Создано секций: {total_sections}")
        print(f"{'='*60}\n")


def main():
    """
    Главная функция скрипта.
    
    Читает конфигурацию из ss.ini и обрабатывает директории
    согласно настройкам в конфигурационном файле.
    """
    print("🔧 Split and Simple - Разбивка Markdown файлов")
    print("=" * 60)
    
    # Инициализируем менеджер конфигурации
    config_manager = ConfigManager('ss.ini')
    
    # Загружаем конфигурацию
    if not config_manager.load_config():
        print("\n💡 Создайте файл ss.ini с настройками директорий:")
        print("""
[directories]
base_source = Src/Base
advanced_source = Src/Advanced
base_target = Src/Base/detailed
advanced_target = Src/Advanced/detailed

[settings]
encoding = utf-8
""")
        return
    
    # Получаем список директорий для обработки
    directories = config_manager.get_directories()
    
    if not directories:
        print("❌ Не найдено директорий для обработки в конфигурации!")
        return
    
    # Получаем кодировку
    encoding = config_manager.get_encoding()
    
    print(f"📁 {len(directories)} пар директорий, кодировка: {encoding}")
    
    total_processed = 0
    total_sections = 0
    
    # Обрабатываем каждую пару директорий
    for source_dir, target_dir in directories:
        print(f"📂 Обработка: {source_dir} -> {target_dir}")
        
        if not source_dir.exists():
            print(f"⚠️  {source_dir} не найден")
            continue
        
        # Создаем сплиттер с настройками из конфигурации
        splitter = MarkdownSplitter(source_dir, target_dir, encoding)
        
        # Обрабатываем директорию
        try:
            splitter.process_directory()
            total_processed += 1
            
            # Подсчитываем созданные секции (примерно)
            md_files = list(source_dir.glob('*.md'))
            if md_files:
                # Примерная оценка - можно улучшить, если нужно точное число
                total_sections += len(md_files) * 3  # Примерно 3 секции на файл
                
        except Exception as e:
            print(f"  ❌ Ошибка при обработке {source_dir}: {e}")
    
    print("\n" + "=" * 60)
    print(f"✅ ЗАВЕРШЕНО")
    print(f"   Обработано директорий: {total_processed}")
    print(f"   Примерное количество секций: {total_sections}")
    print("=" * 60)


if __name__ == '__main__':
    main()
