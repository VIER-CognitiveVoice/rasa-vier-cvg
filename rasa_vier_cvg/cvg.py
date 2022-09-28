import logging
from functools import wraps
from typing import Any, Awaitable, Callable, Dict, Optional, Text
import warnings

# ignore ResourceWarning, InsecureRequestWarning
warnings.filterwarnings("ignore", category=ResourceWarning)

from sanic import Blueprint, response
from sanic.request import Request
from sanic.response import HTTPResponse

import rasa.shared.utils.io
from rasa.core.channels.channel import InputChannel, OutputChannel, UserMessage

from cvg_sdk.api_client import ApiClient
from cvg_sdk.api.call_api import CallApi
from cvg_sdk.api.assist_api import AssistApi
from cvg_sdk.configuration import Configuration
from cvg_sdk.model.say_parameters import SayParameters
from cvg_sdk.model.drop_parameters import DropParameters
from cvg_sdk.model.recording_start_parameters import RecordingStartParameters
from cvg_sdk.model.recording_stop_parameters import RecordingStopParameters
from cvg_sdk.model.play_parameters import PlayParameters
from cvg_sdk.model.transcription_switch_parameters import TranscriptionSwitchParameters
from cvg_sdk.model.bridge_parameters import BridgeParameters
from cvg_sdk.model.forward_parameters import ForwardParameters
from cvg_sdk.model.prompt_parameters import PromptParameters

from cvg_sdk.model.inactivity_start_parameters import InactivityStartParameters  # noqa: E501, F401
from cvg_sdk.model.inactivity_stop_parameters import InactivityStopParameters

from cvg_sdk.model.transcription_start_parameters import TranscriptionStartParameters
from cvg_sdk.model.transcription_stop_parameters import TranscriptionStopParameters
from cvg_sdk.model.assist_recording_start_parameters import AssistRecordingStartParameters
from cvg_sdk.model.assist_recording_stop_parameters import AssistRecordingStopParameters
from cvg_sdk.model.outbound_call_result import OutboundCallResult

logger = logging.getLogger(__name__)

CHANNEL_NAME = "vier-cvg"


def make_metadata(payload: Any) -> Dict[Text, Any]:
    return {
        "cvg_body": payload
    }


