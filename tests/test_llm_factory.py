import os
import sys

from agents.common.llm_factory import get_llm, get_llm_json

def _has_azure_env():
    need = ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_API_VERSION", "AZURE_OPENAI_DEPLOYMENT"]
    return all(os.getenv(k) for k in need)

def _has_bedrock_env():
    # 最低限リージョン・プロファイル（またはクレデンシャル）があるか
    return bool(os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION"))

def _try_invoke(llm, label: str):
    try:
        print(f"\n[{label}] trying llm.invoke('ping') ...")
        out = llm.invoke("次の単語だけを出力: pong")
        # LangChainのMessage/str 両対応
        txt = getattr(out, "content", None) or str(out)
        print(f"[{label}] OK -> {txt[:200]!r}")
    except Exception as e:
        print(f"[{label}] invoke failed: {e.__class__.__name__}: {e}")

def main():
    provider = os.getenv("LLM_PROVIDER", "azure").lower()
    print(f"LLM_PROVIDER={provider}")

    # 通常LLM
    llm = get_llm(temperature=0.2)
    print(f"get_llm -> {llm.__class__.__name__}")

    # JSON想定LLM
    llm_json = get_llm_json(temperature=0.0)
    print(f"get_llm_json -> {llm_json.__class__.__name__}")

    # 実呼び出しは環境が揃っている時だけ
    if provider == "azure" and _has_azure_env():
        _try_invoke(llm, "azure/freeform")
        _try_invoke(llm_json, "azure/json")
    elif provider == "bedrock" and _has_bedrock_env():
        # 例: export BEDROCK_MODEL_ID=meta.llama3-1-8b-instruct-v1:0
        print("BEDROCK_MODEL_ID=", os.getenv("BEDROCK_MODEL_ID"))
        _try_invoke(llm, "bedrock/freeform")
        _try_invoke(llm_json, "bedrock/json-ish")
    else:
        print("環境変数が不足しているため API 呼び出しはスキップします。")
        print("Azure例: AZURE_OPENAI_API_KEY / AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_API_VERSION / AZURE_OPENAI_DEPLOYMENT")
        print("Bedrock例: AWS_REGION（+ 認証は aws configure / SSO など）")

if __name__ == "__main__":
    main()