# Split and Simplify - Конфигурация и использование

## Описание
Скрипты `split_markdown.py` и `simplify_markdown.py` теперь используют единый внешний конфигурационный файл `ss.ini` для определения директорий обработки. Это делает оба скрипта более гибкими и переносимыми.

## Конфигурационный файл ss.ini

### Структура файла
```ini
# Split and Simplify - Конфигурация для разбивки и упрощения Markdown файлов
# Этот файл определяет директории для обработки курсов

[directories]
# Исходные директории с курсами
base_source = Src/Base
advanced_source = Src/Advanced

# Целевые директории для разбитых файлов (split)
base_target = Src/Base/detailed
advanced_target = Src/Advanced/detailed

# Директории для упрощенных файлов (simplify)
base_simplify_source = Src/Base/detailed
base_simplify_target = Src/Base/simpled
advanced_simplify_source = Src/Advanced/detailed
advanced_simplify_target = Src/Advanced/simpled

[settings]
# Кодировка файлов
encoding = utf-8

# Расширение файлов для обработки
file_extension = .md
```

### Секции конфигурации

#### [directories]
Содержит пары директорий для двух операций:

**Для разбивки (split):**
- `{name}_source` - исходная директория с Markdown файлами
- `{name}_target` - целевая директория для разбитых файлов

**Для упрощения (simplify):**
- `{name}_simplify_source` - исходная директория с разбитыми файлами
- `{name}_simplify_target` - целевая директория для упрощенных файлов

Можно добавить любое количество пар директорий для каждой операции.

#### [settings]
- `encoding` - кодировка файлов (по умолчанию: utf-8)
- `file_extension` - расширение файлов для обработки (по умолчанию: .md)

## Использование

### Разбивка файлов (split_markdown.py)
1. **Создайте файл конфигурации** `ss.ini` в корне проекта
2. **Настройте пути** к вашим директориям в секции `[directories]`
3. **Запустите скрипт**: `python split_markdown.py`

### Упрощение файлов (simplify_markdown.py)
1. **Убедитесь, что файл конфигурации** `ss.ini` существует
2. **Настройте пути** для упрощения в секции `[directories]`
3. **Запустите скрипт**: `python simplify_markdown.py`

## Преимущества новой архитектуры

### 🔧 Гибкость
- Легко добавлять новые пары директорий для любой операции
- Настройка кодировки файлов
- Возможность изменения расширений файлов
- Единая конфигурация для обоих скриптов

### 🚀 Переносимость
- Скрипты можно переносить между проектами
- Не нужно изменять код для разных структур директорий
- Конфигурация отделена от логики
- Оба скрипта используют одинаковый подход

### 🛡️ Надежность
- Проверка существования конфигурационного файла
- Обработка ошибок чтения конфигурации
- Информативные сообщения об ошибках
- Валидация директорий перед обработкой

### 📊 Мониторинг
- Подробная статистика обработки
- Отслеживание количества обработанных директорий
- Информация о созданных/упрощенных файлах
- Детальная информация о применённых преобразованиях

## Примеры конфигураций

### Минимальная конфигурация
```ini
[directories]
course_source = Course/Materials
course_target = Course/Sections
course_simplify_source = Course/Sections
course_simplify_target = Course/Simplified
```

### Расширенная конфигурация
```ini
[directories]
basic_source = Courses/Basic
basic_target = Courses/Basic/Detailed
basic_simplify_source = Courses/Basic/Detailed
basic_simplify_target = Courses/Basic/Simplified

advanced_source = Courses/Advanced  
advanced_target = Courses/Advanced/Detailed
advanced_simplify_source = Courses/Advanced/Detailed
advanced_simplify_target = Courses/Advanced/Simplified

practice_source = Practice/Exercises
practice_target = Practice/Split
practice_simplify_source = Practice/Split
practice_simplify_target = Practice/Simplified

[settings]
encoding = utf-8-sig
file_extension = .markdown
```

## Создание директорий

### ✅ Автоматическое создание целевых директорий
Оба скрипта **автоматически создают целевые директории**, если они не существуют:

- **`split_markdown.py`** создает директории для разбитых файлов (`*_target`)
- **`simplify_markdown.py`** создает директории для упрощенных файлов (`*_simplify_target`)

**Как это работает:**
- Создается вся цепочка родительских директорий (`parents=True`)
- Не вызывает ошибку, если директория уже существует (`exist_ok=True`)
- Например: `Src/Base/detailed` будет создана, даже если существует только `Src/`

### ⚠️ Что НЕ создается автоматически
- **Исходные директории** (`*_source`, `*_simplify_source`) - если их нет, скрипт выдаст предупреждение и пропустит обработку
- **Конфигурационный файл** `ss.ini` - его нужно создать вручную

## Обработка ошибок

Оба скрипта обрабатывают следующие ситуации:
- ❌ Отсутствие файла `ss.ini`
- ❌ Ошибки чтения конфигурации
- ❌ Отсутствие секции `[directories]`
- ⚠️ Несуществующие исходные директории
- ❌ Ошибки при обработке файлов
- ❌ Отсутствие пар директорий для конкретной операции

Во всех случаях выводится информативное сообщение с рекомендациями по исправлению.

## Workflow использования

1. **Настройка**: Создайте `ss.ini` с нужными директориями
2. **Разбивка**: Запустите `python split_markdown.py` для разбивки больших файлов
3. **Упрощение**: Запустите `python simplify_markdown.py` для упрощения разбитых файлов
4. **Результат**: Получите упрощенные файлы, готовые для editor.js
