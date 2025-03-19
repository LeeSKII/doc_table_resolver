from math import e
from tkinter import NO
from typing import List
from docx import Document
from ollama import Client
from pymongo import MongoClient
import xml.etree.ElementTree as ET
import re

file_path= "C:\\Lee\\files\\采购\\安阳钢铁集团有限责任公司综利公司烧结机头灰资源化处置项目（运营）\\04 渣浆泵备件采购合同.docx"
file_path = "C:\\Lee\\files\\03 循环风机采购合同.docx"
file_path= "C:\\Lee\\files\\采购\\安阳钢铁集团有限责任公司综利公司烧结机头灰资源化处置项目（运营）\\05 压滤机滤布采购合同.docx"
file_path ="C:\\Lee\\files\\采购\\others\\03 回转窑采购合同.docx"
file_path ="C:\\Lee\\files\\采购\\others\\12低压柜及三箱合同.docx"

system_prompt = '''
你是一位表格数据的识别判断专家，可以帮助分析提供的表格是否为设备\产品表格，用户提供表格内容位于<table></table>标签中，识别要求如下：
   1、首先判断是否为设备\产品表格：
      设备的表头一般出现在表格的前三行以内；
      常见的设备表格的表头字段通常包含但是不局限有：名称或者设备名称或产品，规格或者规格/材质或者型号，单位，数量，单价，总价，生产厂家等，
      如果主要字段基本符合设备表格的要求，名称或者设备名称是必需的，价格、单价、总价至少有一条是必需的，注意表头字段都是在同一行的。
      如果满足这些字段必须的条件，那么可以判断**是**设备表格,按以下分析策略:
    1.1、需要逐个分析原始表头字段，标准化表头到指定的字段：设备名称、规格/材质、单位、数量、生产厂家、单价、总价；
      （分析的时候注意：一、没有出现价格字段，那么默认单价就是价格；二、标准化字段没有出现在原始表格中，将其结果设置为“ ”空然后原始表格对应提取字段索引设置为-1。)
    1.2、分析设备表格表头字段：   
      分析的时候请遵循以下步骤：
      1.2.1、逐个分析表头字段：
        需要注意如果在分析价格字段的时候，将价格单位进行识别，常规是**元**或者**万元**（如果不属于二者其一，使用表格提供的原始单位数据），价格单位通常出现在价格字段之后，位于（）括号符号内；
      1.2.2、分别整理每个字段；
      1.2.3、最后检查索引和对应原始表格字段和标准化后字段的名称映射正确。
    1.3、 按照要求生成XML结构：
      1.3.1、检查是否所有标准字段都被覆盖：
        设备名称：有|无
        规格/材质：有|无
        单位：有|无
        数量：有|无
        生产厂家：有|无
        单价：有|无
        总价：有|无       
        
        最后生成如下格式的XML(start_row属性表示表头行索引，根据实际表头所在的行索引进行填写)，其中unit属性只有标准字段单价和总价才有：
        <fields start_row="0">
            <field original="名称" standard="设备名称" index="1"/>
            <field original="规格/材质" standard="规格/材质" index="2"/>
            <field original="单位" standard="单位" index="3"/>
            <field original="数量" standard="数量" index="4"/>
            <field original="生产厂家" standard="生产厂家" index="5"/>
            <field original="单价" standard="单价" unit="元" index="6"/>
            <field original="总价" standard="总价" unit="元" index="7"/>
        </fields>
  
   2、如果用户提供的表格**不是**一份设备表格，请直接返回空xml，格式为<xml></xml>，不需要做任何的标准化字段提取。
   
   **注意：请严格遵守以上约定，先识别是否是设备表格，再根据对应的结果进行输出,最终的显示结果仅包含XML。**
   
   在回答中请不要假设任何不属于用户提供的数据，并且不要虚拟数据，如实的根据用户提供的数据回答。
   
   以下是用户提供的表格数据：
'''

# 创建键的映射表（中英文对照）
key_mapping = {
    '设备名称': 'device_name',
    '规格/材质': 'specification_material',
    '数量': 'quantity',
    '生产厂家': 'manufacturer',
    '单价': 'unit_price',
    '总价': 'total_price',
    '价格单位': 'unit',
    'other_column': 'additional_info',
}


