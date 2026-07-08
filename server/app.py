from flask import Flask, request, jsonify, abort, render_template
from flask_cors import CORS
import uuid

app = Flask(__name__)
CORS(app)  # Разрешаем CORS для всех маршрутов по умолчанию

# -----------------------------
# Хранилище (в памяти)
# -----------------------------

locations = {}  # Словарь всех точек {id: {"id":..., "type":..., "x":..., "y":...}}
warehouses = (
    {}
)  # Склады {id: {"capacity": int, "free_place": int, "items": [item_id, ...]}}
pickups = {}  # Пункты выдачи {id: {"items": [item_id, ...]}}
items = (
    {}
)  # Все грузы {item_id: {"id": int, "name": str, "weight": num, "location": str}}
tasks = (
    []
)  # Список задач [{"id": uuid, "item_id": int, "from": str, "to": str, "status": ...}, ...]

next_item_id = 1  # Счётчик для присвоения новых ID грузам

robot_status = {}
# -----------------------------
# Эндпоинты API
# -----------------------------


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register_qr", methods=["POST"])
def register_qr():
    """
    Регистрирует новую точку (склад или пункт выдачи).
    Ожидает JSON: { "id": int "x": float, "y": float }
    """
    data = request.get_json()
    if not data or "id" not in data or int(data["id"]) > 4:
        abort(400, "Missing 'id' or 'id' > 4")
    loc_id = data["id"]
    loc_type = "pickup" if len(pickups) == 0 else "warehouse"
    x = data.get("x")
    y = data.get("y")
    if loc_id in locations:
        abort(400, f"Location '{loc_id}' already exists")
    # Сохраняем общую информацию
    locations[loc_id] = {"id": loc_id, "type": loc_type, "x": x, "y": y}
    # Создаём конкретный объект склада или пункта выдачи
    if loc_type == "warehouse":
        capacity = 10
        warehouses[loc_id] = {"capacity": capacity, "free_place": capacity, "items": []}
    elif loc_type == "pickup":
        pickups[loc_id] = {"items": []}
    else:
        abort(400, "Type must be 'warehouse' or 'pickup'")
    return jsonify({"status": "ok", "location": locations[loc_id]}), 201


@app.route("/locations", methods=["GET"])
def get_locations():
    return jsonify(locations)


@app.route("/warehouses", methods=["GET"])
def get_warehouses():
    return jsonify(warehouses)


@app.route("/pickups", methods=["GET"])
def get_pickups():
    return jsonify(pickups)


@app.route("/create_item", methods=["POST"])
def create_item():
    """
    Создаёт новый груз.
    JSON запрос: { "name": str, "weight": number, "location": str? }.
    Если не указан location, кладёт в первый встреченный пункт выдачи.
    """
    global next_item_id
    data = request.get_json()
    if not data or "name" not in data or "weight" not in data:
        abort(400, "Missing 'name' or 'weight'")
    name = data["name"]
    weight = data["weight"]
    location = data.get("location")
    # Если не указан location, пытаемся найти любой пункт выдачи
    if location is None:
        if pickups:
            location = next(iter(pickups))
        else:
            abort(400, "No pickup defined for default location")
    # Проверяем существование указанного места
    if location not in pickups and location not in warehouses:
        abort(404, f"Location '{location}' not found")
    # Присваиваем новый ID и сохраняем груз
    item_id = next_item_id
    next_item_id += 1
    item = {"id": item_id, "name": name, "weight": weight, "location": location}
    items[item_id] = item
    # Помещаем ID груза в соответствующий список
    if location in pickups:
        pickups[location]["items"].append(item_id)
    else:
        # в склад — уменьшаем свободное место
        wh = warehouses[location]
        if weight > wh["free_place"]:
            abort(400, f"Not enough space in warehouse '{location}'")
        wh["items"].append(item_id)
        wh["free_place"] -= weight
    return jsonify(item), 201