class CVGOutput(OutputChannel):
    """Output channel for the Cognitive Voice Gateway"""

    on_message: Callable[[UserMessage], Awaitable[Any]]

    @classmethod
    def name(cls) -> Text:
        return CHANNEL_NAME

    def __init__(
        self,
        callback_base_url: Text,
        on_message: Callable[[UserMessage], Awaitable[Any]],
        proxy: Optional[Text] = None,
    ) -> None:  # noqa: E501, F401
        configuration = Configuration.get_default_copy()
        configuration.host = callback_base_url
        configuration.proxy = proxy
        configuration.verify_ssl = False

        self.on_message = on_message

        self.api_client = ApiClient(configuration=configuration)
        self.call_api = CallApi(self.api_client)
        self.assist_api = AssistApi(self.api_client)

    async def send_text_message(
        self,
        recipient_id: Text,
        text: Text,
        **kwargs: Any,
    ) -> None:
        logger.info("Sending message to cvg: %s" % text)
        logger.info("Ignoring the following args: " + str(kwargs))
        self.call_api.say(SayParameters(dialog_id=recipient_id, text=text))

    async def _execute_operation_by_name(
        self,
        operation_name: Text,
        body: Any,
        dialog_id: Text,
    ):  # noqa: E501, F401
        # TODO parameter injection needs to be different per kind of operation
        def create_parameters(parameters_type: type):
            parameter_args = {}
            for (
                python_name,
                spec_name,
            ) in parameters_type.attribute_map.items():  # noqa: E501, F401
                if spec_name in body:
                    parameter_args[python_name] = body[spec_name]
                elif spec_name == "dialogId":
                    parameter_args[python_name] = dialog_id
                else:
                    logger.info(
                        "Parameter %s for endpoint %s not set."
                        % (spec_name, parameters_type.__name__)
                    )  # noqa: E501, F401
            return parameters_type(**parameter_args)

        async def handle_outbound_call_result(outbound_call_result: OutboundCallResult):
            if outbound_call_result.status == "Success":
                user_message = UserMessage(
                    text="/cvg_outbound_success",
                    output_channel=self,
                    sender_id=dialog_id,
                    input_channel=CHANNEL_NAME,
                    metadata=make_metadata(outbound_call_result.to_dict()),
                )
            elif outbound_call_result.status == "Failure":
                user_message = UserMessage(
                    text="/cvg_outbound_failure",
                    output_channel=self,
                    sender_id=dialog_id,
                    input_channel=CHANNEL_NAME,
                    metadata=make_metadata(outbound_call_result.to_dict()),
                )
            else:
                return response.text(f"Invalid OutboundCallResult status: {outbound_call_result.status}", status=400)

            logger.info(
                "Creating incoming UserMessage: {text=%s, output_channel=%s, sender_id=%s, metadata=%s}"  # noqa: E501, F401
                % (user_message.text, user_message.output_channel, user_message.sender_id, user_message.metadata)  # noqa: E501, F401
            )
            await self.on_message(user_message)

        if operation_name == "cvg_call_drop":
            self.call_api.drop(create_parameters(DropParameters))
        elif operation_name == "cvg_call_recording_start":
            self.call_api.start_recording(create_parameters(RecordingStartParameters))
        elif operation_name == "cvg_call_recording_stop":
            self.call_api.stop_recording(create_parameters(RecordingStopParameters))
        elif operation_name == "cvg_call_play":
            self.call_api.play(create_parameters(PlayParameters))
        elif operation_name == "cvg_call_transcription_switch":
            self.call_api.switch_transcription(create_parameters(TranscriptionSwitchParameters))
        elif operation_name == "cvg_call_bridge":
            await handle_outbound_call_result(self.call_api.bridge(create_parameters(BridgeParameters)))
        elif operation_name == "cvg_call_forward":
            await handle_outbound_call_result(self.call_api.forward(create_parameters(ForwardParameters)))
        elif operation_name == "cvg_call_say":
            self.call_api.say(create_parameters(SayParameters))
        elif operation_name == "cvg_call_prompt":
            self.call_api.prompt(create_parameters(PromptParameters))
        elif operation_name == "cvg_inactivity_start":
            self.call_api.start_inactivity(create_parameters(InactivityStartParameters))
        elif operation_name == "cvg_inactivity_stop":
            self.call_api.stop_inactivity(create_parameters(InactivityStopParameters))
        # TODO: I don't think these work correctly with the current dialogId injection logic
        elif operation_name == "cvg_assist_transcription_start":
            self.assist_api.start_transcription(create_parameters(TranscriptionStartParameters))
        elif operation_name == "cvg_assist_transcription_stop":
            self.assist_api.stop_transcription(create_parameters(TranscriptionStopParameters))
        elif operation_name == "cvg_assist_recording_start":
            self.assist_api.start_recording(create_parameters(AssistRecordingStartParameters))
        elif operation_name == "cvg_assist_recording_stop":
            self.assist_api.stop_recording(create_parameters(AssistRecordingStopParameters))
        else:
            logger.error(
                "Operation %s not found/not implemented yet" % operation_name
            )  # noqa: E501, F401
        logger.info("Ran operation: " + operation_name)

    async def send_custom_json(
        self,
        recipient_id: Text,
        json_message: Dict[Text, Any],
        **kwargs: Any,  # noqa: E501, F401
    ) -> None:
        logger.info("Received custom json: %s to %s" % (json_message, recipient_id))
        for key, value in json_message.items():
            await self._execute_operation_by_name(operation_name=key, dialog_id=recipient_id, body=value)

    async def send_image_url(self, **_: Any) -> None:
        # We do not support images.
        rasa.shared.utils.io.raise_warning(
            "Ignoring image URL."
            "We cannot represent images as a voice bot."
            "Please define a voice-friendly alternative."
        )

