import streamlit as st
from pymongo import MongoClient
import pandas as pd
import json

# 设置页面标题
st.title("MongoDB 数据查询展示")

# 连接 MongoDB
@st.cache_resource
def init_connection():
    # 从 secrets 获取连接信息（推荐方式）
    # 需要在 Streamlit 的 secrets.toml 中配置
    # mongo_uri = st.secrets["mongo"]["uri"]
    
    # 或直接写连接字符串（仅用于测试）
    mongo_uri = "mongodb://localhost:27017/"
    return MongoClient(mongo_uri)

client = init_connection()

# 选择数据库和集合
db_name = st.sidebar.selectbox("equipment_db", ["equipment_collection"])
collection_name = st.sidebar.text_input("输入集合名称", "equipment_collection")

# 获取集合对象
try:
    db = client["equipment_db"]
    collection = db[collection_name]
except Exception as e:
    st.error(f"连接失败: {str(e)}")
    st.stop()

# 查询条件输入
st.subheader("设置查询条件")
query_input = st.text_input('输入查询条件（JSON格式）', '{"contract_number": "BGYRHS-2023-14"}')

try:
    query = json.loads(query_input)
except json.JSONDecodeError:
    st.error("无效的JSON格式！")
    st.stop()

# 限制结果数量
limit = st.number_input("最大返回数量", min_value=1, value=100, step=1)

# 执行查询
try:
    results = list(db.equipment_collection.find(query).limit(limit))
    
    if not results:
        st.warning("没有找到匹配的文档")
        st.stop()
        
except Exception as e:
    st.error(f"查询失败: {str(e)}")
    st.stop()

# 转换为 DataFrame
df = pd.json_normalize(results)

# 处理 ObjectId 类型
if '_id' in df.columns:
    df['_id'] = df['_id'].astype(str)

# 显示结果
st.subheader("查询结果")
st.dataframe(df)  # 使用动态表格

# 显示原始数据开关
if st.checkbox("显示原始JSON数据"):
    st.write(results)

# 显示统计信息
st.subheader("统计信息")
st.write(f"找到 {len(df)} 条记录")
st.write("字段列表：", list(df.columns))

# 关闭连接（可选）
# client.close()