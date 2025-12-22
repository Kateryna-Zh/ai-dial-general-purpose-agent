from typing import Any

from aidial_sdk.chat_completion import Message
from pydantic import StrictStr

from task.tools.deployment.base import DeploymentTool
from task.tools.models import ToolCallParams


class ImageGenerationTool(DeploymentTool):

    async def _execute(self, tool_call_params: ToolCallParams) -> str | Message:
        # In this override impl we just need to add extra actions, we need to propagate attachment to the Choice since
        # in DeploymentTool they were propagated to the stage only as files. The main goal here is show pictures in chat
        # (DIAL Chat support special markdown to load pictures from DIAL bucket directly to the chat)
        # ---
        # 1. Call parent function `_execute` and get result
        message = await super()._execute(tool_call_params)
        # 2. If attachments are present then filter only "image/png" and "image/jpeg"
        attachments = []
        if message.custom_content and message.custom_content.attachments:
            attachments = [
                attachment for attachment in message.custom_content.attachments
                if attachment.type in {"image/png", "image/jpeg"}
            ]
        # 3. Append then as content to choice in such format `f"\n\r![image]({attachment.url})\n\r")`
        for attachment in attachments:
            if attachment.url:
                tool_call_params.choice.append_content(f"\n\r![image]({attachment.url})\n\r")
        # 4. After iteration through attachment if message content is absent add such instruction:
        #    'The image has been successfully generated according to request and shown to user!'
        #    Sometimes models are trying to add generated pictures as well to content (choice), with this instruction
        #    we are notifing LLLM that it was done (but anyway sometimes it will try to add file 😅)
        if not message.content:
            message.content = StrictStr(
                "The image has been successfully generated according to request and shown to user!"
            )

        return message

    @property
    def deployment_name(self) -> str:
        # Provide deployment name for model that you have added to DIAL Core config (dall-e-3)
        return "dall-e-3"

    @property
    def name(self) -> str:
        # Provide self-descriptive name
        return "image_generation_tool"

    @property
    def description(self) -> str:
        # Provide tool description that will help LLM to understand when to use this tools and cover 'tricky'
        #  moments (not more 1024 chars)
        return (
            "Generates an image from a detailed text prompt using DALL-E 3. "
            "Use when the user wants a new image created. "
            "Do not use for editing an existing image or describing an image."
        )
    @property
    def parameters(self) -> dict[str, Any]:
        # TODO: provide tool parameters JSON Schema:
        #  - prompt is string, description: "Extensive description of the image that should be generated.", required
        #  - there are 3 optional parameters: https://platform.openai.com/docs/guides/image-generation?image-generation-model=dall-e-3#customize-image-output
        #  - Sample: https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/dall-e?tabs=dalle-3#call-the-image-generation-api
        return {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Extensive description of the image that should be generated.",
                },
                "size": {
                    "type": "string",
                    "description": "Size of the generated image.",
                    "enum": ["1024x1024", "1024x1792", "1792x1024"],
                },
                "quality": {
                    "type": "string",
                    "description": "Image quality.",
                    "enum": ["standard", "hd"],
                },
                "style": {
                    "type": "string",
                    "description": "Image style.",
                    "enum": ["vivid", "natural"],
                },
            },
            "required": ["prompt"],
        }
