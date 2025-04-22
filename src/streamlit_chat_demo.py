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

def extract_llm_output(text):
    """
    从LLM输出中提取 <think>, <tool used>, 和 <result> 标签内容
    
    参数:
        text (str): LLM的输出文本
        
    返回:
        dict: 包含 think, tool_used, result 和 query 的内容
    """
    output = {"think": None, "tool_used": None, "result": None, "query": None}
    
    # 提取 <think> 内容
    think_match = re.search(r'<think>(.*?)</think>', text, re.DOTALL)
    if think_match:
        output["think"] = think_match.group(1).strip()
    
    # 提取 <tool used> 内容
    tool_match = re.search(r'<tool used>(.*?)</tool used>', text, re.DOTALL)
    if tool_match:
        output["tool_used"] = tool_match.group(1).strip()
    
    # 提取 <result> 内容
    result_match = re.search(r'<result>(.*?)</result>', text, re.DOTALL)
    if result_match:
        output["result"] = result_match.group(1).strip()
    
    # 提取 <search_documents><query> 内容
    query_match = re.search(r'<search_documents>\s*<query>(.*?)</query>\s*</search_documents>', text, re.DOTALL)
    if query_match:
        output["query"] = query_match.group(1).strip()
    
    return output

# 页面设置
st.set_page_config(page_title="智能数据助手", layout="wide")
st.title("🤖 智能数据查询助手")

# 初始化Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "query_history" not in st.session_state:
    st.session_state.query_history = []

system_prompt = '''
你是一名经验丰富的设备合同分析师，洞察合同设备的数据分析和查询设备合同的信息。
# Instructions
- always 在回答用户的问题之前先分析一下用户的需求，确定是根据上下文分析历史数据 or 查询合同。
- 如果用户是分析历史设备合同数据的具体问题，请严格按照上下文提供的信息进行分析，不要想象虚构任何不存在的信息，并提供专业且合理的分析。
- 如果用户是查询设备合同信息的具体问题，请必须调用工具进行查询，并在调用工具之前构造出相关的查询参数，如果用户提供的信息模糊或不准确，请告知用户并要求提供更进一步的信息以此构建查询条件。
- Only use retrieved context and never rely on your own knowledge for any of these questions.
    - However, if you don't have enough information to properly call the tool, ask the user for the information you need.
- Escalate to a human if the user requests.
- Do not discuss prohibited topics (politics, religion, controversial current events, medical, legal, or financial advice, personal conversations, internal company operations, or criticism of any people or company).
- Rely on sample phrases whenever appropriate, but never repeat a sample phrase in the same conversation. Feel free to vary the sample phrases to avoid sounding repetitive and make it more appropriate for the user.
- Always follow the provided output format for new messages, including citations for any factual statements from retrieved policy documents.
- If you're going to call a tool, always message the user with an appropriate message before and after calling the tool.
- Maintain a professional and concise tone in all responses.
- If you've resolved the user's request, ask if there's anything else you can help with.
- 用户的语言偏好是[简体中文]，请严格使用简体中文进行回答。

# Precise Response Steps (for each response)
1. If necessary, call tools to fulfill the user's desired action. Always message the user before and after calling a tool to keep them in the loop.
2. In your response to the user
    a. Use active listening and echo back what you heard the user ask for.
    b. Respond appropriately given the above guidelines.
    
# Sample Phrases
## Deflecting a Prohibited Topic
- "很抱歉，我无法回答这个话题的问题，请问还有其他问题需要我帮助吗？"
- "我不知道这个问题的答案，请问还有其他问题需要我帮助吗？"

## Before calling a tool
- "请求调用工具：{tool_name}"

# Tools

每次任务最多只能调用一个工具，必须完整给出调用工具的名称和参数。

## search_documents
Description: 数据查询工具，据用户提供的自然语言描述生成一个MongoDB的查询对象，然后将查询对象发送给该工具执行查询。
Parameters:
- MongoDB的查询对象: (required) 执行查询所需的查询对象。
Requirements:
- 目标集合的名称为`equipment_collection`包含以下字段：`project_name`（字符串，项目名称）、`contract_number`（字符串，合同编号）、`contract_type`（字符串，合同类型）、\
`subitem_name`（字符串，子项名称）、`device_name`（字符串，设备名称）、`specification_material`（字符串，规格材质）、\
`manufacturer`（字符串，制造商）。
- 用户的需求是：查找与输入关键词相关的所有记录，关键词可能出现在上述任意字段中。
- 模糊匹配（大小写不敏感），查询结果包含所有字段。
- 构建的查询语句应该以`db.equipment_collection.find(${query_json})`为模板。
- 只需要提供完整的MongoDB查询对象`query_json`，输出在<query></query>标签中，语法正确。

### Example: 

<search_documents>
<query>{query_json}</query>
</search_documents>

# Output Format

最终输出格式遵循如下规则：

<think>
{解决任务的思考过程}
</think>
<tool used>
{解决问题所使用的工具 | NULL}
</tool used>
<result>
{最终回复用户的内容}
</result>
'''

