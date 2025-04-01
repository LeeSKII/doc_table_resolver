from pymongo import MongoClient
import time

def log_to_mongodb(log_data: dict):
    log_data = log_data | {'created_time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}
    try:
        # 连接到本地MongoDB (根据你的实际配置修改连接字符串)
        client = MongoClient('mongodb://localhost:27017/')
        
        # 选择数据库和集合
        db = client['equipment_db']  # 数据库名
        collection = db['equipment_log_collection']  # 集合名
        
        # 插入数据
        result = collection.insert_one(log_data)
        # print(f"日志记录成功，ID: {result.inserted_id}")
        
        # 关闭连接
        client.close()
    except Exception as e:
        print(f"发生错误: {str(e)}")