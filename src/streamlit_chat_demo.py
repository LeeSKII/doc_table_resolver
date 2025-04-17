import streamlit as st
from pymongo import MongoClient
import pandas as pd
import json
from datetime import datetime
from ollama import Client
import re
import json
from utils.llm import call_deepseek
from dotenv import load_dotenv
import os

load_dotenv()
# 获取环境变量
deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL")
deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")

def extract_last_result_query(text):
    """
    从文本中提取最后一个完整的 <result><query>...</query></result> 标签内容
    
    参数:
        text (str): 输入的文本内容
        
    返回:
        str: 最后一个完整的 <query> 标签内的内容，如果没有找到则返回 None
    """
    # 使用正则表达式匹配所有 <result><query>...</query></result> 块
    pattern = r'<result>\s*<query>(.*?)</query>\s*</result>'
    matches = re.findall(pattern, text, re.DOTALL)
    
    # 如果找到匹配项，返回最后一个
    if matches:
        return matches[-1].strip()
    else:
        return None

# 页面设置
st.set_page_config(page_title="智能数据助手", layout="wide")
st.title("🤖 智能数据查询助手")

# 初始化Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "query_history" not in st.session_state:
    st.session_state.query_history = []

system_prompt = '''
请根据用户提供的自然语言描述生成一个MongoDB的查询对象，除非用户明确指出待查询的关键字为精确匹配，否则查询对象应支持模糊匹配。
用户输入的内容放置在<input></input>标签中，根据以下步骤生成查询对象：
1. 首先识别用户是否是询问了关于某个问题，如“查找项目名称包含‘***’的记录”、“查找可能设备名称‘****’的信息”等，并提取关键词。
2. 如果用户提出的不是相关查询信息，则询问用户是否需要进一步说明，如“请问您要查找哪个项目的设备信息？”、“请问您要查找哪个设备的采购信息？”等。
3. 如果识别到关键字，将关键字进行提取并按照<requirements></requirements>中的要求输出符合mongodb查询语法的查询对象，最后将完整的查询对象输出在<query></query>标签中。
<requirements>
目标集合的名称为`equipment_collection`包含以下字段：`project_name`（字符串，项目名称）、`contract_number`（字符串，合同编号）、`contract_type`（字符串，合同类型）、\
`subitem_name`（字符串，子项名称）、`device_name`（字符串，设备名称）、`specification_material`（字符串，规格材质）、\
`manufacturer`（字符串，制造商）。
用户的需求是：查找与输入关键词相关的所有记录，关键词可能出现在上述任意字段中。
如果是模糊匹配要求（大小写不敏感），覆盖所有可能的数据，查询结果包含所有字段。
所有查询结果按'table_index'字段进行升序排列。
注意不要虚构任何数据并按照用户的需求进行查询。
构建的查询语句应该以`db.equipment_collection.find(${query_json})`为模板。
只需要提供完整的MongoDB查询对象`query_json`，输出在<query></query>标签中，完整的<query></query>标签由<result></result>包裹，确保语法正确。
</requirements>
'''

mongo_uri = "mongodb://localhost:27017/"

# 侧边栏配置
# with st.sidebar:
#     st.header("⚙️ 配置面板")
    
#     # MongoDB配置
#     st.subheader("MongoDB 设置")
#     mongo_uri = st.text_input(
#         "连接字符串",
#         "mongodb://localhost:27017/",
#         help="格式：mongodb://用户名:密码@地址:端口/"
#     )
#     db_name = st.text_input("数据库名称", "equipment_db")
#     collection_name = st.text_input("集合名称", "equipment_collection")
    
#     # 系统提示词编辑器
#     st.subheader("系统提示词")
#     system_prompt = st.text_area(
#         "定制系统指令",
#         height=200,
#         value=system_prompt
#     )
    


debug_mode = True

# MongoDB连接函数
@st.cache_resource(show_spinner=False)
def get_mongo_client(uri):
    try:
        return MongoClient(uri)
    except Exception as e:
        st.error(f"连接失败: {str(e)}")
        st.stop()

# 处理自然语言查询
def generate_query_ollama(nl_query:str):
    try:
        client = Client(
          host='http://192.168.43.41:11434',
          headers={'x-some-header': 'some-value'}
        )
        response = client.chat(model='qwq:latest', 
                              options={
                                  'temperature':0,
                                  "num_ctx": 4096,
                              },
                              messages=[
          {'role':'system', 'content': system_prompt},
          {
            'role': 'user',
            'content': f"<input>{nl_query}</input>"+"<think>\n",
          },
        ])
        result = response.message.content
        print("LLM响应信息:\n",result)
        result = extract_last_result_query(result)
        print("提取出的查询信息:\n",result)
        return json.loads(result)
    except Exception as e:
        if debug_mode:
            st.error(f"生成查询失败: {str(e)}")
        return None

def generate_query(nl_query:str):
    try:
        result = call_deepseek(deepseek_base_url, deepseek_api_key, f"<input>{nl_query}</input>",system_prompt)     
        print("LLM响应信息:\n",result)
        result = extract_last_result_query(result)
        print("提取出的查询信息:\n",result)
        return json.loads(result)
    except Exception as e:
        if debug_mode:
            st.error(f"生成查询失败: {str(e)}")
        return None

# 执行MongoDB查询
def execute_mongo_query(filter_query, limit=300):
    try:
        client = get_mongo_client(mongo_uri)
        db = client['equipment_db']
        collection = db['equipment_collection']
        
        # 执行查询
        try:
            results = list(db.equipment_collection.find(filter_query).limit(limit))
            
            if not results:
                st.warning("没有找到匹配的文档")
                st.stop()
                
        except Exception as e:
            st.error(f"查询失败: {str(e)}")
            st.stop()
        
        if not results:
            return None, "没有找到匹配的记录"
            
        df = pd.json_normalize(results)
        if '_id' in df.columns:
            df['_id'] = df['_id'].astype(str)
            
        return df, f"找到 {len(df)} 条记录"
    
    except Exception as e:
        return None, f"查询错误: {str(e)}"

# 显示聊天记录
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "dataframe" in message:
            st.dataframe(message["dataframe"], use_container_width=True)

# 用户输入处理
if prompt := st.chat_input("输入你的数据查询需求..."):
    # 添加用户消息
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # 生成查询
    with st.spinner("正在解析您的请求..."):
        query = generate_query(prompt)
        print("query:\n",query)
        
        
    if not query:
        st.error("无法生成有效查询")
        st.stop()
    
    # 执行查询
    with st.spinner("正在查询数据库..."):
        df, result_msg = execute_mongo_query(query)
    
    # 显示结果
    with st.chat_message("assistant"):
        if debug_mode:
            st.markdown(f"**生成的查询条件:**\n```json\n{json.dumps(query, indent=2)}\n```")
        
        if df is not None:
            st.success(result_msg)
            st.dataframe(df, use_container_width=True)
            
            # 保存到历史记录
            st.session_state.query_history.append({
                "query": prompt,
                "filter": query,
                "result_size": len(df)
            })
        else:
            st.warning(result_msg)
        
        # 保存消息记录
        response_content = {
            "content": f"**查询结果:** {result_msg}",
            "dataframe": df if df is not None else None
        }
        st.session_state.messages.append({"role": "assistant", **response_content})

# 显示查询历史
with st.expander("📚 查看查询历史"):
    if st.session_state.query_history:
        history_df = pd.DataFrame(st.session_state.query_history)
        st.dataframe(history_df[["query", "result_size"]], use_container_width=True)
    else:
        st.info("暂无历史查询记录")