model_name = 'deepseek-r1:32b'
model_name = 'qwq:latest'

def chat_with_llm(user_content):
    client = Client(
        host='http://192.168.43.41:11434',
        headers={'x-some-header': 'some-value'}
    )
    response = client.chat(model=model_name, 
                        options={
                            'temperature':0,
                             "num_ctx": 4096,
                        },
                        messages=[
    {
        'role': 'user',
        'content': f"{system_prompt}<table>{user_content}</table>"+"<think>\n",
    },
    ])
    # print(response.message.content)

    return response.message.content

def is_valid_data(data_list):
    """
    检查列表中的每个字典是否都包含 'original', 'standard', 'index' 三个键。
    
    参数:
        data_list (list): 嵌套字典的列表
        
    返回:
        bool: 如果所有字典都包含所需键返回 True，否则返回 False
    """
    required_keys = {'original', 'standard','unit', 'index'}
    
    for item in data_list:
        if set(item.keys()) != required_keys:
            return False
    return True

def extract_xml_to_dict(text):
    """
    从文本中提取XML结构并解析为字典列表，同时提取根节点的start_row属性。
    适应新的XML结构，其中field元素通过属性original、standard、index定义。
    
    参数:
        text (str): 包含XML结构的文本
        
    返回:
        tuple: (字段字典列表, start_row值) 如果解析失败返回 (None, None)
    """
    # 使用正则表达式提取<fields>...</fields>部分
    pattern = r'<fields.*?>.*?</fields>'
    matches = re.findall(pattern, text, re.DOTALL)
    
    if not matches:
        return None, None  # 如果没有找到XML结构，返回None, None
    
    xml_string = matches[-1]  # 取匹配列表中的最后一个元素
    
    # 解析XML
    try:
        root = ET.fromstring(xml_string)
        
        # 提取start_row属性，默认为None如果不存在
        start_row = root.get('start_row', None)
        
        # 解析field元素
        result = []
        for field in root.findall('field'):
            # 直接从属性中提取信息
            field_dict = {
                'original': field.get('original', ''),
                'standard': field.get('standard', ''),
                'unit': field.get('unit', ''),
                'index': field.get('index', '')
            }
            result.append(field_dict)
        
        return result, start_row
    
    except ET.ParseError:
        return None, None  # 如果XML格式错误，返回None, None

def parse_table_to_objects(table, mapping_list:List, start_row=0):
    """
    根据映射列表从 python-docx 的 Table 对象中解析数据并转换为对象列表。
    未定义的表头字段将被聚合到 'other_column' 中。
    
    参数:
        table (docx.table.Table): python-docx 的表格对象
        mapping_list (list): 包含字典的列表，每个字典有 'original', 'standard', 'index' 键
        start_row (int): 开始解析的行号，默认为0
        
    返回:
        list: 解析后的对象列表，每个对象是一个字典
    """
    # 创建从原始标题到标准字段的映射
    header_mapping = {item['original']: item['standard'] for item in mapping_list}
    index_mapping = {item['original']: int(item['index']) for item in mapping_list}
    
    # 获取表头行（第一行）
    header_row = table.rows[0].cells
    headers = [cell.text.strip() for cell in header_row]
    
    # 验证表头是否与 mapping_list 中的 original 匹配，并找出未定义的表头
    undefined_headers = {}
    for idx, header in enumerate(headers):
        if header not in header_mapping and header != '':
            # print(f"警告: 表头 '{header}' 未在映射列表中定义，将被聚合到 other_column")
            undefined_headers[header] = idx
    
    # 解析数据行
    result = []
    start_row = int(start_row) + 1
    for row in table.rows[start_row:]:  # 从start_row+1行开始
        cells = [cell.text.strip() for cell in row.cells]
            
        # 创建对象
        obj = {}
        # 处理已定义的映射字段
        for original, standard in header_mapping.items():
            idx = index_mapping.get(original, -1)
            if idx >= 0 and idx < len(cells):  # 确保索引有效
                obj[standard] = cells[idx]
        
        # 价格单位字段直接添加
        price_dic_list =  list(filter(lambda x: x['standard']=='单价', mapping_list))
        if len(price_dic_list) > 0:
            obj['价格单位'] = price_dic_list[0]['unit']
        else:
            obj['价格单位'] = ''
        
        # 处理未定义的字段，聚合到 other_column
        if undefined_headers:
            other_column = {}
            for header, idx in undefined_headers.items():
                if idx < len(cells):  # 确保索引有效
                    other_column[header] = cells[idx]
            if other_column:  # 只有当有内容时才添加 other_column
                obj['other_column'] = other_column
                
        
        result.append(obj)
    
    return result


