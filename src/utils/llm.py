from ollama import Client
from dotenv import load_dotenv
import os
from openai import OpenAI
from time import time
from typing import Generator

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

def call_deepseek_stream(base_url: str, api_key: str, prompt: str, system_prompt: str, model_name: str = "deepseek-chat", temperature: float = 0):
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)

        response = client.chat.completions.create(
            model=model_name,
            temperature=temperature,       
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            stream=True
        )

        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content           
        else:
            return response.choices[0].message.content         

    except Exception as e:
        print(f'请求deepseek失败，原因：{e}')
        return None

def call_deepseek(base_url: str, api_key: str, prompt: str, system_prompt: str, model_name: str = "deepseek-chat", temperature: float = 0, stream: bool = False) -> str | Generator[str, None, None]:
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)

        # response = client.chat.completions.create(
        #     model=model_name,
        #     temperature=temperature,       
        #     messages=[
        #         {"role": "system", "content": system_prompt},
        #         {"role": "user", "content": prompt},
        #     ],
        #     stream=stream
        # )

        # if stream:
        #     for chunk in response:
        #         if chunk.choices[0].delta.content is not None:
        #             yield chunk.choices[0].delta.content
        # else:
        #     return response.choices[0].message.content
        response = client.chat.completions.create(
            model=model_name,
            temperature=temperature,       
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
        )

        return response.choices[0].message.content
            

    except Exception as e:
        print(f'请求deepseek失败，原因：{e}')
        return None
    
if __name__ == '__main__':
    load_dotenv()
    # 获取环境变量
    deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL")
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
    t1 = time()
    # print(f'Call ollama:',call_ollama('http://192.168.43.41:11434','你好','','qwq:latest'))
    # t2 = time()
    # print(f'Time cost of ollama:',t2-t1)
    response = call_deepseek(deepseek_base_url, deepseek_api_key,'你好','','deepseek-chat',0,False)
    print(f'Call deepseek:',response)
    t3 = time()
    print(f'Time cost of deepseek:',t3-t1)
    
