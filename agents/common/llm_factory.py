import os
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from langchain_aws import ChatBedrockConverse

from dotenv import load_dotenv
load_dotenv()


PROVIDER = os.getenv("LLM_PROVIDER", "azure").lower()


def _openai_base_url() -> str | None:
    return os.getenv("OPENAI_API_BASE") or os.getenv("OPENAI_BASE_URL")


def _openai_model(default: str = "google/gemma-3-12b-it") -> str:
    return os.getenv("OPENAI_MODEL", default)


def get_llm(temperature: float = 0.2):
    """通常応答用"""
    if PROVIDER == "azure":
        return AzureChatOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            temperature=temperature,
        )
    elif PROVIDER in ("openai", "openai_compat", "http"):
        # OpenAI互換API (API Gateway /v1/chat/completions)
        return ChatOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=_openai_base_url(),
            model=_openai_model(),
            temperature=temperature,
            streaming=False,
        )
    else:
        # Bedrock
        model_id = os.getenv("BEDROCK_MODEL_ID")
        return ChatBedrockConverse(
            model_id=model_id,
            region_name=os.getenv("AWS_REGION"),
            temperature=temperature,
        )


def get_llm_json(temperature: float = 0.0):
    """構造化出力（JSON）用"""
    if PROVIDER == "azure":
        return AzureChatOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            temperature=0.0,
            model_kwargs={"response_format": {"type": "json_object"}},
        )
    elif PROVIDER in ("openai", "openai_compat", "http"):
        # vLLM は response_format を厳密には解釈しないことがあります（無視されても害はない）
        return ChatOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=_openai_base_url(),
            model=_openai_model(),
            temperature=0.0,
            streaming=False,
        )
    else:
        model_id = os.getenv("BEDROCK_MODEL_ID")
        return ChatBedrockConverse(
            model_id=model_id,
            region_name=os.getenv("AWS_REGION"),
            temperature=temperature,
        )