@app.route("/create_task", methods=["POST"])
def create_task():
    """
    Создаёт новую задачу перевозки.
    JSON запроса: { "item_id": int, "from": str, "to": str }
    или { "item": { "name": str, "weight": num }, "from": str, "to": str, 'x': float, 'y': float }.
    """
    global next_item_id
    data = request.get_json()
    if not data or "from" not in data or "to" not in data:
        abort(400, "Missing 'from' or 'to'")
    src = data["from"]
    dst = data["to"]
    # Проверяем существование пунктов
    if src not in pickups and src not in warehouses:
        abort(404, f"Source '{src}' not found")
    if dst not in pickups and dst not in warehouses:
        abort(404, f"Destination '{dst}' not found")
    # Определяем item_id: либо передан, либо создаём новый груз
    item_id = None
    if "item_id" in data:
        item_id = data["item_id"]
        if item_id not in items:
            abort(404, f"Item ID {item_id} not found")
    elif "item" in data:
        item_info = data["item"]
        # Ожидаем поля name и weight
        if not item_info or "name" not in item_info or "weight" not in item_info:
            abort(400, "Item data must include 'name' and 'weight'")
        name = item_info["name"]
        weight = item_info["weight"]
        # Создаём новый item и добавляем в source
        item_id = next_item_id
        next_item_id += 1
        items[item_id] = {
            "id": item_id,
            "name": name,
            "weight": weight,
            "location": src,
        }
        # Помещаем груз в исходное место
        if src in pickups:
            pickups[src]["items"].append(item_id)
        else:
            wh_src = warehouses[src]
            if weight > wh_src["free_place"]:
                abort(400, f"Not enough space in warehouse '{src}' for new item")
            wh_src["items"].append(item_id)
            wh_src["free_place"] -= weight
    else:
        abort(400, "Missing 'item_id' or 'item' in request")
    # Проверяем, что груз действительно находится в src
    if items[item_id]["location"] != src:
        abort(400, f"Item {item_id} is not at source '{src}'")
    # Создаём задачу
    task = {
        "id": str(uuid.uuid4()),  # Генерируем уникальный ID задачи
        "item_id": item_id,
        "from": src,
        "to": dst,
        "status": "waiting",
    }
    tasks.append(task)
    return jsonify(task), 201


@app.route("/tasks", methods=["GET"])
def get_tasks():
    return jsonify(tasks)


@app.route("/get_task", methods=["GET"])
def get_task():
    """
    Робот запрашивает следующую задачу.
    Возвращает первую задачу со статусом "waiting" и переводит её в "assigned".
    При нехватке места в целевом складе задача пропускается.
    """
    for task in tasks:
        if task["status"] == "waiting":
            src = task["from"]
            dst = task["to"]
            item_id = task["item_id"]
            item = items.get(item_id)

            # Валидация
            if item is None:
                continue
            if item["location"] != src:
                continue
            # Проверяем свободное место (только если цель — склад)
            if dst in warehouses:
                wh_dst = warehouses[dst]
                if item["weight"] > wh_dst["free_place"]:
                    continue  # недостаёт места — пропустим эту задачу
            # Помечаем задачу назначенной и возвращаем её
            task["x_src"] = locations[src]["x"]
            task["y_src"] = locations[src]["y"]
            task["x_dst"] = locations[dst]["x"]
            task["y_dst"] = locations[dst]["y"]
            task["status"] = "assigned"
            task["task"] = "assigned"
            print(task)
            return jsonify(task)
    return jsonify({"task": None})


@app.route("/task_done", methods=["POST"])
def task_done():
    """
    Помечает задачу как выполненную.
    JSON запрос: { "task_id": str }.
    Переносит груз между from->to (обновляет свободное место складов) и статус задачи -> done.
    """
    data = request.get_json()
    if not data or "task_id" not in data:
        abort(400, "Missing 'task_id'")
    t_id = data["task_id"]
    # Ищем задачу
    task = next((t for t in tasks if t["id"] == t_id), None)
    if not task:
        abort(404, f"Task {t_id} not found")
    if task["status"] != "assigned":
        abort(400, "Task is not in 'assigned' status")
    # Переносим груз
    src = task["from"]
    dst = task["to"]
    item_id = task["item_id"]
    item = items.get(item_id)
    if not item:
        abort(404, f"Item {item_id} not found")
    # Удаляем из src
    if src in warehouses:
        wh_src = warehouses[src]
        if item_id in wh_src["items"]:
            wh_src["items"].remove(item_id)
            wh_src["free_place"] += item["weight"]
    elif src in pickups:
        if item_id in pickups[src]["items"]:
            pickups[src]["items"].remove(item_id)
    # Добавляем в dst
    if dst in warehouses:
        wh_dst = warehouses[dst]
        wh_dst["items"].append(item_id)
        wh_dst["free_place"] -= item["weight"]
    elif dst in pickups:
        pickups[dst]["items"].append(item_id)
    # Обновляем место нахождения груза
    item["location"] = dst
    task["status"] = "done"
    return jsonify({"status": "done", "task": task})


@app.route("/robot_status", methods=["POST"])
def update_robot():
    """
    Обновляет статус робота (любой JSON).
    """
    global robot_status
    robot_status = request.get_json() or {}

    return jsonify({"status": "ok"})


@app.route("/robot_status", methods=["GET"])
def get_robot():
    """
    Возвращает текущий статус робота (JSON, как был получен).
    """
    return jsonify(robot_status)


@app.route("/items", methods=["GET"])
def get_items():
    return jsonify(items)


# -----------------------------
# Ошибка по умолчанию
# -----------------------------


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": str(e)}), 404


@app.errorhandler(400)
def bad_request(e):
    return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
