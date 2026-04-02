import json
from typing import Any, Dict, List, Optional
from app.core.config import Settings
import requests
from openai import OpenAI


class BaseModelClient:
    """所有模型客户端的基础类，只负责保存配置"""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        


class LLMClient:
    def __init__(self, settings: Settings):
        self.client = OpenAI(
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
            )
        self.model = settings.llm_model

    def chat(
        self,
        messages: List[Dict[str, Any]],
        thinking: bool = False,
        **kwargs
    ) -> str:
        if thinking:
            kwargs["extra_body"] = {"enable_thinking": True}
        else:
            kwargs["extra_body"] = {"enable_thinking": False}

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **kwargs
        )
        return completion.choices[0].message.content

    def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        thinking: bool = False,
        **kwargs
    ) -> Any:
        """
        流式输出接口，返回一个生成器，逐步产出模型的回复内容
        """
        if thinking:
            kwargs["extra_body"] = {"enable_thinking": True}
        else:
            kwargs["extra_body"] = {"enable_thinking": False}
            
        completion = self.client.chat.completions.create(
            model=self.model,  # 此处以qwen-plus为例，可按需更换模型名称。模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
            messages=messages,
            stream=True,
            stream_options={"include_usage": True},
            **kwargs
            )
        for chunk in completion:
            # print("Received chunk:", chunk)  # 调试输出，查看每个流式返回的内容
            if len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                text = delta.content
                yield text
    
    def chat_json(
        self,
        messages: List[Dict[str, Any]],
        thinking: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        if thinking:
            kwargs["extra_body"] = {"enable_thinking": True}
        else:
            kwargs["extra_body"] = {"enable_thinking": False}

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
            **kwargs,
        )

        content = response.choices[0].message.content
        return json.loads(content)


class LVLMClient(BaseModelClient):
    """多模态大模型客户端（如 Qwen-VL）"""

    def __init__(self, settings: Settings):
        self.client = OpenAI(
                api_key=settings.lvlm_api_key,
                base_url=settings.lvlm_base_url,
            )
        self.model = settings.lvlm_model

    def chat(
        self,
        messages: List[Dict[str, Any]],
        thinking: bool = False,
        **kwargs
    ) -> str:
        if thinking:
            kwargs["extra_body"] = {"enable_thinking": True}
        else:
            kwargs["extra_body"] = {"enable_thinking": False}

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **kwargs
        )
        return completion.choices[0].message.content

    def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        thinking: bool = False,
        **kwargs
    ) -> Any:
        """
        流式输出接口，返回一个生成器，逐步产出模型的回复内容
        """
        if thinking:
            kwargs["extra_body"] = {"enable_thinking": True}
        else:
            kwargs["extra_body"] = {"enable_thinking": False}
            
        completion = self.client.chat.completions.create(
            model=self.model,  # 此处以qwen-plus为例，可按需更换模型名称。模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
            messages=messages,
            stream=True,
            stream_options={"include_usage": True},
            **kwargs
            )
        for chunk in completion:
            # print("Received chunk:", chunk)  # 调试输出，查看每个流式返回的内容
            if len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                text = delta.content
                yield text
    
    def chat_json(
        self,
        messages: List[Dict[str, Any]],
        thinking: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        if thinking:
            kwargs["extra_body"] = {"enable_thinking": True}
        else:
            kwargs["extra_body"] = {"enable_thinking": False}

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
            **kwargs,
        )

        content = response.choices[0].message.content
        return json.loads(content)


class EmbeddingClient(BaseModelClient):
    def __init__(self, settings: Settings):
        super().__init__(
            base_url=settings.embedding_base_url,
            api_key=settings.embedding_api_key,
            model=settings.embedding_model,
        )

    def embed_content(
        self,
        contents: List[dict],
        model: Optional[str] = None,
        task: str = "text-matching",
        normalized: bool = True,
        return_multivector: bool = True,
        **kwargs,
    ) -> List[List[float]]:
        actual_model = model or self.model

        url = self.base_url
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload: Dict[str, Any] = {
            "model": actual_model,
            "task": task,
            "input": contents,
            "normalized": normalized,
            "return_multivector": return_multivector
        }
        payload.update(kwargs)

        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        return data["data"]
    

def test_embedding():
    settings = Settings()
    embedding_client = EmbeddingClient(settings)
    contents = [
        {"text": "这是一个测试"},
        {"text": "这是另一个测试"},
    ]
    embeddings = embedding_client.embed_content(contents)
    # return_multivector=True 时，输出是三维的嵌入向量列表，第一维是输入文本的数量，第二维是各项待嵌入数据的词元数量，第三维是每个词元向量的维度。
    print(len(embeddings), len(embeddings[0]["embeddings"]), len(embeddings[0]["embeddings"][0]))
    print(embeddings[0]["embeddings"][0])
    # return_multivector=False 时，输出是二维的嵌入向量列表，第一维是输入文本的数量，第二维是每个向量的维度。
    # print(len(embeddings), len(embeddings[0]["embedding"]))
    
def test_llm():
    settings = Settings()
    llm_client = LLMClient(settings)
    messages = [
        {"role": "system", "content": "你是一个有帮助的助手。"},
        {"role": "user", "content": "请介绍一下你自己。"}
    ]
    
    messages_json = [
        {
            "role": "system",
            "content": "你是一个助手，请用JSON格式返回结果"
        },
        {
            "role": "user",
            "content": "返回一个JSON对象，包含你自己的名字和功能介绍。例如：{\"name\": \"HealthAgent\", \"description\": \"我是一个健康助手，可以帮助你解答健康相关的问题。\"}"
        }
    ]
    
    response = llm_client.chat_json(messages_json)
    print(response)
    
    # for text in llm_client.stream_chat(messages):
    #     print(text, end="", flush=True)
    
def test_lvlm():
    settings = Settings()
    lvlm_client = LVLMClient(settings)
    messages_img=[{"role": "user","content": [
            {"type": "image_url",
             "image_url": {"url": "https://dashscope.oss-cn-beijing.aliyuncs.com/images/dog_and_girl.jpeg"}},
            {"type": "text", "text": "这是什么"},
            ]}]
    
    for text in lvlm_client.stream_chat(messages_img):
        print(text, end="", flush=True)
    
if __name__ == "__main__":
    test_embedding()
    # test_llm()
    # test_lvlm()
    
