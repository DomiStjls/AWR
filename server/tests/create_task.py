import requests

SERVER = "https://lucidly-liked-egret.cloudpub.ru"

# 1. Регистрация точек
points = [
    {"id": "PICKUP", "x": 0, "y": 0},
    {"id": "1", "x": 10, "y": 0},
    {"id": "2", "x": 20, "y": 0},
]
for p in points:
    print(requests.post(SERVER + "/register_qr", json=p).json())

# 2. Проверка точек
print(requests.get(SERVER + "/locations").json())
print(requests.get(SERVER + "/warehouses").json())
print(requests.get(SERVER + "/pickups").json())

# 3. Создание задач
tasks = [
    {"item": {"name": "Box1", "weight": 1}, "from": "PICKUP", "to": "1"},
    {"item": {"name": "Box2", "weight": 5}, "from": "PICKUP", "to": "2"},
    {"item": {"name": "Box3", "weight": 9}, "from": "PICKUP", "to": "2"},
    {"item": {"name": "Box4", "weight": 9}, "from": "PICKUP", "to": "1"},
    {"item": {"name": "Box5", "weight": 1}, "from": "1", "to": "2"},
]
for t in tasks:
    print(requests.post(SERVER + "/create_task", json=t).json())

# 4. Проверка задач и грузов
print(requests.get(SERVER + "/tasks").json())
print(requests.get(SERVER + "/items").json())

# 5. Робот берёт задачу
task = requests.get(SERVER + "/get_task").json()
print(task)

# 6. Робот завершает задачу
if "id" in task:
    print(requests.post(SERVER + "/task_done", json={"task_id": task["id"]}).json())

# 7. Проверка после выполнения
print(requests.get(SERVER + "/tasks").json())
print(requests.get(SERVER + "/warehouses").json())
print(requests.get(SERVER + "/pickups").json())

# 8. Статус робота
requests.post(SERVER + "/robot_status", json={"x": 5, "y": 3, "battery": 87, "state": "moving"})
print(requests.get(SERVER + "/robot_status").json())