class CVGInput(InputChannel):
    """Input channel for the Cognitive Voice Gateway"""

    @classmethod
    def name(cls) -> Text:
        return CHANNEL_NAME

    @classmethod
    def from_credentials(
        cls, credentials: Optional[Dict[Text, Any]]
    ) -> InputChannel:
        if not credentials:
            cls.raise_missing_credentials_exception()
        token = credentials.get("token")
        if token is None or type(token) != str or len(token) == 0:
            raise ValueError('No authentication token has been configured in your credentials.yml!')
        proxy = credentials.get("proxy")

        return cls(token, proxy)

    def __init__(self, token: Text, proxy: Optional[Text] = None) -> None:
        self.callback = None
        self.expected_authorization_header_value = f"Bearer {token}"
        self.proxy = proxy

    async def process_message(
        self,
        request: Request,
        on_new_message: Callable[[UserMessage], Awaitable[Any]],
        text: Text,
        sender_id: Optional[Text],
    ) -> Any:
        try:
            if text[-1] == ".":
                text = text[:-1]

            metadata = make_metadata(request.json)
            user_msg = UserMessage(
                text=text,
                output_channel=CVGOutput(request.json["callback"], on_new_message, self.proxy),
                sender_id=sender_id,
                input_channel=CHANNEL_NAME,
                metadata=metadata,
            )

            logger.info(
                "Creating incoming UserMessage: {text=%s, output_channel=%s, sender_id=%s, metadata=%s}"  # noqa: E501, F401
                % (text, user_msg.output_channel, sender_id, metadata)
            )

            await on_new_message(user_msg)
        except Exception as e:
            logger.error(f"Exception when trying to handle message.{e}")
            logger.error(str(e), exc_info=True)

        return response.text("")

    def blueprint(
        self, on_new_message: Callable[[UserMessage], Awaitable[Any]]
    ) -> Blueprint:
        def valid_request(func):
            def decorator(f):
                @wraps(f)
                async def decorated_function(request: HTTPResponse, *args, **kwargs):
                    if request.headers.get("authorization") != self.expected_authorization_header_value:
                        return response.text("bot token is invalid!", status=401)

                    if not request.headers.get("content-type") == "application/json":
                        return response.text("content-type is not supported. Please use application/json", status=415)
                    json_body = request.json
                    if json_body is None:
                        return response.text("body is not valid json.", status=400)
                    if json_body["dialogId"] is None:
                        return response.text("dialogId is required", status=400)
                    if json_body["callback"] is None:
                        return response.text("callback is required", status=400)
                    return await f(request, *args, **kwargs)
                return decorated_function
            return decorator(func)

        async def process_message_oneline(request: Request, text: Text):
            return await self.process_message(
                request,
                on_new_message,
                text=text,
                sender_id=request.json["dialogId"],
            )
            
        cvg_webhook = Blueprint(
            "vier_cvg_webhook", __name__,
        )

        @cvg_webhook.post("/session")
        @valid_request
        async def session(request: Request) -> HTTPResponse:
            return await process_message_oneline(request, "/cvg_session")
        
        @cvg_webhook.post("/message")
        @valid_request
        async def message(request: Request) -> HTTPResponse:
            return await process_message_oneline(request, request.json["text"])

        @cvg_webhook.post("/answer")
        @valid_request
        async def answer(request: Request) -> HTTPResponse:
            return await process_message_oneline(request, "/cvg_answer_" + request.json["type"]["name"].lower())

        @cvg_webhook.post("/inactivity")
        @valid_request
        async def inactivity(request: Request) -> HTTPResponse:
            return await process_message_oneline(request, "/cvg_inactivity")

        @cvg_webhook.post("/terminated")
        @valid_request
        async def terminated(request: Request) -> HTTPResponse:
            return await process_message_oneline(request, "/cvg_terminated")

        @cvg_webhook.post("/recording")
        @valid_request
        async def recording(request: Request) -> HTTPResponse:
            return await process_message_oneline(request, "/cvg_recording")

        return cvg_webhook