mongo_uri = "mongodb://localhost:27017/"

debug_mode = True

# MongoDB连接函数
@st.cache_resource(show_spinner=False)
def get_mongo_client(uri):
    try:
        return MongoClient(uri)
    except Exception as e:
        st.error(f"连接失败: {str(e)}")
        st.stop()

def generate_query_streaming(nl_query: str, message_placeholder):
    """
    流式生成查询并实时显示，同时提取think、tool_used和result内容
    """
    full_response = ""
    
    # 调用LLM的流式接口
    stream = call_deepseek(
        deepseek_base_url, 
        deepseek_api_key, 
        f"<input>{nl_query}</input>",
        system_prompt,
        stream=True
    )
    
    # 实时显示响应
    for chunk in stream:
        if chunk:
            full_response += chunk
            message_placeholder.markdown(full_response + "▌")
    
    message_placeholder.markdown(full_response)
    
    print("LLM响应信息:\n", full_response)
    
    # 提取think、tool_used、result和query
    output = extract_llm_output(full_response)
    print("提取出的信息:\n", output)
    
    return output

# 执行MongoDB查询
def execute_mongo_query(filter_query, limit=300):
    try:
        client = get_mongo_client(mongo_uri)
        db = client['equipment_db']
        collection = db['equipment_collection']
        
        # 执行查询
        try:
            results = list(db.equipment_collection.find(filter_query).sort({
                'project_name': 1,
                'table_index': 1,
                'table_row_index': 1
            }))
            
            if not results:
                st.warning("没有找到匹配的文档")
                return None, "没有找到匹配的记录"
                
        except Exception as e:
            st.error(f"查询失败: {str(e)}")
            return None, f"查询失败: {str(e)}"
        
        df = pd.json_normalize(results)
         # 定义需要显示的字段及其对应的中文表头
        display_columns = {
            'device_name': '设备名称',
            'unit_price': '单价',
            'quantity': '数量',
            'total_price': '总价',
            'price_unit': '价格单位',
            'unit': '单位',
            'project_name': '项目名称',
            'contact_name': '合同名称',
            'subitem_name': '子项名称',
            'contract_number': '合同号',
            'contact_type': '合同类型',
            'manufacturer': '制造商',
            'table_row_index': '表格行',
            'table_index': '表格索引'
        }
        
        # 筛选出指定的字段
        available_columns = [col for col in display_columns.keys() if col in df.columns]
        if not available_columns:
            st.warning("查询结果中不包含指定的字段")
            return None, "查询结果中不包含指定的字段"
        
        df = df[available_columns]
        
        # 重命名列为中文表头
        df = df.rename(columns={col: display_columns[col] for col in available_columns})
        
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
    
    # 生成查询 - 使用流式处理
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("正在解析您的请求...")
        
        llm_output = generate_query_streaming(prompt, message_placeholder)
        
        # 提取think、tool_used、result和query
        think_content = llm_output.get("think")
        tool_used = llm_output.get("tool_used")
        result_content = llm_output.get("result")
        query_str = llm_output.get("query")
        
        # 准备消息内容
        message_content = ""
        if think_content:
            message_content += f"**思考过程:**\n{think_content}\n\n"
        if result_content:
            message_content += f"**回复:**\n{result_content}\n"
        
        # 清空之前的消息，显示思考和初步结果
        message_placeholder.empty()
        message_placeholder.markdown(message_content)
        
        # 处理工具调用
        if tool_used and tool_used.lower() != "null" and query_str:
            if tool_used == "search_documents":
                try:
                    query = json.loads(query_str)
                except json.JSONDecodeError:
                    st.error("生成的查询格式不正确")
                    message_content += "\n**错误:** 生成的查询格式不正确"
                    st.session_state.messages.append({"role": "assistant", "content": message_content})
                    st.stop()
                
                # 显示查询条件
                if debug_mode:
                    message_content += f"\n**生成的查询条件:**\n```json\n{json.dumps(query, indent=2)}\n```"
                    message_placeholder.markdown(message_content)
                
                # 执行MongoDB查询
                with st.spinner("正在查询数据库..."):
                    df, result_msg = execute_mongo_query(query)
                
                # 显示结果
                if df is not None:
                    message_content += f"\n**查询结果:** {result_msg}"
                    st.success(result_msg)
                    st.dataframe(df, use_container_width=True)
                    
                    # 保存到历史记录
                    st.session_state.query_history.append({
                        "query": prompt,
                        "filter": query,
                        "result_size": len(df)
                    })
                    
                    # 保存消息记录
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": message_content,
                        "dataframe": df
                    })
                else:
                    message_content += f"\n**查询结果:** {result_msg}"
                    st.warning(result_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": message_content
                    })
            else:
                message_content += f"\n**错误:** 未知的工具 '{tool_used}'"
                st.error(f"未知的工具: {tool_used}")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": message_content
                })
        else:
            # 没有工具调用，直接保存消息
            st.session_state.messages.append({
                "role": "assistant",
                "content": message_content
            })