from typing import Any, Dict, List, Optional
from app.core.config import Settings


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


class LLMClient(BaseModelClient):
    """文本大模型客户端（如 Qwen 文本模型）"""

    def __init__(self, settings: Settings):
        super().__init__(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
        )

    def chat(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """
        文本对话接口
        这里的具体调用你后面自己写
        """
        actual_model = model or self.model

        raise NotImplementedError(
            f"LLM chat not implemented yet. model={actual_model}, base_url={self.base_url}"
        )

    def chat_json(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        结构化 JSON 输出接口
        适合 query understanding
        """
        actual_model = model or self.model

        raise NotImplementedError(
            f"LLM chat_json not implemented yet. model={actual_model}, base_url={self.base_url}"
        )


class LVLMClient(BaseModelClient):
    """多模态大模型客户端（如 Qwen-VL）"""

    def __init__(self, settings: Settings):
        super().__init__(
            base_url=settings.lvlm_base_url,
            api_key=settings.lvlm_api_key,
            model=settings.lvlm_model,
        )

    def chat(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """
        多模态对话接口
        messages 里后面你可以自己塞 image_url / image base64 / text
        """
        actual_model = model or self.model

        raise NotImplementedError(
            f"LVLM chat not implemented yet. model={actual_model}, base_url={self.base_url}"
        )


class EmbeddingClient(BaseModelClient):
    """向量模型客户端（如 Jina Embedding）"""

    def __init__(self, settings: Settings):
        super().__init__(
            base_url=settings.embedding_base_url,
            api_key=settings.embedding_api_key,
            model=settings.embedding_model,
        )

    def embed_text(
        self,
        text: str,
        model: Optional[str] = None,
        **kwargs,
    ) -> List[float]:
        """
        单文本向量化
        """
        actual_model = model or self.model

        raise NotImplementedError(
            f"Embedding embed_text not implemented yet. model={actual_model}, base_url={self.base_url}"
        )

    def embed_texts(
        self,
        texts: List[str],
        model: Optional[str] = None,
        **kwargs,
    ) -> List[List[float]]:
        """
        批量文本向量化
        """
        actual_model = model or self.model

        raise NotImplementedError(
            f"Embedding embed_texts not implemented yet. model={actual_model}, base_url={self.base_url}"
        )