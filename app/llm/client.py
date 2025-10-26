import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Literal, Optional, Union

from openai import OpenAI
from openai.types.responses import ParsedResponse, Response
from openai.types.responses.response_input_param import FunctionCallOutput
from pydantic import BaseModel

from app.agents.tool_registry import Tool

logger = logging.getLogger(__name__)


class LLMTextResponse(BaseModel):
    type: Literal["text"] = "text"
    text: str


class LLMStructuredResponse(BaseModel):
    type: Literal["structured"] = "structured"
    data: BaseModel


class LLMToolCallDetails(BaseModel):
    name: str
    arguments: dict[str, Any]
    call_id: str


class LLMToolCallRequestResponse(BaseModel):
    type: Literal["tool_call"] = "tool_call"
    tools: list[LLMToolCallDetails]
    conversation_context: Any


class LLMToolCallResponse(BaseModel):
    "Response to a tool call request"

    name: str
    call_id: str
    response: Any


LLMResponse = Union[LLMTextResponse, LLMStructuredResponse, LLMToolCallRequestResponse]


class LLMClient(ABC):
    @abstractmethod
    def generate(
        self,
        message: str,
        model: str,
        tools: list[Tool],
        response_model: type[BaseModel] | None = None,
        **kwargs: Any,
    ) -> LLMResponse: ...

    @abstractmethod
    def continue_after_function_call(
        self,
        tool_results: list[LLMToolCallResponse],
        model: str,
        response_model: type[BaseModel],
        conversation_context: Any,
        tools: list[Tool],
        **kwargs,
    ) -> LLMResponse: ...


class OpenAIClient(LLMClient):
    """Minimal OpenAI client exposing a single text-or-structural response entrypoint."""

    def __init__(self, client: Optional[OpenAI] = None) -> None:
        self._client = client or OpenAI()

    def generate(
        self,
        message: str,
        model: str,
        tools: list[Tool],
        response_model: type[BaseModel] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        logger.info(
            "generate start model=%s tools=%d response_model=%s",
            model,
            len(tools),
            response_model.__name__ if response_model else "None",
        )
        message_payload = [{"role": "system", "content": message}]
        response = self._send_request(model, message_payload, response_model, tools=tools, **kwargs)
        logger.info("generate response received model=%s", model)
        return self._process_response(message_payload, response)

    def continue_after_function_call(
        self,
        tool_results: list[LLMToolCallResponse],
        model: str,
        response_model: type[BaseModel],
        conversation_context: list[Any],
        tools: list[Tool],
        **kwargs,
    ) -> LLMResponse:
        logger.info(
            "continue_after_function_call start model=%s tools=%d tool_results=%d",
            model,
            len(tools),
            len(tool_results),
        )
        conversation_context = conversation_context.copy()
        for tool_result in tool_results:
            function_call_output: FunctionCallOutput = {
                "call_id": tool_result.call_id,
                "output": str(tool_result.response),
                "type": "function_call_output",
            }
            conversation_context.append(function_call_output)

        response = self._send_request(
            model, conversation_context, response_model, tools=tools, **kwargs
        )
        logger.info("continue_after_function_call response received model=%s", model)
        return self._process_response(conversation_context, response)

    def _send_request(
        self,
        model: str,
        payload: Any,
        response_model: type[BaseModel] | None,
        tools: list[Tool],
        **kwargs: Any,
    ) -> ParsedResponse | Response:
        openai_tools = [t.function_schema for t in tools]
        payload_size = len(payload) if hasattr(payload, "__len__") else 1
        logger.info(
            "sending request model=%s payload_items=%d tools=%d parsed=%s",
            model,
            payload_size,
            len(openai_tools),
            bool(response_model),
        )
        if response_model is not None:
            return self._client.responses.parse(
                model=model,
                input=payload,
                text_format=response_model,
                tools=openai_tools,
                **kwargs,
            )
        return self._client.responses.create(
            model=model,
            input=payload,
            tools=openai_tools,
            **kwargs,
        )

    def _process_response(
        self, request_payload: Any, response: ParsedResponse | Response
    ) -> LLMResponse:
        if isinstance(response, ParsedResponse) and response.output_parsed is not None:
            logger.info("process_response structured")
            return LLMStructuredResponse(data=response.output_parsed)

        tool_calls = self._extract_tool_calls(response)
        if tool_calls:
            request_payload = (
                [request_payload] if isinstance(request_payload, str) else request_payload
            )
            logger.info("process_response tool_calls=%d", len(tool_calls))
            return LLMToolCallRequestResponse(
                tools=tool_calls, conversation_context=[*request_payload, *response.output]
            )

        if response.output_text:
            logger.info("process_response text")
            return LLMTextResponse(text=response.output_text)

        raise ValueError("Unexpected OpenAI response.")

    def _extract_tool_calls(self, response: ParsedResponse | Response) -> list[LLMToolCallDetails]:
        tool_calls: list[LLMToolCallDetails] = []
        for output_message in response.output or []:
            if output_message.type != "function_call":
                continue
            tool_calls.append(
                LLMToolCallDetails(
                    name=output_message.name,
                    arguments=json.loads(output_message.arguments),
                    call_id=output_message.call_id,
                )
            )
        if tool_calls:
            logger.info("extract_tool_calls count=%d", len(tool_calls))
        return tool_calls
