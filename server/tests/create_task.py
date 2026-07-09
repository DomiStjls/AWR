import requests

SERVER = "https://lucidly-liked-egret.cloudpub.ru"

# 1. Регистрация точек (id > 4 запрещён, поэтому только 4 точки)
points = [
    {"id": 0, "x": 0, "y": 0},    # pickup (первый всегда pickup)
    {"id": 1, "x": 10, "y": 0},   # warehouse
    {"id": 2, "x": 20, "y": 5},   # warehouse
    {"id": 3, "x": 15, "y": 10},  # warehouse
]
for p in points:
    print(requests.post(SERVER + "/register_qr", json=p).json())

# 2. Проверка точек
print("locations:", requests.get(SERVER + "/locations").json())
print("warehouses:", requests.get(SERVER + "/warehouses").json())
print("pickups:", requests.get(SERVER + "/pickups").json())

# 3. Создание задач
tasks = [
    {"item": {"name": "Box1", "weight": 1}, "from": 0, "to": 1},
    {"item": {"name": "Box2", "weight": 5}, "from": 0, "to": 2},
    {"item": {"name": "Box3", "weight": 9}, "from": 0, "to": 2},  # переполнит склад 2 (capacity=10, уже 5)
    {"item": {"name": "Box4", "weight": 2}, "from": 0, "to": 1},
    {"item": {"name": "Box5", "weight": 1}, "from": 1, "to": 2},  # перемещение между складами
]
for t in tasks:
    print(requests.post(SERVER + "/create_task", json=t).json())

# 4. Проверка задач и грузов
print("tasks:", requests.get(SERVER + "/tasks").json())
print("items:", requests.get(SERVER + "/items").json())

# 5. Робот берёт задачи по одной и завершает
for _ in range(5):
    task = requests.get(SERVER + "/get_task").json()
    print("got task:", task)
    
    # task приходит с полем "task" = "assigned" внутри, id в поле "id"
    if "id" in task and task.get("task") == "assigned":
        print("done:", requests.post(SERVER + "/task_done", json={"task_id": task["id"]}).json())
    else:
        print("no more tasks or task skipped")
        break

# 6. Проверка после выполнения
print("tasks after:", requests.get(SERVER + "/tasks").json())
print("warehouses after:", requests.get(SERVER + "/warehouses").json())
print("pickups after:", requests.get(SERVER + "/pickups").json())
print("items after:", requests.get(SERVER + "/items").json())

# 7. Статус робота
requests.post(SERVER + "/robot_status", json={"x": 5, "y": 3, "battery": 87, "state": "moving"})
print("robot:", requests.get(SERVER + "/robot_status").json())