# Implement utility functions here

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage

# from django.conf import settings
import os

def get_message_text(msg: BaseMessage) -> str:
    """Get the text content of a message."""
    content = msg.content
    if isinstance(content, str):
        return content
    elif isinstance(content, dict):
        return content.get("text", "")
    else:
        txts = [c if isinstance(c, str) else (c.get("text") or "") for c in content]
        return "".join(txts).strip()


def load_chat_model(fully_specified_name: str) -> BaseChatModel:
    """Load a chat model from a fully specified name.

    Args:
        fully_specified_name (str): String in the format 'provider/model'.
    """
    provider, model = fully_specified_name.split("/", maxsplit=1)

    # AWS - claude-3-5-sonnet-20240620-v1:0
    if provider == "bedrock" and model == "anthropic.claude-3-5-sonnet-20240620-v1:0":
        return init_chat_model(model, model_provider=provider, temperature=0.3, region="us-east-1")

    # AWS - anthropic.claude-3-5-sonnet-20241022-v2:0
    if provider == "bedrock" and model == "anthropic.claude-3-5-sonnet-20241022-v2:0":
        return init_chat_model("us.anthropic.claude-3-5-sonnet-20241022-v2:0", model_provider=provider, temperature=0.3, region="us-east-1") 
    
    # AWS - meta.llama3-2-90b-instruct-v1:0
    elif provider == "bedrock" and model == "meta.llama3-2-90b-instruct-v1:0":
        return init_chat_model("us.meta.llama3-2-90b-instruct-v1:0", model_provider=provider, temperature=0.3, region="us-east-1") 
    
    # AWS - meta.llama3-1-70b-instruct-v1:0
    elif provider == "bedrock" and model == "meta.llama3-1-70b-instruct-v1:0":
        return init_chat_model("us.meta.llama3-1-70b-instruct-v1:0", model_provider=provider, temperature=0.3, region="us-east-1")
    
    # AWS - 'mistral.mistral-large-2402-v1:0'
    elif provider == "bedrock" and model == 'mistral.mistral-large-2402-v1:0':
        return init_chat_model("mistral.mistral-large-2402-v1:0", model_provider=provider, temperature=0.3, region="us-east-1")
    
    # OPENAI models
    elif provider == "openai":
        return init_chat_model(model, model_provider=provider, api_key=os.environ.get("OPENAI_API_KEY") , 
                               temperature=0.3, stream_usage=True)
    
    # UNSUPPORTED MODEL
    else:
        raise ValueError("Unsupported model")
