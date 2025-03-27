from ollama import Client
from dotenv import load_dotenv
import os
from openai import OpenAI
from time import time

def call_ollama(host:str, prompt:str, system_prompt:str,model:str,temperature=0,num_ctx=4096):
    client = Client(
        host=host,
    )
    response = client.chat(model=model, 
        options={
            'temperature':temperature,
            "num_ctx": num_ctx,
        },
        messages=[
            {'role':'system', 'content': system_prompt},
            {
                'role': 'user',
                'content': prompt,
            },
    ])
    return response.message.content

def call_deepseek(base_url:str, api_key:str, prompt:str, system_prompt:str, temperature=0):
    client = OpenAI(api_key=api_key, base_url=base_url)

    response = client.chat.completions.create(
        model="deepseek-chat",
        temperature=temperature,       
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        stream=False
    )
    return response.choices[0].message.content

if __name__ == '__main__':
    load_dotenv()
    # 获取环境变量
    deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL")
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
    t1 = time()
    print(f'Call ollama:',call_ollama('http://192.168.43.41:11434','你好','','qwq:latest'))
    t2 = time()
    print(f'Time cost of ollama:',t2-t1)
    print(f'Call deepseek:',call_deepseek(deepseek_base_url, deepseek_api_key,'你好',''))
    t3 = time()
    print(f'Time cost of deepseek:',t3-t1)
    