# 函数：根据映射表转换字典键
def transform_keys(data, mapping):
    if isinstance(data, dict):
        return {mapping.get(k, k): transform_keys(v, mapping) for k, v in data.items()}
    return data

# 连接到MongoDB
def save_to_mongodb(transformed_data):
    try:
        # 连接到本地MongoDB (根据你的实际配置修改连接字符串)
        client = MongoClient('mongodb://localhost:27017/')
        
        # 选择数据库和集合
        db = client['equipment_db']  # 数据库名
        collection = db['equipment_collection']  # 集合名
        
        # 插入数据
        result = collection.insert_one(transformed_data)
        print(f"数据插入成功，ID: {result.inserted_id}")
        
        # 关闭连接
        client.close()
    except Exception as e:
        print(f"发生错误: {str(e)}")

def parse_docx_tables(file_path):
    # 打开 .docx 文件
    doc = Document(file_path)
    # 遍历文档中的所有表格
    for table in doc.tables:
        print("找到一个表格：\n")
        table_context_list = []
        index = 0
        # 遍历表格的每一行
        for row in table.rows:
            row_data = []
            # 遍历每一行的每个单元格
            for cell in row.cells:
                row_data.append(cell.text.strip())  # 获取单元格文本并去除多余空格
            # print(row_data)  # 打印该行内容
            table_context_list.append(row_data)  # 将该行内容添加到表格内容列表中
            index += 1
            if index > 5:
                break
        table_context = '\n'.join('\t'.join(row) for row in table_context_list)
        table_objects = None
        # LLM继续数据分析
        llm_result = chat_with_llm(table_context)
        xml_result,start_row = extract_xml_to_dict(llm_result)
        if xml_result is not None:
            is_xml_valid = is_valid_data(xml_result)
        else:
            is_xml_valid = False
        if is_xml_valid:
            #print(f"表格内容：\n{table_context}")
            # print(f"XML结构：\n{xml_result}")
            table_objects = parse_table_to_objects(table, xml_result, start_row)
            # print(f"对象列表：\n{table_objects}")
            for obj in table_objects:
                db_data = transform_keys(obj, key_mapping)
                print(f"转换后的对象列表：\n{db_data}")
                try:                
                    save_to_mongodb(db_data)
                except Exception as e:
                    print(f"存储到MongoDB失败: {str(e)}")            
        elif xml_result is not None and is_xml_valid is False:
            print(xml_result)
            # TODO: 需要进入重试机制，重新分析表格内容
            print("LLM解析非有效XML结构，重新分析！")
            # LLM重新数据分析
            llm_result = chat_with_llm(table_context)
            xml_result,start_row = extract_xml_to_dict(llm_result)
            if xml_result is not None:
                is_xml_valid = is_valid_data(xml_result)
            else:
                is_xml_valid = False
                print("LLM重新解析失败！")
            if is_xml_valid:
                table_objects = parse_table_to_objects(table, xml_result, start_row)
                for obj in table_objects:
                    db_data = transform_keys(obj, key_mapping)
                    print(f"转换后的对象列表：\n{db_data}")
                    try:                
                        save_to_mongodb(db_data)
                    except Exception as e:
                        print(f"存储到MongoDB失败: {str(e)}")     
        else:
            print(f"表格内容：\n{table_context}")
            print(f"llm_result:\n{llm_result}")
            print("无XML结构!")
        
        # 存储表格
        if is_xml_valid and table_objects is not None:
            pass
        
        print("-" * 50)  # 分隔不同表格


parse_docx_tables(file_path)