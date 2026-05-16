from flask import Flask, request, jsonify
import psycopg2
from psycopg2.extras import execute_values

app = Flask(__name__)

# НАСТРОЙКА: Укажите здесь параметры вашей базы данных PostgreSQL
DB_CONFIG = (
    "host=127.0.0.1 "
    "port=5432 "
    "dbname=ut_bi_storage "  # Ваша BI-база
    "user=postgres "
    "password=ВАШ_РЕАЛЬНЫЙ_ПАРОЛЬ"  # Впишите ваш пароль
)

TYPE_MAPPING = {
    "TIMESTAMP": "TIMESTAMP",
    "BOOLEAN": "BOOLEAN",
    "UUID": "UUID",
    "TEXT": "TEXT"
}

# --- ЭНДПОИНТ 1: СОЗДАНИЕ СТРУКТУРЫ ТАБЛИЦ ---
@app.route('/api/create-table', methods=['POST'])
def create_table():
    try:
        data = request.json
        table_name = data['table_name']
        columns = data['columns']
        
        sql_parts = []
        for col_name, col_type in columns.items():
            sql_type = TYPE_MAPPING.get(col_type, col_type)
            if sql_type == "NUMBER":
                sql_type = "NUMERIC(15,2)"
            sql_parts.append(f'"{col_name}" {sql_type}')
            
        sql_parts.append('"etl_updated_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        create_query = f'CREATE TABLE IF NOT EXISTS public."{table_name}" ({", ".join(sql_parts)});'
        
        conn = psycopg2.connect(DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(create_query)
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"[УСПЕХ] Структура таблицы public.\"{table_name}\" создана/проверена.")
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"[ОШИБКА СТРУКТУРЫ] {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


# --- ЭНДПОИНТ 2: СВЕРХБЫСТРАЯ ЗАГРУЗКА ПАКЕТОВ ДАННЫХ ---
@app.route('/api/upload-data', methods=['POST'])
def upload_data():
    try:
        data = request.json
        table_name = data['table_name']
        rows = data['rows']
        
        if not rows:
            return jsonify({"status": "success", "message": "Пакет пуст"}), 200
            
        # Извлекаем имена колонок из ПЕРВОЙ строки полученного массива данных
        columns = list(rows[0].keys())
        
        # Превращаем массив JSON-объектов в плоский список кортежей значений для вставки
        values = [tuple(row[col] for col in columns) for row in rows]
        
        # Собираем динамический SQL-запрос пакетного импорта под стандартный executemany
        escaped_columns = ", ".join(f'"{col}"' for col in columns)
        placeholders = ", ".join(["%s"] * len(columns))
        insert_query = f'INSERT INTO public."{table_name}" ({escaped_columns}) VALUES ({placeholders})'
        
        # ВЫПОЛНЕНИЕ: Используем стандартный нативный метод ядра СУБД - executemany
        conn = psycopg2.connect(DB_CONFIG)
        cursor = conn.cursor()
        cursor.executemany(insert_query, values)
        conn.commit()
        
        cursor.close()
        conn.close()
        
        print(f"[УСПЕХ] В таблицу public.\"{table_name}\" загружена пачка из {len(rows)} строк!")
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        print(f"[ОШИБКА ЗАГРУЗКИ ДАННЫХ] {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
